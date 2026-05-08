from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import UserProfile
from app.services.adaptive_engine import BehavioralEvent, process_event

router = APIRouter(prefix="/api/users", tags=["behavior"])


class BehaviorEventPayload(BaseModel):
    user_id: int
    event_type: str   # "field_error" | "help_click" | "page_dwell"
    value: float
    page: str
    current_mode: str = "intermediate"


class BehaviorResponse(BaseModel):
    suggest_mode_change: bool
    suggested_mode: str | None
    reason: str
    cognitive_load: float


@router.post("/behavior", response_model=BehaviorResponse)
def record_behavior(payload: BehaviorEventPayload, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == payload.user_id).first()
    if not profile:
        raise HTTPException(404, "User profile not found")

    current_error_rate = (profile.error_rate_percent or 0.0) / 100.0
    current_slow_typing = min(1.0, (profile.interaction_speed_avg_ms or 0) / 5000.0)
    current_help_clicks = 0.0  # not stored separately; start at 0

    decision = process_event(
        events=[BehavioralEvent(
            event_type=payload.event_type,
            value=payload.value,
            page=payload.page,
        )],
        current_mode=payload.current_mode,
        current_error_rate=current_error_rate,
        current_slow_typing=current_slow_typing,
        current_help_clicks=current_help_clicks,
    )

    profile.cognitive_load_score = decision.updated_cognitive_load
    profile.error_rate_percent = decision.updated_error_rate * 100.0
    db.commit()

    return BehaviorResponse(
        suggest_mode_change=decision.suggest_mode_change,
        suggested_mode=decision.suggested_mode,
        reason=decision.reason,
        cognitive_load=decision.updated_cognitive_load,
    )
