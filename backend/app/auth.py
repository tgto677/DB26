from datetime import datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pymongo.database import Database

from .config import settings
from .database import users_collection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# tokenUrl 指向登录接口，供 Swagger 的 Authorize 使用
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ---------- 密码 ----------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------- JWT ----------
def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> str:
    """解析 token，返回 subject(user_id)。失败抛 401。"""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或过期的凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        sub = payload.get("sub")
        if not sub:
            raise credentials_exc
        return sub
    except JWTError:
        raise credentials_exc


# ---------- 当前用户依赖 ----------
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """受保护接口用：Depends(get_current_user)。返回用户文档。"""
    user_id = decode_token(token)
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = users_collection.find_one({"_id": oid})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def user_doc_to_out(user: dict) -> dict:
    """把 users 集合文档转成前端可用的结构。"""
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "created_at": user.get("created_at"),
    }

from fastapi import Request

def _optional_current_user(request: Request) -> dict | None:
    """可选鉴权：没有 Authorization 头或 token 无效都返回 None。"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer "):]
    try:
        user_id = decode_token(token)
        oid = ObjectId(user_id)
    except Exception:
        return None
    return users_collection.find_one({"_id": oid})