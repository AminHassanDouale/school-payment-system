import httpx
import hashlib
import hmac
import json
from datetime import datetime
from typing import Dict, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class DMoneyGateway:
    """D-Money Payment Gateway Integration"""
    
    def __init__(self):
        self.api_url = settings.DMONEY_API_URL
        self.merchant_id = settings.DMONEY_MERCHANT_ID
        self.api_key = settings.DMONEY_API_KEY
        self.api_secret = settings.DMONEY_API_SECRET
        self.webhook_secret = settings.DMONEY_WEBHOOK_SECRET
    
    def _generate_signature(self, payload: Dict) -> str:
        """Generate HMAC signature for D-Money API"""
        # Sort payload keys and create signature string
        sorted_keys = sorted(payload.keys())
        signature_string = "&".join([f"{k}={payload[k]}" for k in sorted_keys])
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for D-Money API"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-Merchant-ID": self.merchant_id
        }
    
    async def create_payment_request(
        self,
        order_id: str,
        amount: float,
        guardian_phone: str,
        description: str,
        student_name: str
    ) -> Dict:
        """
        Create a payment request in D-Money
        
        Args:
            order_id: Unique order identifier
            amount: Payment amount in DJF
            guardian_phone: Guardian's phone number
            description: Payment description
            student_name: Student name for reference
            
        Returns:
            Dict with payment_url, transaction_id, and status
        """
        try:
            payload = {
                "merchant_id": self.merchant_id,
                "order_id": order_id,
                "amount": amount,
                "currency": settings.PAYMENT_CURRENCY,
                "customer_phone": guardian_phone,
                "description": description,
                "customer_name": student_name,
                "callback_url": settings.PAYMENT_CALLBACK_URL,
                "success_url": f"{settings.PAYMENT_SUCCESS_URL}?order_id={order_id}",
                "cancel_url": f"{settings.PAYMENT_CANCEL_URL}?order_id={order_id}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Generate signature
            payload["signature"] = self._generate_signature(payload)
            
            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/payment/create",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Payment request created for order {order_id}: {result}")
                
                return {
                    "success": True,
                    "payment_url": result.get("payment_url"),
                    "transaction_id": result.get("transaction_id"),
                    "status": result.get("status", "initiated"),
                    "message": result.get("message", "Payment request created")
                }
                
        except httpx.HTTPError as e:
            logger.error(f"D-Money API error for order {order_id}: {str(e)}")
            return {
                "success": False,
                "error": "Payment gateway error",
                "detail": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error creating payment for order {order_id}: {str(e)}")
            return {
                "success": False,
                "error": "Internal error",
                "detail": str(e)
            }
    
    async def check_payment_status(self, transaction_id: str) -> Dict:
        """
        Check payment status from D-Money
        
        Args:
            transaction_id: D-Money transaction ID
            
        Returns:
            Dict with status, amount, and payment details
        """
        try:
            params = {
                "transaction_id": transaction_id,
                "merchant_id": self.merchant_id
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/payment/status",
                    params=params,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Payment status checked for transaction {transaction_id}: {result}")
                
                return {
                    "success": True,
                    "status": result.get("status"),
                    "amount": result.get("amount"),
                    "currency": result.get("currency"),
                    "payment_method": result.get("payment_method"),
                    "paid_at": result.get("paid_at"),
                    "transaction_id": transaction_id
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Error checking payment status for {transaction_id}: {str(e)}")
            return {
                "success": False,
                "error": "Failed to check payment status",
                "detail": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error checking payment status: {str(e)}")
            return {
                "success": False,
                "error": "Internal error",
                "detail": str(e)
            }
    
    def verify_webhook_signature(self, payload: Dict, received_signature: str) -> bool:
        """
        Verify webhook signature from D-Money
        
        Args:
            payload: Webhook payload
            received_signature: Signature from webhook header
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Generate expected signature
            expected_signature = self._generate_signature(payload)
            
            # Compare signatures (constant-time comparison)
            return hmac.compare_digest(expected_signature, received_signature)
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    async def process_refund(
        self,
        transaction_id: str,
        amount: float,
        reason: str
    ) -> Dict:
        """
        Process a refund in D-Money
        
        Args:
            transaction_id: Original transaction ID
            amount: Refund amount
            reason: Refund reason
            
        Returns:
            Dict with refund status
        """
        try:
            payload = {
                "merchant_id": self.merchant_id,
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": settings.PAYMENT_CURRENCY,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            payload["signature"] = self._generate_signature(payload)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/payment/refund",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Refund processed for transaction {transaction_id}: {result}")
                
                return {
                    "success": True,
                    "refund_id": result.get("refund_id"),
                    "status": result.get("status"),
                    "message": result.get("message")
                }
                
        except httpx.HTTPError as e:
            logger.error(f"Error processing refund for {transaction_id}: {str(e)}")
            return {
                "success": False,
                "error": "Refund failed",
                "detail": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error processing refund: {str(e)}")
            return {
                "success": False,
                "error": "Internal error",
                "detail": str(e)
            }


# Global instance
dmoney_gateway = DMoneyGateway()
