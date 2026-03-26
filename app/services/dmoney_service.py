"""
D-Money Djibouti Payment Gateway Integration

Correct API flow (per official documentation):

Step 1 – Token
  POST {DMONEY_TOKEN_URL}
  Header : X-APP-Key: {DMONEY_APP_KEY}
  Body   : {"appSecret": "{DMONEY_APP_SECRET}"}
  Returns: {"token": "...", "code": "0", ...}

Step 2 – PreOrder
  POST {DMONEY_PREORDER_URL}
  Headers: Authorization: Bearer {token}
           X-APP-Key: {DMONEY_APP_KEY}
  Body (flat wrapper + biz_content):
    {
      "method":    "payment.preorder",
      "nonce_str": "<32-char random>",
      "timestamp": "<UTC seconds>",
      "version":   "1.0",
      "sign_type": "SHA256WithRSA",
      "sign":      "<RSA-PSS signature>",
      "biz_content": { appid, merch_code, merch_order_id, ... }
    }
  Returns: {"code": "0", "biz_content": {"prepay_id": "...", ...}}

Step 3 – Build Checkout URL
  https://{DMONEY_CHECKOUT_BASE_URL}?appid=...&prepay_id=...&sign=...
  Guardian visits this URL and pays with their D-Money PIN.

Step 4 – Query Order
  POST {DMONEY_QUERY_ORDER_URL}
  Same signing pattern, method = "payment.queryorder"

Step 5 – Webhook
  D-Money POSTs to PAYMENT_CALLBACK_URL.
  Payload includes: merch_order_id, trade_status, sign, sign_type, ...
  trade_status values: Completed | Paying | Expired | Failure

Signing rules:
  - Flatten top-level params + biz_content params into one dict
  - Exclude: "sign", "sign_type", "biz_content"
  - Sort keys alphabetically, exclude None/empty values
  - Concatenate as "key1=val1&key2=val2"
  - Sign with RSA-PSS (SHA256 + MGF1) using merchant private key (PKCS#8 DER)
  - Base64-encode the result
"""

import base64
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlencode, quote

import httpx
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding

from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Keys excluded from the sign string (always)
_SIGN_EXCLUDE = {"sign", "sign_type", "biz_content"}


def _build_sign_string(flat_params: Dict) -> str:
    """
    Sort params alphabetically, drop excluded keys and None/empty values,
    concatenate as key=value&key=value.
    """
    items = sorted(
        [(k, str(v)) for k, v in flat_params.items()
         if k not in _SIGN_EXCLUDE and v is not None and str(v) != ""],
        key=lambda x: x[0]
    )
    return "&".join(f"{k}={v}" for k, v in items)


