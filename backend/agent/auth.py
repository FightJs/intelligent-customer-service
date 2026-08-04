"""认证授权层 —— bcrypt 密码 hash + JWT token + FastAPI Depends。

依赖：passlib[bcrypt]（密码 hash）、python-jose[cryptography]（JWT）。

用法：
- register/login 端点直接调 hash_password / verify_password / create_token
- 业务端点加 `current = Depends(get_current_user)` 鉴权
- admin 端点加 `admin = Depends(get_admin_user)` 校验管理员角色
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from store import db

load_dotenv()

# 配置（沿用 llm.py 的 os.getenv 模式）
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-change-in-production')
JWT_ALG = 'HS256'
TOKEN_EXPIRE_MINUTES = int(os.getenv('TOKEN_EXPIRE_MINUTES', '10080'))  # 默认 7 天

# passlib bcrypt 上下文（bcrypt 是推荐算法，自动处理 salt）
_pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

# FastAPI Bearer token 提取器（从 Authorization: Bearer <token> 头取）
_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """对明文密码做 bcrypt hash。"""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与 hash 是否匹配。"""
    return _pwd_context.verify(plain, hashed)


def create_token(user: dict) -> str:
    """为 user 生成 JWT。payload 含 user_id、username、role、过期时间。"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    payload = {
        'sub': str(user['id']),
        'username': user['username'],
        'role': user['role'],
        'exp': expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    """解析并验证 JWT。返回 payload dict。无效抛 HTTPException 401。"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'token 无效或已过期：{exc}',
            headers={'WWW-Authenticate': 'Bearer'},
        )


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """FastAPI 依赖：从 Authorization 头解析 token，返回 user dict。

    无 token / token 无效 / 用户不存在 → 401。
    返回的 user dict 含 id、username、role、created_at（不含 password_hash）。
    """
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='缺少认证 token',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    payload = decode_token(creds.credentials)
    user_id = int(payload['sub'])
    user = db.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='token 对应用户不存在',
        )
    return user


def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    """FastAPI 依赖：在 get_current_user 基础上校验 role == admin，否则 403。"""
    if user['role'] != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='需要管理员权限',
        )
    return user
