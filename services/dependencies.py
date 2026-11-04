from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database.database import get_db
from database.models import User
from services.security import get_current_user

bearer = HTTPBearer(auto_error=False, scheme_name="bearerAuth")
DbSession = Annotated[Session, Depends(get_db)]


def get_admin(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    token = credentials.credentials if credentials else None
    return get_current_user(db, token)
