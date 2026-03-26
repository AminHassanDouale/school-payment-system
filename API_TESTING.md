# API Testing Examples

This document contains examples for testing all API endpoints.

## 🔐 Authentication

### Get Access Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "your_api_key",
    "api_secret": "your_api_secret"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Save the token for subsequent requests:**
```bash
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## 📝 Preorder (Create Invoice)

### Create Single Invoice

```bash
curl -X POST http://localhost:8000/api/v1/preorder \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "STU001",
    "student_name": "Ahmed Hassan Mohamed",
    "guardian_phone": "+25361234567",
    "guardian_email": "parent@example.com",
    "fee_type": "tuition",
    "amount": 5000.00,
    "due_date": "2026-04-30",
    "description": "Q1 2026 Tuition Fee"
  }'
```

**Response:**
```json
{
  "success": true,
  "order_id": "ORD-20260326-A1B2C3D4",
  "payment_link": "https://scolapp.com/pay/ORD-20260326-A1B2C3D4",
  "status": "pending",
  "amount": 5000.0,
  "currency": "DJF",
  "due_date": "2026-04-30",
  "message": "Invoice created successfully. Payment link sent to guardian."
}
```

### Create Multiple Fee Types

```bash
# Books fee
curl -X POST http://localhost:8000/api/v1/preorder \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "STU001",
    "student_name": "Ahmed Hassan Mohamed",
    "guardian_phone": "+25361234567",
    "fee_type": "books",
    "amount": 1500.00,
    "due_date": "2026-03-31",
    "description": "Textbooks for Q1 2026"
  }'

# Uniform fee
curl -X POST http://localhost:8000/api/v1/preorder \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "STU001",
    "student_name": "Ahmed Hassan Mohamed",
    "guardian_phone": "+25361234567",
    "fee_type": "uniform",
    "amount": 2000.00,
    "due_date": "2026-03-31",
    "description": "School uniform 2026"
  }'
```

## 🔍 Query Orders

### Get Single Order Status

```bash
curl -X GET "http://localhost:8000/api/v1/orders/ORD-20260326-A1B2C3D4" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "order_id": "ORD-20260326-A1B2C3D4",
  "status": "pending",
  "student_name": "Ahmed Hassan Mohamed",
  "guardian_phone": "+25361234567",
  "fee_type": "tuition",
  "amount": 5000.0,
  "currency": "DJF",
  "due_date": "2026-04-30",
  "created_at": "2026-03-26T10:30:00",
  "paid_at": null,
  "transaction_id": null,
  "payment_method": null
}
```

### Query Orders with Filters

```bash
# By student ID
curl -X GET "http://localhost:8000/api/v1/orders?student_id=STU001" \
  -H "Authorization: Bearer $TOKEN"

# By guardian phone
curl -X GET "http://localhost:8000/api/v1/orders?guardian_phone=%2B25361234567" \
  -H "Authorization: Bearer $TOKEN"

# By status
curl -X GET "http://localhost:8000/api/v1/orders?status=pending&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

## 🔔 Webhooks

### Test Webhook Endpoint

```bash
curl -X GET http://localhost:8000/api/v1/webhooks/test
```

### Simulate D-Money Payment Webhook (Success)

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/dmoney \
  -H "Content-Type: application/json" \
  -H "X-Signature: your_webhook_signature" \
  -d '{
    "order_id": "ORD-20260326-A1B2C3D4",
    "transaction_id": "DMY-TXN-123456789",
    "status": "success",
    "amount": 5000.00,
    "currency": "DJF",
    "payment_method": "D-Money Wallet",
    "payer_phone": "+25361234567",
    "payer_name": "Ibrahim Ahmed",
    "reference": "REF-123456",
    "status_code": "00",
    "status_message": "Payment successful",
    "timestamp": "2026-03-26T10:45:00"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Webhook processed successfully",
  "order_id": "ORD-20260326-A1B2C3D4",
  "status": "paid"
}
```

### Simulate Payment Failure

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/dmoney \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-20260326-A1B2C3D4",
    "transaction_id": "DMY-TXN-987654321",
    "status": "failed",
    "amount": 5000.00,
    "status_code": "05",
    "status_message": "Insufficient balance"
  }'
```

## 📊 Dashboard

### Get Dashboard Statistics

```bash
curl -X GET http://localhost:8000/api/v1/dashboard/stats \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "total_invoices": 150,
  "pending_invoices": 45,
  "paid_invoices": 100,
  "overdue_invoices": 5,
  "total_revenue": 750000.0,
  "pending_amount": 225000.0,
  "today_revenue": 25000.0,
  "this_month_revenue": 500000.0,
  "currency": "DJF"
}
```

### Get Transaction List

```bash
# All transactions
curl -X GET "http://localhost:8000/api/v1/dashboard/transactions?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"

# Pending only
curl -X GET "http://localhost:8000/api/v1/dashboard/transactions?status=pending&page=1&page_size=50" \
  -H "Authorization: Bearer $TOKEN"

# Paid only
curl -X GET "http://localhost:8000/api/v1/dashboard/transactions?status=paid" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Revenue Analytics

```bash
# Daily revenue (last 30 days)
curl -X GET "http://localhost:8000/api/v1/dashboard/revenue?period=daily" \
  -H "Authorization: Bearer $TOKEN"

