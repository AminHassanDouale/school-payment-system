from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.config import settings
from app.models.models import Invoice, Payment, InvoiceStatus, FeeType, APIToken
from app.schemas.schemas import (
    DashboardStats, TransactionListResponse, TransactionItem,
    RevenueResponse, RevenueDataPoint, GuardianHistoryResponse, GuardianHistoryItem,
    ErrorResponse
)
from app.routers.auth import get_current_token
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/stats",
    response_model=DashboardStats,
    responses={401: {"model": ErrorResponse, "description": "Unauthorized"}},
    summary="Dashboard Statistics",
    description="Overall system statistics"
)
async def get_stats(
    db: Session = Depends(get_db),
    current_token: APIToken = Depends(get_current_token)
):
    """Return aggregate statistics across all invoices."""
    total = db.query(Invoice).count()
    pending = db.query(Invoice).filter(Invoice.status == InvoiceStatus.PENDING).count()
    paid = db.query(Invoice).filter(Invoice.status == InvoiceStatus.PAID).count()
    failed = db.query(Invoice).filter(Invoice.status == InvoiceStatus.FAILED).count()
    overdue = db.query(Invoice).filter(Invoice.status == InvoiceStatus.OVERDUE).count()

    total_revenue = db.query(func.sum(Invoice.amount)).filter(
        Invoice.status == InvoiceStatus.PAID
    ).scalar() or 0.0

    pending_revenue = db.query(func.sum(Invoice.amount)).filter(
        Invoice.status == InvoiceStatus.PENDING
    ).scalar() or 0.0

    return DashboardStats(
        total_invoices=total,
        pending_invoices=pending,
        paid_invoices=paid,
        failed_invoices=failed,
        overdue_invoices=overdue,
        total_revenue=float(total_revenue),
        pending_revenue=float(pending_revenue),
        currency=settings.PAYMENT_CURRENCY
    )


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    responses={401: {"model": ErrorResponse, "description": "Unauthorized"}},
    summary="Transaction List",
    description="Paginated list of all transactions"
)
async def get_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[InvoiceStatus] = Query(None, alias="status"),
    fee_type: Optional[FeeType] = Query(None),
    db: Session = Depends(get_db),
    current_token: APIToken = Depends(get_current_token)
):
    """Return a paginated list of invoices/transactions."""
    query = db.query(Invoice)
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    if fee_type:
        query = query.filter(Invoice.fee_type == fee_type)

    total = query.count()
    invoices = query.order_by(Invoice.created_at.desc()) \
                    .offset((page - 1) * page_size) \
                    .limit(page_size) \
                    .all()

    transactions = [
        TransactionItem(
            order_id=inv.order_id,
            student_name=inv.student_name,
            guardian_phone=inv.guardian_phone,
            fee_type=inv.fee_type,
            amount=inv.amount,
            currency=inv.currency,
            status=inv.status,
            created_at=inv.created_at,
            paid_at=inv.paid_at
        )
        for inv in invoices
    ]

    return TransactionListResponse(
        success=True,
        total=total,
        page=page,
        page_size=page_size,
        transactions=transactions
    )


@router.get(
    "/revenue",
    response_model=RevenueResponse,
    responses={401: {"model": ErrorResponse, "description": "Unauthorized"}},
    summary="Revenue Analytics",
    description="Revenue breakdown by period (daily, monthly, yearly)"
)
async def get_revenue(
    period: str = Query("monthly", description="Period: daily | monthly | yearly"),
    db: Session = Depends(get_db),
    current_token: APIToken = Depends(get_current_token)
):
    """Return revenue aggregated by the requested period."""
    paid_invoices = db.query(Invoice).filter(Invoice.status == InvoiceStatus.PAID).all()

    revenue_map: dict = {}
    for inv in paid_invoices:
        if period == "daily":
            key = inv.paid_at.strftime("%Y-%m-%d") if inv.paid_at else inv.created_at.strftime("%Y-%m-%d")
        elif period == "yearly":
            key = inv.paid_at.strftime("%Y") if inv.paid_at else inv.created_at.strftime("%Y")
        else:  # monthly (default)
            key = inv.paid_at.strftime("%Y-%m") if inv.paid_at else inv.created_at.strftime("%Y-%m")

        if key not in revenue_map:
            revenue_map[key] = {"revenue": 0.0, "count": 0}
        revenue_map[key]["revenue"] += inv.amount
        revenue_map[key]["count"] += 1

    data = [
        RevenueDataPoint(period=k, revenue=v["revenue"], count=v["count"])
        for k, v in sorted(revenue_map.items())
    ]
    total_revenue = sum(d.revenue for d in data)

    return RevenueResponse(
        success=True,
        period=period,
        data=data,
        total_revenue=total_revenue,
        currency=settings.PAYMENT_CURRENCY
    )


@router.get(
    "/guardian/{phone}/history",
    response_model=GuardianHistoryResponse,
    responses={401: {"model": ErrorResponse, "description": "Unauthorized"}},
    summary="Guardian Payment History",
    description="Full payment history for a specific guardian phone number"
)
async def get_guardian_history(
    phone: str,
    db: Session = Depends(get_db),
    current_token: APIToken = Depends(get_current_token)
):
    """Return all invoices associated with the given guardian phone number."""
    invoices = db.query(Invoice).filter(
        Invoice.guardian_phone == phone
    ).order_by(Invoice.created_at.desc()).all()

    total_paid = sum(
        inv.amount for inv in invoices if inv.status == InvoiceStatus.PAID
    )

    items = [
        GuardianHistoryItem(
            order_id=inv.order_id,
            student_name=inv.student_name,
            fee_type=inv.fee_type,
            amount=inv.amount,
            currency=inv.currency,
            status=inv.status,
            created_at=inv.created_at,
            paid_at=inv.paid_at
        )
        for inv in invoices
    ]

    return GuardianHistoryResponse(
        success=True,
        guardian_phone=phone,
        total_invoices=len(invoices),
        total_paid=total_paid,
        currency=settings.PAYMENT_CURRENCY,
        invoices=items
    )
