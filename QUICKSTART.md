# Quick Start Guide

Get your School Payment System up and running in minutes!

## 🚀 Quick Deployment (5 Steps)

### Step 1: Clone Repository on VPS

```bash
ssh root@187.124.32.203

cd /var/www
git clone https://github.com/AminHassanDouale/school-payment-system.git
cd school-payment-system
```

### Step 2: Run Deployment Script

```bash
chmod +x deployment/deploy.sh
sudo ./deployment/deploy.sh
```

The script will:
- ✅ Install all dependencies
- ✅ Setup virtual environment
- ✅ Create log directories
- ✅ Configure Nginx
- ✅ Setup systemd service
- ✅ Start the application

### Step 3: Configure Environment

Edit the `.env` file with your actual credentials:

```bash
nano .env
```

**Required changes:**
```env
# Database
DATABASE_URL=mysql+pymysql://root:YOUR_MYSQL_PASSWORD@localhost:3306/school_payments

# Security
SECRET_KEY=GENERATE_NEW_SECRET_KEY_HERE

# D-Money (get from D-Money merchant dashboard)
DMONEY_MERCHANT_ID=your_merchant_id
DMONEY_API_KEY=your_api_key
DMONEY_API_SECRET=your_api_secret
DMONEY_WEBHOOK_SECRET=your_webhook_secret

# URLs
PAYMENT_CALLBACK_URL=https://api.scolapp.com/api/v1/webhooks/dmoney
SCOLAPP_DOMAIN=https://scolapp.com

# Production settings
ENVIRONMENT=production
DEBUG=False
```

**Generate a secure SECRET_KEY:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### Step 4: Initialize Database

```bash
# Create MySQL database
mysql -u root -p -e "CREATE DATABASE school_payments CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Run initialization script
python init_db.py
```

**Save the API credentials** that are displayed! You'll need them for scolapp integration.

### Step 5: Setup SSL & Start

```bash
# Setup SSL certificate (if not already done)
sudo certbot --nginx -d api.scolapp.com

# Restart services
sudo systemctl restart school-payment
sudo systemctl restart nginx

# Verify it's running
curl https://api.scolapp.com/health
```

## ✅ Verify Installation

### Test API Endpoints

```bash
# Health check
curl https://api.scolapp.com/health

# API info
curl https://api.scolapp.com/api/v1/info

# View documentation
# Open in browser: https://api.scolapp.com/api/v1/docs
```

### Test Authentication

```bash
# Use the API credentials from init_db.py
curl -X POST https://api.scolapp.com/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "YOUR_API_KEY",
    "api_secret": "YOUR_API_SECRET"
  }'
```

You should get a response with an `access_token`.

### Test Invoice Creation

```bash
# Save token from previous step
export TOKEN="your_access_token_here"

# Create test invoice
curl -X POST https://api.scolapp.com/api/v1/preorder \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "TEST001",
    "student_name": "Test Student",
    "guardian_phone": "+25361234567",
    "fee_type": "tuition",
    "amount": 1000.00,
    "due_date": "2026-04-30",
    "description": "Test invoice"
  }'
```

## 🔗 Integrate with Scolapp

### 1. Add to Scolapp .env

```env
PAYMENT_API_URL=https://api.scolapp.com/api/v1
PAYMENT_API_KEY=your_api_key_from_init_db
PAYMENT_API_SECRET=your_api_secret_from_init_db
```

### 2. Add to config/services.php

```php
'payment' => [
    'api_url' => env('PAYMENT_API_URL'),
    'api_key' => env('PAYMENT_API_KEY'),
    'api_secret' => env('PAYMENT_API_SECRET'),
],
```

### 3. Create PaymentService

Copy the PaymentService class from `INTEGRATION_GUIDE.md` to:
```
app/Services/PaymentService.php
```

### 4. Use in Your Code

```php
use App\Services\PaymentService;

$paymentService = new PaymentService();

$result = $paymentService->createInvoice(
    $student->student_id,
    $student->full_name,
    $guardian->phone,
    'tuition',
    5000.00,
    '2026-04-30',
    'Q1 2026 Tuition'
);

if ($result['success']) {
    // Send SMS with payment link
    SMS::send($guardian->phone, "Pay now: {$result['payment_link']}");
}
```

## 📱 Guardian Payment Flow

1. **Guardian receives SMS:**
   ```
   Invoice for Ahmed Hassan: 5000 DJF due 30-Apr-2026
   Pay now: https://scolapp.com/pay/ORD-20260326-ABC123
   ```

2. **Clicks link → D-Money payment page**

