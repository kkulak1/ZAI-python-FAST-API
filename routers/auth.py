"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.security import HTTPAuthorizationCredentials

from schemas import LoginRequest, LoginResponse, PasswordChange
from services.dependencies import DbSession, bearer, get_admin
from services.security import (
    authenticate_user,
    change_password,
    issue_token,
    revoke_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: DbSession) -> LoginResponse:
    user = authenticate_user(db, payload.username, payload.password)
    expires_in = 3600
    return LoginResponse(
        accessToken=issue_token(user, expires_in),
        tokenType="bearer",
        expiresIn=expires_in,
    )


@router.post("/logout", status_code=204)
def logout(
    _admin=Depends(get_admin),
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> Response:
    revoke_token(credentials.credentials if credentials else None)
    return Response(status_code=204)


@router.put("/password", status_code=204)
def update_password(
    payload: PasswordChange,
    db: DbSession,
    user=Depends(get_admin),
) -> Response:
    change_password(db, user, payload.currentPassword, payload.newPassword)
    return Response(status_code=204)
