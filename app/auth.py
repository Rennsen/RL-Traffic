from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from starlette.responses import JSONResponse, RedirectResponse

from .db import SessionLocal
from .db_models import Role, User, UserRole
from .security import hash_password, verify_password

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
SESSION_COOKIE = os.getenv("SESSION_COOKIE_NAME", "flowmind_session")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "7"))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=os.getenv(
        "GOOGLE_DISCOVERY_URL",
        "https://accounts.google.com/.well-known/openid-configuration",
    ),
    client_kwargs={"scope": "openid email profile"},
)


def _create_access_token(user: User, roles: List[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    payload = {
        "sub": user.id,
        "email": user.email,
        "roles": roles,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _get_roles_for_user(db, user_id: str) -> List[str]:
    roles = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user_id)
        .all()
    )
    return [row[0] for row in roles]


def get_current_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session")

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        roles = _get_roles_for_user(db, user_id)
    return {"id": user.id, "email": user.email, "name": user.name, "roles": roles}


def get_current_user_optional(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        roles = _get_roles_for_user(db, user_id)
    return {"id": user.id, "email": user.email, "name": user.name, "roles": roles}


def require_roles(required: List[str]):
    def _dependency(user=Depends(get_current_user)):
        user_roles = set(user["roles"])
        if not user_roles.intersection(required):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _dependency


async def login(request: Request):
    if not oauth.google.client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


async def callback(request: Request):
    if not oauth.google.client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    token = await oauth.google.authorize_access_token(request)
    userinfo = await oauth.google.parse_id_token(request, token)

    email = userinfo.get("email")
    name = userinfo.get("name") or email
    avatar_url = userinfo.get("picture")

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, name=name, avatar_url=avatar_url)
            db.add(user)
            db.commit()
            db.refresh(user)

            role = db.query(Role).filter(Role.name == "Operator").first()
            if role:
                db.add(UserRole(user_id=user.id, role_id=role.id))
                db.commit()
        roles = _get_roles_for_user(db, user.id)

    token_value = _create_access_token(user, roles)
    response = RedirectResponse(url=FRONTEND_ORIGIN)
    response.set_cookie(
        SESSION_COOKIE,
        token_value,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=SESSION_DAYS * 24 * 60 * 60,
    )
    return response


def logout():
    response = RedirectResponse(url=FRONTEND_ORIGIN)
    response.delete_cookie(SESSION_COOKIE)
    return response


def register_local(email: str, name: str, password: str):
    with SessionLocal() as db:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
            auth_provider="local",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        role = db.query(Role).filter(Role.name == "Operator").first()
        if role:
            db.add(UserRole(user_id=user.id, role_id=role.id))
            db.commit()

        roles = _get_roles_for_user(db, user.id)

    token_value = _create_access_token(user, roles)
    response = JSONResponse({"status": "ok", "email": email, "name": name})
    response.set_cookie(
        SESSION_COOKIE,
        token_value,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=SESSION_DAYS * 24 * 60 * 60,
    )
    return response


def login_local(email: str, password: str):
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.password_hash:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        roles = _get_roles_for_user(db, user.id)

    token_value = _create_access_token(user, roles)
    response = JSONResponse({"status": "ok", "email": email})
    response.set_cookie(
        SESSION_COOKIE,
        token_value,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=SESSION_DAYS * 24 * 60 * 60,
    )
    return response
