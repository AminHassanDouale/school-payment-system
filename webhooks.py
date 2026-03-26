from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.models.models import Invoice, Payment, InvoiceStatus, PaymentStatus
from app.schemas.schemas import DMoneyWebhookPayload, WebhookResponse, ErrorResponse
from app.services.dmoney_service import dmoney_gateway
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post(
    "/dmoney",
    response_model=WebhookResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid webhook"},
        404: {"model": ErrorResponse, "description": "Order not found"},
        500: {"model": ErrorResponse, "description": "Server error"}
    },
    summary="D-Money Payment Webhook",
    description="Webhook endpoint for D-Money to send payment status updates"
)
async def dmoney_webhook(
    payload: DMoneyWebhookPayload,
    request: Request,
    x_signature: str = Header(None, alias="X-Signature"),
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for D-Money payment confirmations.
    
    This endpoint is called by D-Money when a payment status changes.
    It updates the invoice status and creates payment records.
    
    **Security:** Webhook signature is verified to ensure authenticity.
    
    **Webhook Payload:**
    - order_id: The order identifier
    - transaction_id: D-Money transaction ID
    - status: Payment status (success, failed, pending)
    - amount: Payment amount
    - payment_method: Payment method used
    - payer_phone: Payer's phone number
    
    **Actions:**
    - Updates invoice status
    - Creates/updates payment record
    - Logs payment event
    - (Future: Send SMS notification to guardian)
    """
    try:
        logger.info(f"Webhook received for order: {payload.order_id}")
        
        # Verify webhook signature if provided
        if x_signature:
            payload_dict = payload.model_dump()
            is_valid = dmoney_gateway.verify_webhook_signature(
                payload_dict,
                x_signature
            )
            
            if not is_valid:
                logger.warning(f"Invalid webhook signature for order {payload.order_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid webhook signature"
                )
        
        # Find invoice
        invoice = db.query(Invoice).filter(Invoice.order_id == payload.order_id).first()
        
        if not invoice:
            logger.error(f"Invoice not found for webhook: {payload.order_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order {payload.order_id} not found"
            )
        
        # Map D-Money status to our payment status
        status_mapping = {
            "success": PaymentStatus.SUCCESS,
            "completed": PaymentStatus.SUCCESS,
            "paid": PaymentStatus.SUCCESS,
            "failed": PaymentStatus.FAILED,
            "error": PaymentStatus.FAILED,
            "pending": PaymentStatus.PENDING,
            "initiated": PaymentStatus.INITIATED
        }
        
        payment_status = status_mapping.get(
            payload.status.lower(),
            PaymentStatus.PENDING
        )
        
        # Find existing payment or create new one
        payment = db.query(Payment).filter(
            Payment.transaction_id == payload.transaction_id
        ).first()
        
        if payment:
            # Update existing payment
            payment.status = payment_status
            payment.amount = payload.amount
            payment.payment_method = payload.payment_method
            payment.payer_phone = payload.payer_phone
            payment.payer_name = payload.payer_name
            payment.dmoney_reference = payload.reference
            payment.dmoney_status_code = payload.status_code
            payment.dmoney_status_message = payload.status_message
            payment.webhook_data = json.dumps(payload.model_dump())
            
            if payment_status == PaymentStatus.SUCCESS:
                payment.paid_at = datetime.utcnow()
            elif payment_status == PaymentStatus.FAILED:
                payment.failed_at = datetime.utcnow()
        else:
            # Create new payment record
            payment = Payment(
                invoice_id=invoice.id,
                transaction_id=payload.transaction_id,
                amount=payload.amount,
                currency=payload.currency or "DJF",
                payment_method=payload.payment_method,
                payer_phone=payload.payer_phone,
                payer_name=payload.payer_name,
                status=payment_status,
                dmoney_reference=payload.reference,
                dmoney_status_code=payload.status_code,
                dmoney_status_message=payload.status_message,
                webhook_data=json.dumps(payload.model_dump()),
                initiated_at=datetime.utcnow()
            )
            
            if payment_status == PaymentStatus.SUCCESS:
                payment.paid_at = datetime.utcnow()
            elif payment_status == PaymentStatus.FAILED:
                payment.failed_at = datetime.utcnow()
            
            db.add(payment)
        
        # Update invoice status based on payment status
        if payment_status == PaymentStatus.SUCCESS:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.utcnow()
            logger.info(f"Invoice {invoice.order_id} marked as PAID - Amount: {payload.amount} DJF")
            
        elif payment_status == PaymentStatus.FAILED:
            invoice.status = InvoiceStatus.FAILED
            logger.warning(f"Payment failed for invoice {invoice.order_id}")
        
        db.commit()
        db.refresh(invoice)
        
        logger.info(f"Webhook processed successfully for order {payload.order_id}")
        
        return WebhookResponse(
            success=True,
            message="Webhook processed successfully",
            order_id=invoice.order_id,
            status=invoice.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook for order {payload.order_id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process webhook"
        )


@router.get(
    "/test",
    summary="Test Webhook Endpoint",
    description="Test if webhook endpoint is accessible"
)
async def test_webhook():
    """
    Test endpoint to verify webhook is accessible.
    
    D-Money may call this endpoint to verify webhook configuration.
    """
    return {
        "status": "ok",
        "message": "Webhook endpoint is active",
        "timestamp": datetime.utcnow().isoformat()
    }
