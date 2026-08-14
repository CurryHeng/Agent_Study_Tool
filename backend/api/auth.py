"""认证路由。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models import User
from schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user, access, refresh = auth_service.register(db, body.username, body.email, body.password)
        db.commit()
    except auth_service.AuthError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.message) from e
    return TokenResponse(user=user, access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user, access, refresh = auth_service.login(db, body.email, body.password)
        db.commit()
    except auth_service.AuthError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.message) from e
    return TokenResponse(user=user, access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user, access, refresh = auth_service.refresh(db, body.refresh_token)
        db.commit()
    except auth_service.AuthError as e:
        db.rollback()
        raise HTTPException(e.status_code, e.message) from e
    return TokenResponse(user=user, access_token=access, refresh_token=refresh)


@router.post("/logout")
def logout(
    body: RefreshRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    auth_service.logout(db, user.id, body.refresh_token)
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
