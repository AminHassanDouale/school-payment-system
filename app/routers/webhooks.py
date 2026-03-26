from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
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

# Map D-Money trade_status → our PaymentStatus
_TRADE_STATUS_MAP = {
    "completed": PaymentStatus.SUCCESS,
    "paying":    PaymentStatus.PENDING,
    "expired":   PaymentStatus.FAILED,
    "failure":   PaymentStatus.FAILED,
}


@router.post(
    "/dmoney",
    summary="D-Money Payment Webhook",
    description=(
        "Receives payment status notifications from D-Money. "
        "trade_status values: Completed | Paying | Expired | Failure"
    ),
)
async def dmoney_webhook(
    payload: DMoneyWebhookPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    D-Money calls this endpoint when a payment status changes.

    - Verifies the RSA-PSS signature (when present)
    - Looks up the invoice by merch_order_id
    - Creates/updates the Payment record
    - Updates the Invoice status
    - Returns {"success": true, "message": "..."} as required by D-Money
    """
    order_id = payload.merch_order_id
    logger.info(f"D-Money webhook received for order {order_id}: trade_status={payload.trade_status}")

    try:
        # ── 1. Verify signature ──────────────────────────────────────────────
        if payload.sign:
            flat = payload.model_dump(exclude_none=True)
            is_valid = dmoney_gateway.verify_webhook_signature(flat, payload.sign)
            if not is_valid:
                logger.warning(f"Invalid webhook signature for order {order_id}")
                # Return 200 with error body so D-Money doesn't keep retrying on auth errors
                return JSONResponse(
                    status_code=200,
                    content={"success": False, "message": "Invalid signature"}
                )

        # ── 2. Idempotency check ─────────────────────────────────────────────
        txn_id = payload.payment_order_id or payload.transId or f"dmoney_{order_id}"
        existing_payment = db.query(Payment).filter(
            Payment.transaction_id == txn_id,
            Payment.status == PaymentStatus.SUCCESS,
        ).first()
        if existing_payment:
            logger.info(f"Webhook already processed for order {order_id}, skipping")
            return JSONResponse(
                status_code=200,
                content={"success": True, "message": "Already processed"}
            )

        # ── 3. Find invoice ──────────────────────────────────────────────────
        invoice = db.query(Invoice).filter(Invoice.order_id == order_id).first()
        if not invoice:
            logger.error(f"Invoice not found for webhook order {order_id}")
            # Return 200 to prevent D-Money from endless retries for unknown orders
            return JSONResponse(
                status_code=200,
                content={"success": False, "message": f"Order {order_id} not found"}
            )

        # ── 4. Map trade_status → PaymentStatus ──────────────────────────────
        payment_status = _TRADE_STATUS_MAP.get(
            payload.trade_status.lower(), PaymentStatus.PENDING
        )

        # ── 5. Parse amount ───────────────────────────────────────────────────
        try:
            paid_amount = float(payload.total_amount or invoice.amount)
        except (ValueError, TypeError):
            paid_amount = invoice.amount

        # ── 6. Upsert Payment record ─────────────────────────────────────────
        payment = db.query(Payment).filter(Payment.transaction_id == txn_id).first()
        raw_data = json.dumps(payload.model_dump())

        if payment:
            payment.status = payment_status
            payment.amount = paid_amount
            payment.currency = payload.trans_currency or "DJF"
            payment.dmoney_reference = payload.payment_order_id
            payment.dmoney_status_code = payload.trade_status
            payment.webhook_data = raw_data
            if payment_status == PaymentStatus.SUCCESS:
                payment.paid_at = datetime.utcnow()
            elif payment_status == PaymentStatus.FAILED:
                payment.failed_at = datetime.utcnow()
        else:
            payment = Payment(
                invoice_id=invoice.id,
                transaction_id=txn_id,
                amount=paid_amount,
                currency=payload.trans_currency or "DJF",
                status=payment_status,
                dmoney_reference=payload.payment_order_id,
                dmoney_status_code=payload.trade_status,
                webhook_data=raw_data,
                initiated_at=datetime.utcnow(),
            )
            if payment_status == PaymentStatus.SUCCESS:
                payment.paid_at = datetime.utcnow()
            elif payment_status == PaymentStatus.FAILED:
                payment.failed_at = datetime.utcnow()
            db.add(payment)

        # ── 7. Update invoice status ─────────────────────────────────────────
        if payment_status == PaymentStatus.SUCCESS:
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.utcnow()
            logger.info(
                f"Invoice {order_id} marked PAID — "
                f"amount={paid_amount} {payload.trans_currency}"
            )
        elif payment_status == PaymentStatus.FAILED:
            invoice.status = InvoiceStatus.FAILED
            logger.warning(f"Payment FAILED for invoice {order_id}")
        # Paying → leave invoice as PENDING

        db.commit()
        logger.info(f"Webhook processed OK for order {order_id}")

        # ── 8. Return D-Money expected response ──────────────────────────────
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Payment notification processed successfully"
            }
        )

    except Exception as e:
        logger.error(f"Webhook processing error for order {order_id}: {e}", exc_info=True)
        db.rollback()
        # Return 200 with error body — HTTP 5xx would cause D-Money to retry indefinitely
        return JSONResponse(
            status_code=200,
            content={"success": False, "message": "Internal processing error"}
        )


@router.get(
    "/test",
    summary="Test Webhook Endpoint",
    description="Verify this webhook URL is reachable (for D-Money configuration)"
)
async def test_webhook():
    return {
        "status": "ok",
        "message": "D-Money webhook endpoint is active",
        "timestamp": datetime.utcnow().isoformat()
    }