# Weekly revenue (last 12 weeks)
curl -X GET "http://localhost:8000/api/v1/dashboard/revenue?period=weekly" \
  -H "Authorization: Bearer $TOKEN"

# Monthly revenue (last 12 months)
curl -X GET "http://localhost:8000/api/v1/dashboard/revenue?period=monthly" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "period": "monthly",
  "data": [
    {
      "date": "2026-01",
      "revenue": 450000.0,
      "count": 90
    },
    {
      "date": "2026-02",
      "revenue": 520000.0,
      "count": 104
    },
    {
      "date": "2026-03",
      "revenue": 500000.0,
      "count": 100
    }
  ],
  "total_revenue": 1470000.0,
  "total_transactions": 294
}
```

### Get Guardian Payment History

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/guardian/%2B25361234567/history" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "guardian_phone": "+25361234567",
  "total_invoices": 12,
  "paid_invoices": 10,
  "pending_invoices": 2,
  "total_paid": 50000.0,
  "total_pending": 10000.0,
  "transactions": [
    {
      "id": 1,
      "order_id": "ORD-20260326-A1B2C3D4",
      "student_name": "Ahmed Hassan Mohamed",
      "guardian_phone": "+25361234567",
      "fee_type": "tuition",
      "amount": 5000.0,
      "status": "paid",
      "due_date": "2026-04-30T00:00:00",
      "created_at": "2026-03-26T10:30:00",
      "paid_at": "2026-03-26T10:45:00",
      "transaction_id": "DMY-TXN-123456789"
    }
  ]
}
```

## 🐍 Python Testing Script

Save as `test_api.py`:

```python
import requests
import json

# Configuration
API_URL = "http://localhost:8000/api/v1"
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"

class PaymentAPITester:
    def __init__(self):
        self.api_url = API_URL
        self.token = None
    
    def authenticate(self):
        """Get access token"""
        response = requests.post(
            f"{self.api_url}/auth/token",
            json={
                "api_key": API_KEY,
                "api_secret": API_SECRET
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            print("✓ Authentication successful")
            return True
        else:
            print(f"✗ Authentication failed: {response.text}")
            return False
    
    def create_invoice(self, student_id, student_name, guardian_phone, fee_type, amount, due_date):
        """Create a new invoice"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.post(
            f"{self.api_url}/preorder",
            headers=headers,
            json={
                "student_id": student_id,
                "student_name": student_name,
                "guardian_phone": guardian_phone,
                "fee_type": fee_type,
                "amount": amount,
                "due_date": due_date
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Invoice created: {data['order_id']}")
            print(f"  Payment link: {data['payment_link']}")
            return data['order_id']
        else:
            print(f"✗ Invoice creation failed: {response.text}")
            return None
    
    def check_order(self, order_id):
        """Check order status"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.get(
            f"{self.api_url}/orders/{order_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Order status: {data['status']}")
            print(f"  Amount: {data['amount']} {data['currency']}")
            return data
        else:
            print(f"✗ Order check failed: {response.text}")
            return None
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        headers = {"Authorization": f"Bearer {self.token}"}
        
        response = requests.get(
            f"{self.api_url}/dashboard/stats",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Dashboard Stats:")
            print(f"  Total invoices: {data['total_invoices']}")
            print(f"  Paid: {data['paid_invoices']}")
            print(f"  Pending: {data['pending_invoices']}")
            print(f"  Total revenue: {data['total_revenue']} {data['currency']}")
            return data
        else:
            print(f"✗ Dashboard fetch failed: {response.text}")
            return None

# Run tests
if __name__ == "__main__":
    tester = PaymentAPITester()
    
    # Authenticate
    if tester.authenticate():
        print("\n--- Testing Invoice Creation ---")
        order_id = tester.create_invoice(
            student_id="STU001",
            student_name="Ahmed Hassan Mohamed",
            guardian_phone="+25361234567",
            fee_type="tuition",
            amount=5000.00,
            due_date="2026-04-30"
        )
        
        if order_id:
            print("\n--- Checking Order Status ---")
            tester.check_order(order_id)
        
        print("\n--- Getting Dashboard Stats ---")
        tester.get_dashboard_stats()
```

Run the script:
```bash
python test_api.py
```

## 📋 Testing Checklist

- [ ] Authentication works with valid credentials
- [ ] Authentication fails with invalid credentials
- [ ] Can create invoice for each fee type
- [ ] Phone number validation works
- [ ] Date validation works
- [ ] Query order by order_id works
- [ ] Query orders with filters works
- [ ] Webhook updates invoice status correctly
- [ ] Dashboard stats are accurate
- [ ] Revenue analytics returns correct data
- [ ] Guardian history shows all invoices
- [ ] API returns proper error messages
- [ ] Token expiration is handled correctly

## 🔍 Debugging Tips

1. **Check logs:**
   ```bash
   tail -f logs/app.log
   sudo journalctl -u school-payment -f
   ```

2. **Test database connection:**
   ```bash
   mysql -u root -p school_payments -e "SELECT COUNT(*) FROM invoices;"
   ```

3. **Verify service is running:**
   ```bash
   sudo systemctl status school-payment
   curl http://localhost:8000/health
   ```

4. **Check Nginx:**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   tail -f /var/log/nginx/payment-api-error.log
   ```
