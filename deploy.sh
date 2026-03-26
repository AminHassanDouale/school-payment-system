#!/bin/bash

# School Payment System Deployment Script
# This script deploys/updates the payment system on your VPS

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/var/www/school-payment-system"
REPO_URL="https://github.com/AminHassanDouale/school-payment-system.git"
VENV_DIR="$PROJECT_DIR/venv"
SERVICE_NAME="school-payment"
LOG_DIR="/var/log/school-payment"

echo "=========================================="
echo "School Payment System - Deployment Script"
echo "=========================================="
echo ""

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root (use sudo)"
    exit 1
fi

# Step 1: Install/Update System Dependencies
print_info "Installing system dependencies..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git nginx mysql-server curl -qq
print_success "System dependencies installed"

# Step 2: Create project directory and clone/update repository
if [ -d "$PROJECT_DIR" ]; then
    print_info "Updating existing installation..."
    cd $PROJECT_DIR
    
    # Backup .env file
    if [ -f ".env" ]; then
        cp .env .env.backup
        print_success "Environment file backed up"
    fi
    
    # Stop service before update
    systemctl stop $SERVICE_NAME 2>/dev/null || true
    
    # Pull latest changes
    git pull origin main
    print_success "Code updated from repository"
    
    # Restore .env file
    if [ -f ".env.backup" ]; then
        mv .env.backup .env
        print_success "Environment file restored"
    fi
else
    print_info "Fresh installation - cloning repository..."
    mkdir -p $PROJECT_DIR
    git clone $REPO_URL $PROJECT_DIR
    cd $PROJECT_DIR
    print_success "Repository cloned"
fi

# Step 3: Create/Update virtual environment
print_info "Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv $VENV_DIR
    print_success "Virtual environment created"
else
    print_success "Virtual environment exists"
fi

# Activate virtual environment and install dependencies
source $VENV_DIR/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
print_success "Python dependencies installed"

# Step 4: Setup environment file if not exists
if [ ! -f ".env" ]; then
    print_info "Creating .env file from template..."
    cp .env.example .env
    print_error "IMPORTANT: Edit .env file with your actual credentials!"
    echo ""
    echo "Run: nano $PROJECT_DIR/.env"
    echo ""
    read -p "Press Enter after you've configured .env file..."
fi

# Step 5: Create log directory
print_info "Creating log directory..."
mkdir -p $LOG_DIR
chown -R www-data:www-data $LOG_DIR
mkdir -p $PROJECT_DIR/logs
chown -R www-data:www-data $PROJECT_DIR/logs
print_success "Log directory created"

# Step 6: Database setup prompt
echo ""
print_info "Database Setup"
echo "Have you created the MySQL database? (yes/no)"
read -p "> " db_created

if [ "$db_created" != "yes" ]; then
    print_info "Creating database..."
    mysql -e "CREATE DATABASE IF NOT EXISTS school_payments CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    print_success "Database created"
    
    print_info "Running database initialization..."
    python init_db.py
fi

# Step 7: Setup systemd service
print_info "Configuring systemd service..."
cp deployment/school-payment.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable $SERVICE_NAME
print_success "Systemd service configured"

# Step 8: Setup Nginx
print_info "Configuring Nginx..."
cp deployment/nginx.conf /etc/nginx/sites-available/payment-api
ln -sf /etc/nginx/sites-available/payment-api /etc/nginx/sites-enabled/
nginx -t
print_success "Nginx configured"

# Step 9: Set correct permissions
print_info "Setting permissions..."
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR
print_success "Permissions set"

# Step 10: Start services
print_info "Starting services..."
systemctl restart $SERVICE_NAME
systemctl restart nginx
print_success "Services started"

# Step 11: Verify installation
echo ""
print_info "Verifying installation..."
sleep 3

# Check if service is running
if systemctl is-active --quiet $SERVICE_NAME; then
    print_success "Payment service is running"
else
    print_error "Payment service failed to start"
    echo "Check logs: journalctl -u $SERVICE_NAME -n 50"
fi

# Check if Nginx is running
if systemctl is-active --quiet nginx; then
    print_success "Nginx is running"
else
    print_error "Nginx failed to start"
fi

# Test API endpoint
print_info "Testing API endpoint..."
sleep 2
if curl -f -s http://localhost:8000/health > /dev/null; then
    print_success "API is responding"
else
    print_error "API is not responding"
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
print_success "Payment system deployed successfully"
echo ""
echo "📋 Next Steps:"
echo "1. Configure your domain DNS to point to this server"
echo "2. Setup SSL certificate (if not already done):"
echo "   sudo certbot --nginx -d api.scolapp.com"
echo "3. Test the API endpoints:"
echo "   curl https://api.scolapp.com/health"
echo "4. Check the documentation:"
echo "   https://api.scolapp.com/api/v1/docs"
echo ""
echo "📊 Useful Commands:"
echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  Check status:    sudo systemctl status $SERVICE_NAME"
echo "  Nginx logs:      sudo tail -f /var/log/nginx/payment-api-error.log"
echo ""
echo "🔐 Security Checklist:"
echo "  ✓ Update .env with real credentials"
echo "  ✓ Setup firewall (ufw allow 80,443/tcp)"
echo "  ✓ Setup SSL certificate"
echo "  ✓ Restrict /docs endpoint in Nginx (production)"
echo ""
