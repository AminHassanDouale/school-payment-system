from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float,
    Text, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class FeeType(str, enum.Enum):
    TUITION = "tuition"
    BOOKS = "books"
    UNIFORM = "uniform"
    TRANSPORT = "transport"
    MEALS = "meals"
    ACTIVITIES = "activities"
    EXAM = "exam"
    REGISTRATION = "registration"
    OTHER = "other"


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    FAILED = "failed"


class PaymentStatus(str, enum.Enum):
    INITIATED = "initiated"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), unique=True, nullable=False, index=True)
    student_id = Column(String(50), nullable=False, index=True)
    student_name = Column(String(200), nullable=False)
    guardian_phone = Column(String(20), nullable=False, index=True)
    guardian_email = Column(String(100), nullable=True)
    fee_type = Column(SQLEnum(FeeType), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="DJF")
    due_date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.PENDING, index=True)
    payment_link = Column(String(500), nullable=True)
    created_by_token_id = Column(Integer, ForeignKey("api_tokens.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    metadata = Column(Text, nullable=True)

    # Relationships
    payments = relationship("Payment", back_populates="invoice")
    token = relationship("APIToken", back_populates="invoices")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    transaction_id = Column(String(100), unique=True, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="DJF")
    payment_method = Column(String(50), nullable=True)
    payer_phone = Column(String(20), nullable=True)
    payer_name = Column(String(200), nullable=True)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.INITIATED, index=True)
    dmoney_reference = Column(String(100), nullable=True)
    dmoney_status_code = Column(String(20), nullable=True)
    dmoney_status_message = Column(Text, nullable=True)
    initiated_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    webhook_data = Column(Text, nullable=True)

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")


class APIToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    api_key = Column(String(64), unique=True, nullable=False, index=True)
    api_secret_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    invoices = relationship("Invoice", back_populates="token")
