from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.models import FeeType, InvoiceStatus, PaymentStatus


# ─── Auth Schemas ─────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    api_key: str = Field(..., description="API key from init_db.py")
    api_secret: str = Field(..., description="API secret from init_db.py")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    token_name: str


# ─── Preorder / Invoice Schemas ───────────────────────────────────────────────

class PreorderRequest(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=50, description="Unique student ID")
    student_name: str = Field(..., min_length=1, max_length=200, description="Full name of student")
    guardian_phone: str = Field(..., description="Guardian phone number (+25361234567)")
    guardian_email: Optional[str] = Field(None, description="Guardian email address")
    fee_type: FeeType = Field(..., description="Type of fee")
    amount: float = Field(..., gt=0, description="Amount in DJF")
    due_date: str = Field(..., description="Due date (YYYY-MM-DD)")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")

    @validator("guardian_phone")
    def validate_phone(cls, v):
        # Basic phone validation - must start with + or digits
        phone = v.strip()
        if not phone:
            raise ValueError("Phone number cannot be empty")
        return phone

    @validator("due_date")
    def validate_due_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("due_date must be in YYYY-MM-DD format")
        return v


class PreorderResponse(BaseModel):
    success: bool
    order_id: str
    payment_link: str
    status: InvoiceStatus
    amount: float
    currency: str
    due_date: str
    message: str


# ─── Order / Invoice Query Schemas ────────────────────────────────────────────

class PaymentInfo(BaseModel):
    transaction_id: str
    amount: float
    currency: str
    payment_method: Optional[str]
    payer_phone: Optional[str]
    status: PaymentStatus
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    success: bool
    order_id: str
    student_id: str
    student_name: str
    guardian_phone: str
    guardian_email: Optional[str]
    fee_type: FeeType
    amount: float
    currency: str
    due_date: datetime
    description: Optional[str]
    status: InvoiceStatus
    payment_link: Optional[str]
    created_at: datetime
    updated_at: datetime
    paid_at: Optional[datetime]
    payments: List[PaymentInfo] = []

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    success: bool
    total: int
    page: int
    page_size: int
    orders: List[OrderResponse]


# ─── Webhook Schemas ──────────────────────────────────────────────────────────

class DMoneyWebhookPayload(BaseModel):
    """
    Actual D-Money webhook notification payload.
    trade_status values: Completed | Paying | Expired | Failure
    """
    merch_order_id: str = Field(..., description="Merchant order ID (our order_id)")
    trade_status: str = Field(..., description="Completed | Paying | Expired | Failure")
    # D-Money's platform transaction ID
    payment_order_id: Optional[str] = Field(None, description="D-Money platform order ID")
    transId: Optional[str] = Field(None, description="D-Money transaction ID (alt field)")
    total_amount: Optional[str] = Field(None, description="Order amount as string")
    trans_currency: Optional[str] = Field("DJF", description="Transaction currency")
    appid: Optional[str] = Field(None, description="Merchant app ID")
    merch_code: Optional[str] = Field(None, description="Merchant short code")
    notify_url: Optional[str] = Field(None)
    notify_time: Optional[str] = Field(None)
    trans_end_time: Optional[str] = Field(None)
    callback_info: Optional[str] = Field(None)
    timestamp: Optional[str] = Field(None)
    sign: Optional[str] = Field(None, description="D-Money signature")
    sign_type: Optional[str] = Field(None)

    class Config:
        extra = "allow"   # accept any extra fields D-Money may add in future


class WebhookResponse(BaseModel):
    """Response expected by D-Money after webhook delivery"""
    success: bool
    message: str


# ─── Dashboard Schemas ────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_invoices: int
    pending_invoices: int
    paid_invoices: int
    failed_invoices: int
    overdue_invoices: int
    total_revenue: float
    pending_revenue: float
    currency: str


class TransactionItem(BaseModel):
    order_id: str
    student_name: str
    guardian_phone: str
    fee_type: FeeType
    amount: float
    currency: str
    status: InvoiceStatus
    created_at: datetime
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    success: bool
    total: int
    page: int
    page_size: int
    transactions: List[TransactionItem]


class RevenueDataPoint(BaseModel):
    period: str
    revenue: float
    count: int


class RevenueResponse(BaseModel):
    success: bool
    period: str
    data: List[RevenueDataPoint]
    total_revenue: float
    currency: str


class GuardianHistoryItem(BaseModel):
    order_id: str
    student_name: str
    fee_type: FeeType
    amount: float
    currency: str
    status: InvoiceStatus
    created_at: datetime
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True


class GuardianHistoryResponse(BaseModel):
    success: bool
    guardian_phone: str
    total_invoices: int
    total_paid: float
    currency: str
    invoices: List[GuardianHistoryItem]


# ─── Error Schema ─────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
