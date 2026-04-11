import re
from urllib.parse import quote

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, Field
from app.core.config import settings
from app.core.database import get_database
from app.core.password_reset_email import send_password_reset_email
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
)
from app.core.dependencies import get_current_user, get_current_active_user
from app.models.user import User, UserCreate, UserLogin, Token

router = APIRouter()


async def _find_user_by_email_ci(db, email: str):
    """Case-insensitive email lookup."""
    raw = (email or "").strip()
    if not raw:
        return None
    esc = re.escape(raw)
    return await db.users.find_one({"email": {"$regex": f"^{esc}$", "$options": "i"}})


@router.options("/register")
@router.options("/login")
@router.options("/login/json")
@router.options("/forgot-password")
@router.options("/reset-password")
async def auth_options():
    """CORS preflight - return 200 so browser can proceed with actual request."""
    return {}


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user"""
    db = await get_database()
    
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password strength (basic check)
    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    # Normalize role text (free-form work role, e.g., "Frontend Developer", "QA Engineer")
    role = (user_data.role or "").strip()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role is required",
        )

    # Create user
    user_dict = user_data.model_dump(exclude={"password"})
    user_dict["role"] = role
    user_dict["hashed_password"] = get_password_hash(user_data.password)
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    
    result = await db.users.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)
    return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Login and get access token
    
    Use OAuth2PasswordRequestForm for form-data or JSON body:
    - username: email address
    - password: user password
    """
    db = await get_database()
    user = await db.users.find_one({"email": form_data.username})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"], "user_id": str(user["_id"]), "role": user["role"]},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login/json", response_model=Token)
async def login_json(credentials: UserLogin):
    """
    Login endpoint that accepts JSON body instead of form-data
    Alternative to /login endpoint
    """
    db = await get_database()
    user = await db.users.find_one({"email": credentials.email})
    
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"], "user_id": str(user["_id"]), "role": user["role"]},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current authenticated user information"""
    return current_user

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user)
):
    """Change user password"""
    db = await get_database()
    user = await db.users.find_one({"_id": ObjectId(current_user.id)})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not verify_password(password_data.current_password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(password_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )
    
    # Update password
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "hashed_password": get_password_hash(password_data.new_password),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Password changed successfully"}


class ForgotPasswordBody(BaseModel):
    email: EmailStr


class ResetPasswordBody(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=6)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(body: ForgotPasswordBody):
    """
    Request a password reset. Always returns the same message (no email enumeration).
    Sends email when SMTP is configured; in dev set PASSWORD_RESET_RETURN_TOKEN=true to get token in JSON.
    """
    db = await get_database()
    user = await _find_user_by_email_ci(db, body.email)
    base = (settings.FRONTEND_BASE_URL or "http://localhost:5173").rstrip("/")

    if user:
        token = create_password_reset_token(str(user["_id"]))
        reset_url = f"{base}/reset-password?token={quote(token, safe='')}"
        try:
            if (settings.SMTP_HOST or "").strip():
                send_password_reset_email(user["email"], reset_url)
        except Exception:
            # Log but still allow dev token return path
            import logging

            logging.getLogger(__name__).exception("send_password_reset_email failed")

    msg = "If an account exists for that email, password reset instructions have been sent."
    if not user:
        return {"message": msg}

    out: dict = {"message": msg}
    if settings.PASSWORD_RESET_RETURN_TOKEN:
        out["reset_token"] = token
        out["reset_url"] = reset_url
    return out


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(body: ResetPasswordBody):
    """Set a new password using a reset token from forgot-password."""
    user_id = decode_password_reset_token(body.token.strip())
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link. Request a new one.",
        )

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )

    db = await get_database()
    user = await db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )

    if len(body.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    await db.users.update_one(
        {"_id": oid},
        {
            "$set": {
                "hashed_password": get_password_hash(body.new_password),
                "updated_at": datetime.utcnow(),
            }
        },
    )
    return {"message": "Password updated. You can sign in with your new password."}
