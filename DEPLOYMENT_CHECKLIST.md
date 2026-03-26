# Deployment Checklist

Complete this checklist when deploying to production.

## 📋 Pre-Deployment

### Local Development
- [ ] All code tested locally
- [ ] Database migrations tested
- [ ] API endpoints tested
- [ ] Webhook simulation tested
- [ ] Environment variables configured
- [ ] Dependencies up to date
- [ ] .gitignore properly configured
- [ ] No sensitive data in code

### GitHub Repository
- [ ] Code pushed to GitHub
- [ ] Repository is private (if needed)
- [ ] README.md updated
- [ ] .env.example has all required variables
- [ ] Deployment scripts are executable

## 🖥️ VPS Setup

### Initial Server Configuration
- [ ] VPS created and accessible
- [ ] SSH access configured
- [ ] Firewall configured (ports 80, 443, 22)
- [ ] Server timezone set correctly
- [ ] Server hostname set

### Required Software
- [ ] Python 3.9+ installed
- [ ] MySQL 8.0+ installed
- [ ] Nginx installed
- [ ] Git installed
- [ ] Certbot installed (for SSL)

### MySQL Database
- [ ] Database created (`school_payments`)
- [ ] Database user created with proper permissions
- [ ] Database connection tested
- [ ] Character set is utf8mb4
- [ ] Collation is utf8mb4_unicode_ci

## 🚀 Deployment Steps

### Clone and Setup
- [ ] Repository cloned to `/var/www/school-payment-system`
- [ ] Virtual environment created
- [ ] Python dependencies installed
- [ ] .env file created and configured
- [ ] Log directories created

### Environment Configuration
- [ ] `DATABASE_URL` configured correctly
- [ ] `SECRET_KEY` set (generate new one for production)
- [ ] `DMONEY_*` credentials configured
- [ ] `PAYMENT_CALLBACK_URL` set to production URL
- [ ] `SCOLAPP_DOMAIN` set correctly
- [ ] `DEBUG` set to `False`
- [ ] `ENVIRONMENT` set to `production`

### Database Initialization
- [ ] Database tables created (`python init_db.py`)
- [ ] API token generated and saved
- [ ] Test invoice created (optional)
- [ ] Database permissions verified

### Service Configuration
- [ ] Systemd service file copied
- [ ] Service enabled
- [ ] Service started
- [ ] Service status checked

### Nginx Configuration
- [ ] Nginx config file copied
- [ ] Config syntax tested (`nginx -t`)
- [ ] Symbolic link created in sites-enabled
- [ ] Nginx reloaded

### SSL Certificate
- [ ] DNS records updated (A record)
- [ ] SSL certificate obtained (certbot)
- [ ] Certificate auto-renewal configured
- [ ] HTTPS tested

## ✅ Post-Deployment Verification

### API Health Checks
- [ ] `/health` endpoint responds
- [ ] `/api/v1/info` endpoint responds
- [ ] API documentation accessible (`/api/v1/docs`)
- [ ] Authentication works
- [ ] Can create test invoice
- [ ] Can query order status
- [ ] Webhook endpoint accessible

### Integration Testing
- [ ] Scolapp can authenticate with payment API
- [ ] Scolapp can create invoices
- [ ] Payment links work
- [ ] Webhooks are received
- [ ] Dashboard data loads correctly

### Monitoring & Logging
- [ ] Application logs are being written
- [ ] Nginx logs are accessible
- [ ] Log rotation configured
- [ ] Monitoring setup (optional)

### Security Checklist
- [ ] Firewall configured properly
- [ ] SSH key authentication enabled
- [ ] Password authentication disabled
- [ ] API rate limiting enabled
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] Security headers configured
- [ ] Database passwords are strong
- [ ] API secrets are secure and unique

## 🔐 D-Money Configuration

### D-Money Account Setup
- [ ] D-Money merchant account created
- [ ] Merchant ID obtained
- [ ] API credentials obtained
- [ ] Webhook URL registered with D-Money
- [ ] Test transactions completed
- [ ] Production mode enabled

### Webhook Configuration
- [ ] Webhook URL: `https://api.scolapp.com/api/v1/webhooks/dmoney`
- [ ] Webhook secret configured
- [ ] Signature verification tested
- [ ] Test webhook sent successfully

