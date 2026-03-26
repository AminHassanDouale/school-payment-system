# Scolapp.com Integration Guide

This guide explains how to integrate the School Payment System into your existing scolapp.com application.

## 🔗 Integration Architecture

```
┌─────────────────┐
│  Scolapp.com    │
│  (Laravel)      │
└────────┬────────┘
         │ API Calls
         │ (HTTP/JSON)
         ▼
┌─────────────────┐      ┌──────────────┐
│ Payment System  │◄────►│   D-Money    │
│    (FastAPI)    │      │   Gateway    │
└────────┬────────┘      └──────────────┘
         │ Webhook
         │ Notifications
         ▼
┌─────────────────┐
│     MySQL       │
│   Database      │
└─────────────────┘
```

## 📋 Integration Steps

### Step 1: Store API Credentials in Scolapp

Add these to your scolapp `.env` file:

```env
# Payment System API
PAYMENT_API_URL=https://api.scolapp.com/api/v1
PAYMENT_API_KEY=your_api_key_from_init_db
PAYMENT_API_SECRET=your_api_secret_from_init_db
```

### Step 2: Create Payment Service in Laravel

Create `app/Services/PaymentService.php`:

```php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class PaymentService
{
    protected $apiUrl;
    protected $apiKey;
    protected $apiSecret;
    protected $accessToken;
    
    public function __construct()
    {
        $this->apiUrl = config('services.payment.api_url');
        $this->apiKey = config('services.payment.api_key');
        $this->apiSecret = config('services.payment.api_secret');
    }
    
    /**
     * Get access token from payment API
     */
    protected function getAccessToken()
    {
        if ($this->accessToken) {
            return $this->accessToken;
        }
        
        try {
            $response = Http::post("{$this->apiUrl}/auth/token", [
                'api_key' => $this->apiKey,
                'api_secret' => $this->apiSecret
            ]);
            
            if ($response->successful()) {
                $data = $response->json();
                $this->accessToken = $data['access_token'];
                return $this->accessToken;
            }
            
            Log::error('Failed to get payment API token', ['response' => $response->body()]);
            throw new \Exception('Failed to authenticate with payment API');
            
        } catch (\Exception $e) {
            Log::error('Payment API authentication error', ['error' => $e->getMessage()]);
            throw $e;
        }
    }
    
    /**
     * Create invoice for student fee
     */
    public function createInvoice($studentId, $studentName, $guardianPhone, $feeType, $amount, $dueDate, $description = null)
    {
        try {
            $token = $this->getAccessToken();
            
            $response = Http::withToken($token)
                ->post("{$this->apiUrl}/preorder", [
                    'student_id' => $studentId,
                    'student_name' => $studentName,
                    'guardian_phone' => $guardianPhone,
                    'fee_type' => $feeType,
                    'amount' => $amount,
                    'due_date' => $dueDate,
                    'description' => $description
                ]);
            
            if ($response->successful()) {
                $data = $response->json();
                
                Log::info('Invoice created', [
                    'order_id' => $data['order_id'],
                    'student_id' => $studentId
                ]);
                
                return [
                    'success' => true,
                    'order_id' => $data['order_id'],
                    'payment_link' => $data['payment_link'],
                    'status' => $data['status'],
                    'amount' => $data['amount']
                ];
            }
            
            Log::error('Failed to create invoice', ['response' => $response->body()]);
            return [
                'success' => false,
                'error' => 'Failed to create invoice'
            ];
            
        } catch (\Exception $e) {
            Log::error('Invoice creation error', ['error' => $e->getMessage()]);
            return [
                'success' => false,
                'error' => $e->getMessage()
            ];
        }
    }
    
    /**
     * Check invoice/order status
     */
    public function checkOrderStatus($orderId)
    {
        try {
            $token = $this->getAccessToken();
            
            $response = Http::withToken($token)
                ->get("{$this->apiUrl}/orders/{$orderId}");
            
            if ($response->successful()) {
                return $response->json();
            }
            
            return null;
            
        } catch (\Exception $e) {
            Log::error('Order status check error', [
                'order_id' => $orderId,
                'error' => $e->getMessage()
            ]);
            return null;
        }
    }
    
    /**
     * Get guardian payment history
     */
    public function getGuardianHistory($guardianPhone)
    {
        try {
            $token = $this->getAccessToken();
            
            $response = Http::withToken($token)
                ->get("{$this->apiUrl}/dashboard/guardian/{$guardianPhone}/history");
            
            if ($response->successful()) {
                return $response->json();
            }
            
            return null;
            
        } catch (\Exception $e) {
            Log::error('Guardian history error', [
                'phone' => $guardianPhone,
                'error' => $e->getMessage()
            ]);
            return null;
        }
    }
}
```

