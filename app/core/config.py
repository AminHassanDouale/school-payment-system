from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "School Payment System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    # Database
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/school_payments"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # D-Money Payment Gateway - Credentials
    DMONEY_APP_ID: str = ""
    DMONEY_APP_KEY: str = ""
    DMONEY_APP_SECRET: str = ""
    DMONEY_SHORT_CODE: str = ""           # merCode / merchant short code
    DMONEY_PUBLIC_KEY: str = ""           # D-Money server RSA public key (base64 DER)
    DMONEY_PRIVATE_KEY: str = ""          # Merchant RSA private key (base64 PKCS#8 DER)

    # D-Money API Endpoints
    DMONEY_TOKEN_URL: str = "https://pgtest.d-money.dj:38443/apiaccess/payment/gateway/payment/v1/token"
    DMONEY_PREORDER_URL: str = "https://pgtest.d-money.dj:38443/apiaccess/payment/gateway/payment/v1/merchant/preOrder"
    DMONEY_QUERY_ORDER_URL: str = "https://pgtest.d-money.dj:38443/apiaccess/payment/gateway/payment/v1/merchant/queryOrder"
    # Checkout page - where the guardian enters their D-Money PIN
    DMONEY_CHECKOUT_BASE_URL: str = "https://pgtest.d-money.dj:38443/payment/web/paygate"

    # Payment Configuration
    PAYMENT_CURRENCY: str = "DJF"
    PAYMENT_CALLBACK_URL: str = "https://api.scolapp.com/api/v1/webhooks/dmoney"
    PAYMENT_SUCCESS_URL: str = "https://scolapp.com/payment/success"
    PAYMENT_CANCEL_URL: str = "https://scolapp.com/payment/cancel"

    # Scolapp Integration
    SCOLAPP_DOMAIN: str = "https://scolapp.com"
    SCOLAPP_API_KEY: str = ""

    # SMS Notifications (optional)
    SMS_PROVIDER: str = "twilio"
    SMS_API_KEY: str = ""
    SMS_SENDER_NUMBER: str = ""

    # Email Configuration (optional)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Scolapp Payment System"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "logs/app.log"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # CORS Settings
    CORS_ORIGINS: str = "https://scolapp.com,http://localhost:3000"
    CORS_ALLOW_CREDENTIALS: bool = True

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
