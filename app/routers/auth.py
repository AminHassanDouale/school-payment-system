from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.core.database import get_db
from app.core.config import settings
from app.models.models import APIToken
from app.schemas.schemas import TokenRequest, TokenResponse, ErrorResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> APIToken:
    """Validate JWT bearer token and return the associated APIToken"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        api_key: str = payload.get("sub")
        token_id: int = payload.get("token_id")

        if not api_key or not token_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_token = db.query(APIToken).filter(
        APIToken.id == token_id,
        APIToken.api_key == api_key,
        APIToken.is_active == True
    ).first()

    if not api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check expiry
    if api_token.expires_at and api_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last used timestamp
    api_token.last_used_at = datetime.utcnow()
    db.commit()

    return api_token


@router.post(
    "/token",
    response_model=TokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
    summary="Get Access Token",
    description="Authenticate with API key/secret to receive a JWT access token"
)
async def get_token(request: TokenRequest, db: Session = Depends(get_db)):
    """
    Exchange API key + secret for a JWT bearer token.

    The token is valid for the configured expiry (default 60 minutes).
    Use the returned access_token as a Bearer token in subsequent requests.
    """
    # Find token by API key
    api_token = db.query(APIToken).filter(
        APIToken.api_key == request.api_key,
        APIToken.is_active == True
    ).first()

    if not api_token:
        logger.warning(f"Auth attempt with unknown api_key: {request.api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API credentials"
        )

    # Verify secret
    if not pwd_context.verify(request.api_secret, api_token.api_secret_hash):
        logger.warning(f"Auth attempt with wrong secret for token: {api_token.name}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API credentials"
        )

    # Check expiry
    if api_token.expires_at and api_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API token has expired"
        )

    # Create JWT
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": api_token.api_key, "token_id": api_token.id},
        expires_delta=expires
    )

    # Update last used
    api_token.last_used_at = datetime.utcnow()
    db.commit()

    logger.info(f"Token issued for: {api_token.name}")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        token_name=api_token.name
    )
