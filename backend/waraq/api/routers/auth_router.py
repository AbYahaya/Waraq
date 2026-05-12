"""Auth endpoints — register and login.

Phase 5 sub-batch M adds the admission gate:
- Register: admins (email in `ADMIN_EMAILS`) get an immediate token;
  non-admins get a 201 response with `approval_status='pending'` and
  NO token until an admin approves them. Frontend displays the
  pending-approval message.
- Login: refuses pending/rejected accounts with distinct error
  detail strings so the UI can show specific guidance.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from waraq.api.dependencies import CurrentAccount, DbSession
from waraq.api.schemas import (
    AccountResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from waraq.auth import (
    AccountInactive,
    AccountPendingApproval,
    AccountRejected,
    EmailAlreadyRegistered,
    InvalidCredentials,
    authenticate,
    issue_token,
    register_account,
)
from waraq.schemas.enums import ApprovalStatus

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterResponse(BaseModel):
    """Outcome of registration. Includes the approval status so the
    frontend can branch: `approved` → log the user in with the token;
    `pending` → show the waiting-for-admin-approval message. Token is
    only issued when the account is approved (admins auto-approve at
    registration via `ADMIN_EMAILS`)."""

    approval_status: str  # ApprovalStatus.value
    access_token: str | None = None
    token_type: str = "bearer"


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(req: RegisterRequest, session: DbSession) -> RegisterResponse:
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

    # M admission gate: token only issued for approved accounts. Admin
    # emails auto-approve; everyone else lands in `pending` and gets
    # no token until an admin acts on their application.
    if account.approval_status == ApprovalStatus.APPROVED:
        token = issue_token(account_uuid=account.account_uuid)
        return RegisterResponse(
            approval_status=account.approval_status.value,
            access_token=token,
        )
    return RegisterResponse(
        approval_status=account.approval_status.value,
        access_token=None,
    )


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
    except AccountPendingApproval as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your account is awaiting administrator approval. "
                "You will be able to log in once an admin approves your application."
            ),
        ) from exc
    except AccountRejected as exc:
        reason_part = f" Reason: {exc.reason}" if exc.reason else ""
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account registration was rejected.{reason_part}",
        ) from exc

    token = issue_token(account_uuid=account.account_uuid)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=AccountResponse)
async def me(current: CurrentAccount) -> AccountResponse:
    from waraq.admission import is_admin_email

    return AccountResponse(
        account_uuid=current.account_uuid,
        email=current.email,
        display_name=current.display_name,
        active=current.active,
        approval_status=current.approval_status.value,
        is_admin=is_admin_email(current.email),
    )