## 🔧 Scolapp Integration

### API Credentials
- [ ] API key saved in scolapp .env
- [ ] API secret saved in scolapp .env
- [ ] Payment API URL configured
- [ ] PaymentService class implemented
- [ ] Routes configured
- [ ] Webhook endpoint created

### Testing from Scolapp
- [ ] Can authenticate with payment API
- [ ] Can create invoices from scolapp
- [ ] Guardian receives payment link
- [ ] Payment flow works end-to-end
- [ ] Webhook updates scolapp database

## 📱 Guardian Experience

### Payment Flow
- [ ] Guardian receives SMS with payment link
- [ ] Payment link opens correctly
- [ ] D-Money payment page loads
- [ ] Payment can be completed
- [ ] Confirmation SMS is sent
- [ ] Invoice status updates in scolapp

## 📊 Dashboard & Reporting

### Admin Access
- [ ] Dashboard stats load correctly
- [ ] Transaction list displays properly
- [ ] Revenue charts render
- [ ] Guardian history works
- [ ] Pagination works
- [ ] Filters work correctly

## 🔄 Backup & Recovery

### Backup Strategy
- [ ] Database backup script created
- [ ] Backup cron job configured
- [ ] Backup location secured
- [ ] Restore procedure tested
- [ ] .env file backed up securely

### Recovery Plan
- [ ] Rollback procedure documented
- [ ] Previous version backup exists
- [ ] Recovery time objective defined
- [ ] Contact list for emergencies

## 📞 Support & Documentation

### Documentation
- [ ] API documentation accessible
- [ ] Integration guide reviewed
- [ ] Testing guide available
- [ ] Troubleshooting guide created

### Support Contacts
- [ ] D-Money support contact saved
- [ ] VPS provider support contact saved
- [ ] Developer contact information documented
- [ ] Escalation procedure defined

## 🎯 Go-Live Checklist

### Final Verification (15 minutes before go-live)
- [ ] All services running
- [ ] No errors in logs
- [ ] Test transaction successful
- [ ] Monitoring active
- [ ] Team notified
- [ ] Rollback plan ready

### Go-Live Steps
- [ ] Make repository/API live
- [ ] Monitor initial requests
- [ ] Watch logs for errors
- [ ] Verify first real transaction
- [ ] Send test SMS
- [ ] Confirm webhook delivery

### Post Go-Live (First 24 hours)
- [ ] Monitor error rates
- [ ] Check payment success rates
- [ ] Review webhook delivery
- [ ] Verify guardian notifications
- [ ] Check dashboard accuracy
- [ ] Gather initial feedback

## 🐛 Common Issues & Solutions

### Service won't start
```bash
sudo journalctl -u school-payment -n 50
# Check for Python errors, database connection, missing dependencies
```

### Database connection errors
```bash
# Test connection
mysql -u user -p school_payments
# Check .env DATABASE_URL
# Verify MySQL is running: sudo systemctl status mysql
```

### Nginx 502 errors
```bash
# Check if service is running
sudo systemctl status school-payment
# Check port 8000 is listening
sudo netstat -tlnp | grep 8000
```

### Webhooks not received
- Check D-Money webhook configuration
- Verify URL is publicly accessible
- Check firewall rules
- Review webhook logs

### Payment links don't work
- Verify PAYMENT_SUCCESS_URL and PAYMENT_CANCEL_URL
- Check D-Money integration
- Test with D-Money sandbox first

## 📝 Notes

**Deployment Date:** _________________

**Deployed By:** _________________

**Version:** _________________

**Environment:** Production / Staging

**Special Considerations:**
- _________________________________
- _________________________________
- _________________________________

**Known Issues:**
- _________________________________
- _________________________________

**Next Review Date:** _________________

---

## ✨ Deployment Complete!

Once all items are checked, your School Payment System is ready for production use.

**Quick Access Links:**
- API: https://api.scolapp.com
- Docs: https://api.scolapp.com/api/v1/docs
- Health: https://api.scolapp.com/health

**Important Commands:**
```bash
# View logs
sudo journalctl -u school-payment -f

# Restart service
sudo systemctl restart school-payment

# Check status
sudo systemctl status school-payment

# Database backup
mysqldump -u root -p school_payments > backup_$(date +%Y%m%d).sql
```

Good luck! 🚀
