from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.models import Invoice, InvoiceStatus, APIToken
from app.schemas.schemas import PreorderRequest, PreorderResponse, ErrorResponse
from app.services.dmoney_service import dmoney_gateway
from app.routers.auth import get_current_token
import secrets
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/preorder", tags=["Preorder"])


def generate_order_id() -> str:
    """
    Generate unique order ID.
    D-Money merch_order_id must match ^[A-Za-z0-9]+$ — no hyphens or special chars.
    Example: ORD202603261A2B3C4D
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(4).upper()
    return f"ORD{timestamp}{random_part}"


@router.post(
    "",
    response_model=PreorderResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
    summary="Create Invoice (Preorder)",
    description="Create a new school fee invoice and generate payment link for guardian"
)
async def create_preorder(
    request: PreorderRequest,
    db: Session = Depends(get_db),
    current_token: APIToken = Depends(get_current_token)
):
    """
    Create a new invoice for school fees.

    Called by scolapp to create payment requests for guardians.
    Generates a unique order ID and payment link via D-Money.

    **Required Authentication:** Bearer token from /auth/token
    """
    try:
        order_id = generate_order_id()
        due_date = datetime.strptime(request.due_date, "%Y-%m-%d")

        invoice = Invoice(
            order_id=order_id,
            student_id=request.student_id,
            student_name=request.student_name,
            guardian_phone=request.guardian_phone,
            guardian_email=request.guardian_email,
            fee_type=request.fee_type,
            amount=request.amount,
            currency=settings.PAYMENT_CURRENCY,
            due_date=due_date,
            description=request.description,
            status=InvoiceStatus.PENDING,
            created_by_token_id=current_token.id
        )

        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        # Create payment request in D-Money
        payment_result = await dmoney_gateway.create_payment_request(
            order_id=order_id,
            amount=request.amount,
            guardian_phone=request.guardian_phone,
            description=f"{request.fee_type.value} - {request.student_name}",
            student_name=request.student_name
        )

        if not payment_result.get("success"):
            logger.error(f"Failed to create D-Money payment for order {order_id}")
            invoice.status = InvoiceStatus.FAILED
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create payment request"
            )

        payment_link = payment_result.get("payment_url", f"{settings.SCOLAPP_DOMAIN}/pay/{order_id}")
        invoice.payment_link = payment_link
        db.commit()

        logger.info(f"Invoice created: {order_id} for student {request.student_id} by {current_token.name}")

        return PreorderResponse(
            success=True,
            order_id=order_id,
            payment_link=payment_link,
            status=InvoiceStatus.PENDING,
            amount=request.amount,
            currency=settings.PAYMENT_CURRENCY,
            due_date=request.due_date,
            message="Invoice created successfully. Payment link sent to guardian."
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error in preorder: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating preorder: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invoice"
        )
