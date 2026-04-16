from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.limiter import limiter

from app.api.v1.deps import CurrentUser, DBSession
from app.api.v1.schemas import LoginRequest, RegisterRequest, TokenPair, UserOut
from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.db.models import User

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DBSession) -> User:
    exists = await db.scalar(select(User).where(User.email == body.email))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: DBSession) -> TokenPair:
    user = await db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")
    sub = str(user.id)
    return TokenPair(
        access_token=create_access_token(sub, {"email": user.email}),
        refresh_token=create_refresh_token(sub),
    )


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