3. **Completes payment**

4. **System automatically:**
   - Updates invoice to "paid"
   - Sends confirmation SMS
   - Updates scolapp database

## 🔍 Monitoring & Logs

### View Application Logs

```bash
# Real-time logs
sudo journalctl -u school-payment -f

# Last 100 lines
sudo journalctl -u school-payment -n 100

# Application logs
tail -f /var/www/school-payment-system/logs/app.log
```

### View Nginx Logs

```bash
# Error log
sudo tail -f /var/log/nginx/payment-api-error.log

# Access log
sudo tail -f /var/log/nginx/payment-api-access.log
```

### Check Service Status

```bash
# Payment service
sudo systemctl status school-payment

# Nginx
sudo systemctl status nginx

# MySQL
sudo systemctl status mysql
```

## 🛠️ Common Tasks

### Restart Service After Code Changes

```bash
cd /var/www/school-payment-system
git pull origin main
sudo systemctl restart school-payment
```

### Update Dependencies

```bash
cd /var/www/school-payment-system
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart school-payment
```

### Backup Database

```bash
mysqldump -u root -p school_payments > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Database

```bash
mysql -u root -p school_payments < backup_20260326_120000.sql
```

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check logs for errors
sudo journalctl -u school-payment -n 50

# Common issues:
# - Database connection error → Check .env DATABASE_URL
# - Port already in use → Check if another service is on port 8000
# - Permission denied → Check file ownership: sudo chown -R www-data:www-data /var/www/school-payment-system
```

### Can't Connect to Database

```bash
# Test MySQL connection
mysql -u root -p school_payments

# If fails, check:
# - MySQL is running: sudo systemctl status mysql
# - Database exists: SHOW DATABASES;
# - User has permissions: SHOW GRANTS FOR 'your_user'@'localhost';
```

### 502 Bad Gateway

```bash
# Check if app is running
sudo systemctl status school-payment

# Check if port 8000 is listening
sudo netstat -tlnp | grep 8000

# Restart both services
sudo systemctl restart school-payment
sudo systemctl restart nginx
```

### Webhooks Not Working

```bash
# Test webhook endpoint
curl https://api.scolapp.com/api/v1/webhooks/test

# Check webhook logs
grep "webhook" /var/www/school-payment-system/logs/app.log

# Verify D-Money webhook URL is set to:
# https://api.scolapp.com/api/v1/webhooks/dmoney
```

## 📚 Next Steps

1. **Read Full Documentation:**
   - `README.md` - Overview and features
   - `INTEGRATION_GUIDE.md` - Complete scolapp integration
   - `API_TESTING.md` - API examples and testing
   - `DEPLOYMENT_CHECKLIST.md` - Production checklist

2. **Configure D-Money:**
   - Login to D-Money merchant dashboard
   - Add webhook URL
   - Test with sandbox mode
   - Switch to production mode

3. **Setup Monitoring:**
   - Configure uptime monitoring
   - Setup error alerting
   - Create backup schedule
   - Document recovery procedures

4. **Train Your Team:**
   - How to view dashboard
   - How to check payment status
   - How to handle failed payments
   - Emergency contacts

## 🎯 Success Checklist

- [ ] API is accessible at https://api.scolapp.com
- [ ] Health check returns {"status": "healthy"}
- [ ] Can authenticate and get token
- [ ] Can create test invoice
- [ ] Can query order status
- [ ] Webhooks are working
- [ ] Scolapp can create invoices
- [ ] Guardian can pay through D-Money
- [ ] Dashboard shows correct data
- [ ] SSL certificate is valid
- [ ] Logs are being written
- [ ] Backups are configured

## 📞 Support

**Documentation:** Check the docs folder for detailed guides

**Logs Location:**
- Application: `/var/www/school-payment-system/logs/app.log`
- Service: `sudo journalctl -u school-payment`
- Nginx: `/var/log/nginx/payment-api-error.log`

**Useful Commands:**
```bash
# Service management
sudo systemctl {start|stop|restart|status} school-payment

# View live logs
sudo journalctl -u school-payment -f

# Test API
curl https://api.scolapp.com/health

# Access documentation
open https://api.scolapp.com/api/v1/docs
```

---

## 🎉 You're All Set!

Your School Payment System is now running and ready to process guardian payments through D-Money!

**What's Next?**
1. Integrate with scolapp.com (see INTEGRATION_GUIDE.md)
2. Configure D-Money webhooks
3. Test the complete payment flow
4. Train your staff
5. Go live!

Good luck! 🚀