class DMoneyGateway:
    """D-Money Djibouti Payment Gateway"""

    def __init__(self):
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    # ─── Key helpers ──────────────────────────────────────────────────────────

    def _private_key(self):
        """Load merchant RSA private key (base64-encoded PKCS#8 DER)"""
        der = base64.b64decode(settings.DMONEY_PRIVATE_KEY)
        return serialization.load_der_private_key(der, password=None, backend=default_backend())

    def _public_key(self):
        """Load D-Money RSA public key (base64-encoded SubjectPublicKeyInfo DER)"""
        der = base64.b64decode(settings.DMONEY_PUBLIC_KEY)
        return serialization.load_der_public_key(der, backend=default_backend())

    # ─── Signing / verification ───────────────────────────────────────────────

    def _sign(self, flat_params: Dict) -> str:
        """
        Sign using RSA-PSS with SHA256 + MGF1.
        flat_params should be the merged dict of top-level + biz_content fields.
        """
        sign_str = _build_sign_string(flat_params)
        logger.debug(f"D-Money sign string: {sign_str}")

        signature = self._private_key().sign(
            sign_str.encode("utf-8"),
            rsa_padding.PSS(
                mgf=rsa_padding.MGF1(hashes.SHA256()),
                salt_length=rsa_padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def _verify_sign(self, flat_params: Dict, received_b64: str) -> bool:
        """
        Verify D-Money RSA-PSS signature (used for webhook and response verification).
        Uses PSS.AUTO so any valid salt length is accepted.
        """
        try:
            sign_str = _build_sign_string(flat_params)
            self._public_key().verify(
                base64.b64decode(received_b64),
                sign_str.encode("utf-8"),
                rsa_padding.PSS(
                    mgf=rsa_padding.MGF1(hashes.SHA256()),
                    salt_length=rsa_padding.PSS.AUTO,
                ),
                hashes.SHA256(),
            )
            return True
        except Exception as e:
            logger.error(f"D-Money signature verification failed: {e}")
            return False

    def verify_webhook_signature(self, payload: Dict, received_signature: str) -> bool:
        """Called by the webhook router to validate incoming D-Money notifications"""
        return self._verify_sign(payload, received_signature)

    # ─── HTTP helpers ─────────────────────────────────────────────────────────

    def _client(self) -> httpx.AsyncClient:
        """
        SSL verification is disabled for the sandbox server (self-signed cert).
        Set ENVIRONMENT=production to re-enable it.
        """
        verify_ssl = (settings.ENVIRONMENT == "production")
        return httpx.AsyncClient(verify=verify_ssl, timeout=30.0)

    @staticmethod
    def _nonce() -> str:
        """32-character alphanumeric random string"""
        return secrets.token_hex(16).upper()  # 32 hex chars

    @staticmethod
    def _ts() -> str:
        """Current UTC timestamp in seconds (as string)"""
        return str(int(time.time()))

    # ─── Token management ─────────────────────────────────────────────────────

    async def _fetch_token(self) -> str:
        """
        POST {DMONEY_TOKEN_URL}
        Header : X-APP-Key: {app_key}
        Body   : {"appSecret": "{app_secret}"}
        """
        async with self._client() as client:
            resp = await client.post(
                settings.DMONEY_TOKEN_URL,
                json={"appSecret": settings.DMONEY_APP_SECRET},
                headers={
                    "X-APP-Key": settings.DMONEY_APP_KEY,
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            result = resp.json()

        code = str(result.get("code", ""))
        if code not in ("0", "200"):
            raise RuntimeError(
                f"D-Money token error (code={code}): {result.get('message', result)}"
            )

        token = result.get("token") or result.get("access_token")
        if not token:
            raise RuntimeError(f"No token field in D-Money response: {result}")

        logger.info("D-Money access token obtained successfully")
        return token

    async def _get_token(self) -> str:
        """Return cached token or fetch a new one"""
        if self._token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._token
        self._token = await self._fetch_token()
        self._token_expires = datetime.utcnow() + timedelta(hours=1)
        return self._token

    # ─── Checkout URL builder ─────────────────────────────────────────────────

    def _build_checkout_url(self, prepay_id: str, order_id: str) -> str:
        """
        Build the guardian-facing checkout URL.
        Signed params: appid, merch_code, nonce_str, prepay_id, timestamp,
                       trade_type, version, language
        """
        nonce = self._nonce()
        ts = self._ts()
        params = {
            "appid": settings.DMONEY_APP_ID,
            "merch_code": settings.DMONEY_SHORT_CODE,
            "nonce_str": nonce,
            "prepay_id": prepay_id,
            "timestamp": ts,
            "trade_type": "Checkout",
            "version": "1.0",
            "language": "en",
        }
        sign = self._sign(params)
        # Append sign and sign_type after signing
        params["sign"] = quote(sign, safe="")
        params["sign_type"] = "SHA256WithRSA"
        return f"{settings.DMONEY_CHECKOUT_BASE_URL}?{urlencode(params)}"

    # ─── Payment operations ───────────────────────────────────────────────────

    async def create_payment_request(
        self,
        order_id: str,
        amount: float,
        guardian_phone: str,
        description: str,
        student_name: str,
    ) -> Dict:
        """
        Step 2: POST /merchant/preOrder
        Builds the signed request body, calls D-Money, then builds the
        checkout URL from the returned prepay_id.

        Returns:
            {success, payment_url, transaction_id, prepay_id, status, message}
          or
            {success: False, error, detail}
        """
        try:
            token = await self._get_token()
            nonce = self._nonce()
            ts = self._ts()

            biz_content = {
                "appid": settings.DMONEY_APP_ID,
                "merch_code": settings.DMONEY_SHORT_CODE,
                "merch_order_id": order_id,
                "trade_type": "Checkout",
                "title": f"School Fee - {student_name}",
                "total_amount": str(int(amount)),   # DJF = integer
                "trans_currency": settings.PAYMENT_CURRENCY,
                "timeout_express": "120m",
                "notify_url": settings.PAYMENT_CALLBACK_URL,
                "redirect_url": f"{settings.PAYMENT_SUCCESS_URL}?order_id={order_id}",
                "business_type": "OnlineMerchant",
                "callback_info": description or f"order:{order_id}",
            }

            # Flatten for signing: top-level (minus sign/sign_type/biz_content) + biz_content
            sign_params = {
                "method": "payment.preorder",
                "nonce_str": nonce,
                "timestamp": ts,
                "version": "1.0",
                **biz_content,
            }
            signature = self._sign(sign_params)

            body = {
                "method": "payment.preorder",
                "nonce_str": nonce,
                "timestamp": ts,
                "version": "1.0",
                "sign_type": "SHA256WithRSA",
                "sign": signature,
                "biz_content": biz_content,
            }

            async with self._client() as client:
                resp = await client.post(
                    settings.DMONEY_PREORDER_URL,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-APP-Key": settings.DMONEY_APP_KEY,
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                result = resp.json()

            logger.info(f"D-Money preOrder response for {order_id}: {result}")

            code = str(result.get("code", ""))
            if code in ("0", "200"):
                biz = result.get("biz_content", {})
                prepay_id = biz.get("prepay_id", "")
                checkout_url = self._build_checkout_url(prepay_id, order_id)
                return {
                    "success": True,
                    "payment_url": checkout_url,
                    "transaction_id": biz.get("order_id") or order_id,
                    "prepay_id": prepay_id,
                    "status": "initiated",
                    "message": result.get("message", "Payment request created"),
                }
            else:
                logger.error(f"D-Money preOrder failed for {order_id}: {result}")
                return {
                    "success": False,
                    "error": result.get("message", "PreOrder failed"),
                    "detail": str(result),
                }

        except httpx.HTTPError as e:
            logger.error(f"D-Money HTTP error (preOrder {order_id}): {e}")
            return {"success": False, "error": "Payment gateway HTTP error", "detail": str(e)}
        except Exception as e:
            logger.error(f"D-Money error (preOrder {order_id}): {e}")
            return {"success": False, "error": "Payment gateway error", "detail": str(e)}

    async def check_payment_status(self, order_id: str) -> Dict:
        """
        Step 4: POST /merchant/queryOrder
        Signed params: method, nonce_str, timestamp, version + biz_content fields
        """
        try:
            token = await self._get_token()
            nonce = self._nonce()
            ts = self._ts()

            biz_content = {
                "appid": settings.DMONEY_APP_ID,
                "merch_code": settings.DMONEY_SHORT_CODE,
                "merch_order_id": order_id,
            }

            sign_params = {
                "method": "payment.queryorder",
                "nonce_str": nonce,
                "timestamp": ts,
                "version": "1.0",
                **biz_content,
            }
            signature = self._sign(sign_params)

            body = {
                "method": "payment.queryorder",
                "nonce_str": nonce,
                "timestamp": ts,
                "version": "1.0",
                "sign_type": "SHA256WithRSA",
                "sign": signature,
                "biz_content": biz_content,
            }

            async with self._client() as client:
                resp = await client.post(
                    settings.DMONEY_QUERY_ORDER_URL,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-APP-Key": settings.DMONEY_APP_KEY,
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                result = resp.json()

            logger.info(f"D-Money queryOrder response for {order_id}: {result}")

            code = str(result.get("code", ""))
            is_fail = result.get("result", "").upper() == "FAIL"
            if code in ("0", "200") and not is_fail:
                biz = result.get("biz_content", {})
                raw_status = (biz.get("order_status") or "PENDING").upper()
                # Map D-Money order_status → our internal PaymentStatus string
                status_map = {
                    "PAID": "success",
                    "COMPLETED": "success",
                    "PAYING": "pending",
                    "PENDING": "pending",
                    "EXPIRED": "failed",
                    "FAILURE": "failed",
                    "FAILED": "failed",
                }
                return {
                    "success": True,
                    "status": status_map.get(raw_status, "pending"),
                    "raw_status": raw_status,
                    "amount": biz.get("total_amount"),
                    "currency": biz.get("trans_currency", settings.PAYMENT_CURRENCY),
                    "payment_method": None,
                    "paid_at": biz.get("trans_time"),
                    "transaction_id": biz.get("payment_order_id") or order_id,
                }
            else:
                return {
                    "success": False,
                    "error": result.get("msg", "Query failed"),
                    "detail": str(result),
                }

        except httpx.HTTPError as e:
            logger.error(f"D-Money HTTP error (queryOrder {order_id}): {e}")
            return {"success": False, "error": "Failed to query payment", "detail": str(e)}
        except Exception as e:
            logger.error(f"D-Money error (queryOrder {order_id}): {e}")
            return {"success": False, "error": "Internal error", "detail": str(e)}

    async def process_refund(self, transaction_id: str, amount: float, reason: str) -> Dict:
        """Placeholder — D-Money Djibouti refund API not documented yet"""
        logger.warning("Refund API not available for D-Money Djibouti")
        return {
            "success": False,
            "error": "Refund not supported",
            "detail": "Contact D-Money support to initiate a refund",
        }


# Singleton — safe because token caching is instance state only
dmoney_gateway = DMoneyGateway()
