"""CRUD operations for User, UserProfile, ComplianceCheck, AuditLog.

Phase 0: trimmed to non-deleted models. Tax-form / W-2 / 1099 / Dependent /
UserInputData CRUD removed alongside the underlying SQLAlchemy models.
ITR1Filing / Form16 CRUD currently live inline in api/filing_v2.py; if the
filing logic grows it can be lifted here.
"""
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import models, schemas
from app.security import get_password_hash, verify_password


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

def get_user(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create new user with hashed password and default profile."""
    db_user = models.User(
        email=user.email,
        hashed_password=get_password_hash(user.password),
        full_name=user.full_name,
        is_active=True,
        is_verified=False,
    )
    try:
        db.add(db_user)
        db.flush()
        db_profile = models.UserProfile(
            user_id=db_user.id,
            preferred_mode="novice",
            theme="light",
            language="en",
            notifications_enabled=True,
            preferred_regime="new",
        )
        db.add(db_profile)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        db.rollback()
        raise


def update_user(db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[models.User]:
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    for field, value in user_update.model_dump(exclude_unset=True).items():
        setattr(db_user, field, value)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    db.delete(db_user)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# User Profile
# ---------------------------------------------------------------------------

def get_user_profile(db: Session, user_id: int) -> Optional[models.UserProfile]:
    return db.query(models.UserProfile).filter(models.UserProfile.user_id == user_id).first()


def update_user_profile(
    db: Session, user_id: int, profile_update: schemas.UserProfileUpdate
) -> Optional[models.UserProfile]:
    db_profile = get_user_profile(db, user_id)
    if not db_profile:
        return None
    for field, value in profile_update.model_dump(exclude_unset=True).items():
        setattr(db_profile, field, value)
    db.commit()
    db.refresh(db_profile)
    return db_profile


def update_user_interaction_stats(db: Session, user_id: int, help_requested: bool = False) -> None:
    db_profile = get_user_profile(db, user_id)
    if not db_profile:
        return
    db_profile.interaction_count += 1
    if help_requested:
        db_profile.help_requests += 1
    if db_profile.interaction_count > 10:
        help_rate = db_profile.help_requests / db_profile.interaction_count
        if help_rate < 0.1 and db_profile.preferred_mode == "novice":
            db_profile.preferred_mode = "intermediate"
        elif help_rate < 0.05 and db_profile.preferred_mode == "intermediate":
            db_profile.preferred_mode = "expert"
    db.commit()


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def create_audit_log(
    db: Session,
    user_id: int,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> models.AuditLog:
    db_log = models.AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_user_audit_logs(db: Session, user_id: int, limit: int = 100) -> List[models.AuditLog]:
    return (
        db.query(models.AuditLog)
        .filter(models.AuditLog.user_id == user_id)
        .order_by(models.AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