### Step 3: Configure Service in config/services.php

Add to `config/services.php`:

```php
'payment' => [
    'api_url' => env('PAYMENT_API_URL'),
    'api_key' => env('PAYMENT_API_KEY'),
    'api_secret' => env('PAYMENT_API_SECRET'),
],
```

### Step 4: Create Controller for Fee Management

Create `app/Http/Controllers/FeeController.php`:

```php
<?php

namespace App\Http\Controllers;

use App\Services\PaymentService;
use App\Models\Student;
use App\Models\Guardian;
use Illuminate\Http\Request;
use Carbon\Carbon;

class FeeController extends Controller
{
    protected $paymentService;
    
    public function __construct(PaymentService $paymentService)
    {
        $this->paymentService = $paymentService;
    }
    
    /**
     * Generate invoice for student fee
     */
    public function generateInvoice(Request $request)
    {
        $validated = $request->validate([
            'student_id' => 'required|exists:students,id',
            'fee_type' => 'required|in:tuition,books,uniform,transport,meals,activities,exam,registration,other',
            'amount' => 'required|numeric|min:0',
            'due_date' => 'required|date',
            'description' => 'nullable|string'
        ]);
        
        // Get student and guardian info
        $student = Student::findOrFail($validated['student_id']);
        $guardian = $student->guardian;
        
        // Create invoice via payment API
        $result = $this->paymentService->createInvoice(
            $student->student_id,
            $student->full_name,
            $guardian->phone,
            $validated['fee_type'],
            $validated['amount'],
            Carbon::parse($validated['due_date'])->format('Y-m-d'),
            $validated['description'] ?? null
        );
        
        if ($result['success']) {
            // Store order_id in your database for tracking
            // Send SMS to guardian with payment link
            $this->sendPaymentNotification($guardian, $result['payment_link'], $validated['amount']);
            
            return response()->json([
                'success' => true,
                'message' => 'Invoice created successfully',
                'data' => $result
            ]);
        }
        
        return response()->json([
            'success' => false,
            'message' => 'Failed to create invoice',
            'error' => $result['error']
        ], 400);
    }
    
    /**
     * Check payment status
     */
    public function checkStatus($orderId)
    {
        $status = $this->paymentService->checkOrderStatus($orderId);
        
        if ($status) {
            return response()->json([
                'success' => true,
                'data' => $status
            ]);
        }
        
        return response()->json([
            'success' => false,
            'message' => 'Order not found'
        ], 404);
    }
    
    /**
     * Send payment notification to guardian
     */
    protected function sendPaymentNotification($guardian, $paymentLink, $amount)
    {
        // Implement SMS sending logic here
        // Example: Using Twilio or local SMS gateway
        
        $message = "Invoice for {$guardian->student->full_name}: {$amount} DJF. Pay now: {$paymentLink}";
        
        // Send SMS
        // SMS::send($guardian->phone, $message);
    }
}
```

### Step 5: Create Webhook Endpoint in Scolapp

Create `app/Http/Controllers/PaymentWebhookController.php`:

```php
<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Invoice;
use Illuminate\Support\Facades\Log;

class PaymentWebhookController extends Controller
{
    /**
     * Handle webhook from payment system
     */
    public function handle(Request $request)
    {
        // Log webhook data
        Log::info('Payment webhook received', $request->all());
        
        $orderId = $request->input('order_id');
        $status = $request->input('status');
        $transactionId = $request->input('transaction_id');
        
        // Find invoice in your database
        $invoice = Invoice::where('order_id', $orderId)->first();
        
        if (!$invoice) {
            Log::warning('Invoice not found for webhook', ['order_id' => $orderId]);
            return response()->json(['success' => false, 'message' => 'Invoice not found'], 404);
        }
        
        // Update invoice status
        if ($status === 'paid') {
            $invoice->status = 'paid';
            $invoice->paid_at = now();
            $invoice->transaction_id = $transactionId;
            $invoice->save();
            
            // Send confirmation to guardian
            $this->sendPaymentConfirmation($invoice);
            
            Log::info('Invoice marked as paid', ['order_id' => $orderId]);
        } elseif ($status === 'failed') {
            $invoice->status = 'failed';
            $invoice->save();
            
            Log::warning('Payment failed', ['order_id' => $orderId]);
        }
        
        return response()->json([
            'success' => true,
            'message' => 'Webhook processed'
        ]);
    }
    
    /**
     * Send payment confirmation
     */
    protected function sendPaymentConfirmation($invoice)
    {
        // Send SMS confirmation
        $message = "Payment received for {$invoice->student_name}. Amount: {$invoice->amount} DJF. Thank you!";
        
        // SMS::send($invoice->guardian_phone, $message);
    }
}
```

