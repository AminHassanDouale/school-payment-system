from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.models import Invoice, InvoiceStatus, FeeType, APIToken
from app.schemas.schemas import OrderResponse, OrderListResponse, PaymentInfo, ErrorResponse
from app.routers.auth import get_current_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
    summary="Get Order by ID",
    description="Retrieve a specific order and its payment status"
)
async def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_token: APIToken = Depends(get_current_token)
):
    """Retrieve a specific invoice/order by its order ID."""
    invoice = db.query(Invoice).filter(Invoice.order_id == order_id).first()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )

    payments = [
        PaymentInfo(
            transaction_id=p.transaction_id,
            amount=p.amount,
            currency=p.currency,
            payment_method=p.payment_method,
            payer_phone=p.payer_phone,
            status=p.status,
            paid_at=p.paid_at
        )
        for p in invoice.payments
    ]

    return OrderResponse(
        success=True,
        order_id=invoice.order_id,
        student_id=invoice.student_id,
        student_name=invoice.student_name,
        guardian_phone=invoice.guardian_phone,
        guardian_email=invoice.guardian_email,
        fee_type=invoice.fee_type,
        amount=invoice.amount,
        currency=invoice.currency,
        due_date=invoice.due_date,
        description=invoice.description,
        status=invoice.status,
        payment_link=invoice.payment_link,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        paid_at=invoice.paid_at,
        payments=payments
    )


@router.get(
    "",
    response_model=OrderListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
    summary="List Orders",
    description="Query orders with optional filters"
)
async def list_orders(
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    guardian_phone: Optional[str] = Query(None, description="Filter by guardian phone"),
    status_filter: Optional[InvoiceStatus] = Query(None, alias="status", description="Filter by status"),
    fee_type: Optional[FeeType] = Query(None, description="Filter by fee type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db),
    current_token: APIToken = Depends(get_current_token)
):
    """Query invoices with optional filters and pagination."""
    query = db.query(Invoice)

    if student_id:
        query = query.filter(Invoice.student_id == student_id)
    if guardian_phone:
        query = query.filter(Invoice.guardian_phone == guardian_phone)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if fee_type:
        query = query.filter(Invoice.fee_type == fee_type)

    total = query.count()
    invoices = query.order_by(Invoice.created_at.desc()) \
                    .offset((page - 1) * page_size) \
                    .limit(page_size) \
                    .all()

    orders = []
    for invoice in invoices:
        payments = [
            PaymentInfo(
                transaction_id=p.transaction_id,
                amount=p.amount,
                currency=p.currency,
                payment_method=p.payment_method,
                payer_phone=p.payer_phone,
                status=p.status,
                paid_at=p.paid_at
            )
            for p in invoice.payments
        ]
        orders.append(OrderResponse(
            success=True,
            order_id=invoice.order_id,
            student_id=invoice.student_id,
            student_name=invoice.student_name,
            guardian_phone=invoice.guardian_phone,
            guardian_email=invoice.guardian_email,
            fee_type=invoice.fee_type,
            amount=invoice.amount,
            currency=invoice.currency,
            due_date=invoice.due_date,
            description=invoice.description,
            status=invoice.status,
            payment_link=invoice.payment_link,
            created_at=invoice.created_at,
            updated_at=invoice.updated_at,
            paid_at=invoice.paid_at,
            payments=payments
        ))

    return OrderListResponse(
        success=True,
        total=total,
        page=page,
        page_size=page_size,
        orders=orders
    )
