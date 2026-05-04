"""Auth endpoints — register and login."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    AccountResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from waraq.auth import (
    AccountInactive,
    EmailAlreadyRegistered,
    InvalidCredentials,
    authenticate,
    issue_token,
    register_account,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(req: RegisterRequest, session: DbSession) -> TokenResponse:
    try:
        account = await register_account(
            session=session,
            email=req.email,
            password=req.password,
            display_name=req.display_name,
        )
    except EmailAlreadyRegistered as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {exc.email!r} is already registered",
        ) from exc

    token = issue_token(account_uuid=account.account_uuid)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, session: DbSession) -> TokenResponse:
    try:
        account = await authenticate(session=session, email=req.email, password=req.password)
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect",
        ) from exc
    except AccountInactive as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        ) from exc

    token = issue_token(account_uuid=account.account_uuid)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=AccountResponse)
async def me(current: CurrentAccount) -> AccountResponse:
    return AccountResponse.model_validate(current)
