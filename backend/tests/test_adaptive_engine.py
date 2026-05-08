import pytest


def test_compute_cognitive_load_high_error_rate():
    from app.services.adaptive_engine import compute_cognitive_load
    score = compute_cognitive_load(error_rate=0.9, slow_typing_ratio=0.0, help_click_ratio=0.0)
    # error_rate weight 40%: 0.9 * 0.4 = 0.36 — above threshold triggers suggestion
    assert score > 0.3


def test_compute_cognitive_load_all_zero():
    from app.services.adaptive_engine import compute_cognitive_load
    score = compute_cognitive_load(error_rate=0.0, slow_typing_ratio=0.0, help_click_ratio=0.0)
    assert score == 0.0


def test_compute_cognitive_load_weights_sum():
    """Full load on all dimensions gives 1.0."""
    from app.services.adaptive_engine import compute_cognitive_load
    score = compute_cognitive_load(error_rate=1.0, slow_typing_ratio=1.0, help_click_ratio=1.0)
    assert abs(score - 1.0) < 1e-9


def test_process_event_high_load_suggests_novice():
    from app.services.adaptive_engine import process_event, BehavioralEvent

    events = [
        BehavioralEvent(event_type="field_error", value=1.0, page="filing"),
        BehavioralEvent(event_type="field_error", value=1.0, page="filing"),
        BehavioralEvent(event_type="help_click", value=1.0, page="filing"),
    ]
    # Simulate current profile scores indicating high load
    decision = process_event(
        events=events,
        current_mode="expert",
        current_error_rate=0.85,
        current_slow_typing=0.7,
        current_help_clicks=0.8,
    )
    assert decision.suggest_mode_change is True
    assert decision.suggested_mode in ("novice", "accessibility")


def test_process_event_low_load_suggests_expert():
    from app.services.adaptive_engine import process_event, BehavioralEvent

    decision = process_event(
        events=[BehavioralEvent(event_type="page_dwell", value=0.1, page="filing")],
        current_mode="novice",
        current_error_rate=0.0,
        current_slow_typing=0.0,
        current_help_clicks=0.0,
    )
    assert decision.suggest_mode_change is True
    assert decision.suggested_mode == "expert"


def test_process_event_moderate_load_no_suggestion():
    from app.services.adaptive_engine import process_event, BehavioralEvent

    decision = process_event(
        events=[BehavioralEvent(event_type="page_dwell", value=5.0, page="filing")],
        current_mode="intermediate",
        current_error_rate=0.5,
        current_slow_typing=0.4,
        current_help_clicks=0.3,
    )
    assert decision.suggest_mode_change is False


def test_adaptive_decision_has_updated_scores():
    from app.services.adaptive_engine import process_event, BehavioralEvent

    decision = process_event(
        events=[BehavioralEvent(event_type="field_error", value=1.0, page="filing")],
        current_mode="intermediate",
        current_error_rate=0.5,
        current_slow_typing=0.3,
        current_help_clicks=0.2,
    )
    assert 0.0 <= decision.updated_error_rate <= 1.0
    assert 0.0 <= decision.updated_cognitive_load <= 1.0
