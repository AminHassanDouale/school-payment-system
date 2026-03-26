# School Invoice Payment System for Scolapp.com

A production-ready payment system for school invoices where guardians pay through D-Money gateway.

## 🎯 System Overview

This system integrates with your existing **scolapp.com** to handle:
- Automatic invoice creation from scolapp
- Guardian payments through D-Money
- Real-time payment tracking
- Admin dashboard for monitoring

## 📋 Features

### 1. **Token Authentication**
- Secure API tokens for scolapp system integration
- Guardian authentication for payment access

### 2. **Preorder (Invoice Creation)**
- Automatically receive invoices from scolapp
- Store: Student info, Guardian phone, Fee type, Amount, Due date
- Generate unique payment links for guardians

### 3. **Query Order**
- Check payment status in real-time
- Track pending/paid/failed transactions

### 4. **Webhooks**
- Receive D-Money payment confirmations
- Auto-update invoice status
- Send notifications to guardians

### 5. **Dashboard**
- View all payments and transactions
- Monitor pending vs paid invoices
- Revenue analytics and reports
- Guardian payment history

## 🏗️ Architecture

```
Scolapp System → API Token Auth → Create Invoice (Preorder)
                                          ↓
Guardian → Payment Link → D-Money Gateway → Webhook → Update Status
                                                           ↓
                                                   Admin Dashboard
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- MySQL 8.0+
- D-Money merchant account

### Installation

```bash
# Clone repository
git clone https://github.com/AminHassanDouale/school-payment-system.git
cd school-payment-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

### Database Setup

```bash
# Create database
mysql -u root -p -e "CREATE DATABASE school_payments;"

# Run migrations
python -m alembic upgrade head
```

### Run Application

```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📡 API Endpoints

### Authentication
```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "api_key": "your_api_key",
  "api_secret": "your_api_secret"
}

Response: { "access_token": "...", "token_type": "bearer" }
```

### Preorder (Create Invoice)
```http
POST /api/v1/preorder
Authorization: Bearer {token}
Content-Type: application/json

{
  "student_id": "STU001",
  "student_name": "Ahmed Hassan",
  "guardian_phone": "+25361234567",
  "fee_type": "tuition",
  "amount": 5000.00,
  "due_date": "2026-04-30",
  "description": "Q1 2026 Tuition Fee"
}

Response: {
  "order_id": "ORD-20260326-001",
  "payment_link": "https://scolapp.com/pay/ORD-20260326-001",
  "status": "pending"
}
```

### Query Order
```http
GET /api/v1/orders/{order_id}
Authorization: Bearer {token}

Response: {
  "order_id": "ORD-20260326-001",
  "status": "paid",
  "amount": 5000.00,
  "payment_date": "2026-03-26T10:30:00",
  "transaction_id": "DMY-TXN-123456"
}
```

### Webhook (D-Money)
```http
POST /api/v1/webhooks/dmoney
Content-Type: application/json

{
  "order_id": "ORD-20260326-001",
  "transaction_id": "DMY-TXN-123456",
  "status": "success",
  "amount": 5000.00,
  "payment_method": "D-Money Wallet"
}
```

### Dashboard
```http
GET /api/v1/dashboard/stats
GET /api/v1/dashboard/transactions?status=pending
GET /api/v1/dashboard/revenue?period=monthly
GET /api/v1/dashboard/guardian/{phone}/history
```

## 🗄️ Database Schema

### Invoices Table
```sql
- id (primary key)
- order_id (unique)
- student_id
- student_name
- guardian_phone
- fee_type
- amount
- due_date
- status (pending/paid/overdue/cancelled)
- created_at
- updated_at
```

### Payments Table
```sql
- id (primary key)
- invoice_id (foreign key)
- transaction_id
- amount
- payment_method
- status
- paid_at
- webhook_data (JSON)
```

### API Tokens Table
```sql
- id (primary key)
- name (e.g., "Scolapp Main System")
- api_key
- api_secret_hash
- is_active
- created_at
- expires_at
```

## 🔐 Security

- API token authentication for system-to-system calls
- Webhook signature verification from D-Money
- Rate limiting on all endpoints
- SQL injection protection
- HTTPS only in production
- Environment variable for sensitive data

## 📊 Integration with Scolapp.com

### From Scolapp Backend
```python
import requests

# Get token
auth_response = requests.post(
    "https://api.scolapp.com/api/v1/auth/token",
    json={
        "api_key": "your_key",
        "api_secret": "your_secret"
    }
)
token = auth_response.json()["access_token"]

# Create invoice
invoice_response = requests.post(
    "https://api.scolapp.com/api/v1/preorder",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "student_id": "STU001",
        "student_name": "Ahmed Hassan",
        "guardian_phone": "+25361234567",
        "fee_type": "tuition",
        "amount": 5000.00,
        "due_date": "2026-04-30"
    }
)

payment_link = invoice_response.json()["payment_link"]
# Send payment_link to guardian via SMS/email
```

## 🚢 Deployment to Hostinger VPS

```bash
# SSH into VPS
ssh root@187.124.32.203

# Clone and setup
git clone https://github.com/AminHassanDouale/school-payment-system.git
cd school-payment-system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
nano .env

# Setup systemd service
sudo cp deployment/school-payment.service /etc/systemd/system/
sudo systemctl enable school-payment
sudo systemctl start school-payment

# Setup nginx
sudo cp deployment/nginx.conf /etc/nginx/sites-available/payment-api
sudo ln -s /etc/nginx/sites-available/payment-api /etc/nginx/sites-enabled/
sudo systemctl reload nginx
```

## 📱 Guardian Payment Flow

1. Guardian receives SMS: "Invoice for Ahmed Hassan (STU001): 5000 DJF due 30-Apr-2026. Pay now: https://scolapp.com/pay/ORD-001"
2. Clicks link → Redirected to payment page
3. Enters D-Money phone number
4. Completes payment on D-Money
5. Webhook confirms payment
6. Guardian receives confirmation SMS
7. Invoice marked as "paid" in scolapp system

## 📈 Dashboard Features

- **Real-time Stats**: Total revenue, pending payments, overdue invoices
- **Transaction List**: Filterable by status, date, student, fee type
- **Revenue Charts**: Daily/weekly/monthly trends
- **Guardian History**: All payments by a specific guardian
- **Export**: Download reports as CSV/Excel

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: MySQL 8.0
- **Payment Gateway**: D-Money API
- **Authentication**: JWT tokens
- **Documentation**: Auto-generated Swagger/OpenAPI

## 📞 Support

For issues or questions:
- Email: support@scolapp.com
- GitHub Issues: https://github.com/AminHassanDouale/school-payment-system/issues

## 📄 License

Proprietary - Scolapp.com © 2026