### Step 6: Add Routes in routes/web.php or routes/api.php

```php
use App\Http\Controllers\FeeController;
use App\Http\Controllers\PaymentWebhookController;

// Protected routes (require authentication)
Route::middleware(['auth'])->group(function () {
    Route::post('/fees/generate-invoice', [FeeController::class, 'generateInvoice']);
    Route::get('/fees/check-status/{orderId}', [FeeController::class, 'checkStatus']);
});

// Webhook endpoint (no auth - secured by payment system signature)
Route::post('/webhooks/payment', [PaymentWebhookController::class, 'handle']);
```

### Step 7: Create Database Migration for Invoice Tracking

```php
php artisan make:migration create_payment_invoices_table
```

```php
<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up()
    {
        Schema::create('payment_invoices', function (Blueprint $table) {
            $table->id();
            $table->string('order_id')->unique();
            $table->foreignId('student_id')->constrained();
            $table->string('guardian_phone');
            $table->string('fee_type');
            $table->decimal('amount', 10, 2);
            $table->date('due_date');
            $table->string('status')->default('pending');
            $table->string('transaction_id')->nullable();
            $table->timestamp('paid_at')->nullable();
            $table->text('payment_link')->nullable();
            $table->timestamps();
        });
    }
    
    public function down()
    {
        Schema::dropIfExists('payment_invoices');
    }
};
```

## 📱 Usage Example in Scolapp

### Generate Invoice When Fee is Created

```php
// In your FeeAssignment creation logic
$paymentService = new PaymentService();

$result = $paymentService->createInvoice(
    $student->student_id,           // "STU001"
    $student->full_name,             // "Ahmed Hassan"
    $student->guardian->phone,       // "+25361234567"
    'tuition',                       // fee type
    5000.00,                         // amount in DJF
    '2026-04-30',                    // due date
    'Q1 2026 Tuition Fee'           // description
);

if ($result['success']) {
    // Store order_id and payment_link
    PaymentInvoice::create([
        'order_id' => $result['order_id'],
        'student_id' => $student->id,
        'guardian_phone' => $student->guardian->phone,
        'fee_type' => 'tuition',
        'amount' => 5000.00,
        'due_date' => '2026-04-30',
        'payment_link' => $result['payment_link']
    ]);
    
    // Send SMS to guardian
    SMS::send($student->guardian->phone, 
        "New invoice for {$student->full_name}: 5000 DJF due 30-Apr-2026. Pay: {$result['payment_link']}"
    );
}
```

## 🔔 Webhook Flow

1. Guardian clicks payment link
2. Completes payment on D-Money
3. D-Money sends webhook to payment system
4. Payment system updates invoice status
5. Payment system sends webhook to scolapp
6. Scolapp updates local database
7. Scolapp sends confirmation SMS to guardian

## 🧪 Testing Integration

Test the integration locally:

```bash
# Test authentication
curl -X POST https://api.scolapp.com/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your_key", "api_secret": "your_secret"}'

# Test invoice creation (use token from above)
curl -X POST https://api.scolapp.com/api/v1/preorder \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "STU001",
    "student_name": "Ahmed Hassan",
    "guardian_phone": "+25361234567",
    "fee_type": "tuition",
    "amount": 5000.00,
    "due_date": "2026-04-30"
  }'
```

## 📊 Dashboard Integration

You can also fetch dashboard data to show in scolapp admin panel:

```php
$paymentService = new PaymentService();
$stats = $paymentService->getDashboardStats();

// Returns:
// {
//   "total_invoices": 150,
//   "paid_invoices": 100,
//   "pending_invoices": 50,
//   "total_revenue": 500000.00,
//   "this_month_revenue": 75000.00
// }
```

## 🔐 Security Notes

1. Never commit API credentials to version control
2. Use HTTPS for all API calls
3. Verify webhook signatures
4. Rate limit API calls
5. Log all payment transactions
6. Monitor for suspicious activity

## 📞 Support

For integration issues:
- Check logs: `/var/log/school-payment/`
- API docs: `https://api.scolapp.com/api/v1/docs`
- Webhook test: `https://api.scolapp.com/api/v1/webhooks/test`
