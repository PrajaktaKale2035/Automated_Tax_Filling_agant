"""Shared FastAPI dependency factories for the Indian Tax Filing System.

Usage
-----
from app.api.deps import require_role
from app.models import UserRole

@router.post("/filing/start")
async def start_filing(
    req: FilingStartRequest,
    current_user: User = Depends(require_role(UserRole.filer, UserRole.helper)),
    db: Session = Depends(get_db),
):
    ...
"""
from fastapi import Depends, HTTPException, status

from app.api.auth import get_current_active_user
from app.models import User, UserRole


def require_role(*allowed_roles: UserRole):
    """Dependency factory — returns a FastAPI dependency that raises HTTP 403
    if the authenticated user's role is not in *allowed_roles*.

    Always chain after get_current_active_user so inactive users get 400 first.
    """
    def _check(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{current_user.role}' is not permitted for this action. "
                    f"Required: {[r.value for r in allowed_roles]}"
                ),
            )
        return current_user

    return _check
