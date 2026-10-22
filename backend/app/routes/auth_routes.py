# backend/app/routes/auth_routes.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import (
    create_access_token,
    get_current_user,
    hash_password,
    user_doc_to_out,
    verify_password,
)
from ..database import users_collection
from ..schemas import TokenOut, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister):
    # 用户名已存在
    if users_collection.find_one({"username": payload.username}):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已被占用",
        )

    now = datetime.now(timezone.utc)
    doc = {
        "username": payload.username,
        "password_hash": hash_password(payload.password),
        "created_at": now,
    }
    result = users_collection.insert_one(doc)
    doc["_id"] = result.inserted_id

    token = create_access_token(str(result.inserted_id))
    return TokenOut(access_token=token, user=UserOut(**user_doc_to_out(doc)))


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin):
    user = users_collection.find_one({"username": payload.username})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(str(user["_id"]))
    return TokenOut(access_token=token, user=UserOut(**user_doc_to_out(user)))


@router.post("/login/form", response_model=TokenOut, include_in_schema=False)
def login_form(form_data: OAuth2PasswordRequestForm = Depends()):
    """供 Swagger 的 Authorize 按钮使用的表单登录端点。"""
    return login(UserLogin(username=form_data.username, password=form_data.password))


@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)):
    return UserOut(**user_doc_to_out(current_user))