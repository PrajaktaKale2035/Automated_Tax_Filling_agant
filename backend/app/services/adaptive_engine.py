"""
Adaptive behavioral engine.
Weights: error_rate 40%, slow_typing 30%, help_clicks 30%.
Thresholds: score > 0.7 → suggest simpler mode; score < 0.3 → suggest expert.
"""
from dataclasses import dataclass

# Rolling average smoothing factor (EMA)
_ALPHA = 0.3

WEIGHT_ERROR = 0.40
WEIGHT_SLOW = 0.30
WEIGHT_HELP = 0.30

HIGH_LOAD_THRESHOLD = 0.70
LOW_LOAD_THRESHOLD = 0.30


@dataclass
class BehavioralEvent:
    event_type: str   # "field_error" | "help_click" | "page_dwell"
    value: float      # 1.0 for discrete events, dwell seconds for page_dwell
    page: str


@dataclass
class AdaptiveDecision:
    suggest_mode_change: bool
    suggested_mode: str | None      # None when no change suggested
    reason: str
    updated_cognitive_load: float
    updated_error_rate: float
    updated_slow_typing: float
    updated_help_clicks: float


def compute_cognitive_load(
    error_rate: float,
    slow_typing_ratio: float,
    help_click_ratio: float,
) -> float:
    return (
        error_rate * WEIGHT_ERROR
        + slow_typing_ratio * WEIGHT_SLOW
        + help_click_ratio * WEIGHT_HELP
    )


def _ema(current: float, new_sample: float) -> float:
    return _ALPHA * new_sample + (1 - _ALPHA) * current


def process_event(
    events: list[BehavioralEvent],
    current_mode: str,
    current_error_rate: float,
    current_slow_typing: float,
    current_help_clicks: float,
) -> AdaptiveDecision:
    error_rate = current_error_rate
    slow_typing = current_slow_typing
    help_clicks = current_help_clicks

    for event in events:
        if event.event_type == "field_error":
            error_rate = _ema(error_rate, min(1.0, event.value))
        elif event.event_type == "help_click":
            help_clicks = _ema(help_clicks, min(1.0, event.value))
        elif event.event_type == "page_dwell":
            # Long dwell (> 60s on one field) is a slow-typing proxy
            slow_typing = _ema(slow_typing, min(1.0, event.value / 120.0))

    load = compute_cognitive_load(error_rate, slow_typing, help_clicks)

    if load > HIGH_LOAD_THRESHOLD and current_mode not in ("novice", "accessibility"):
        return AdaptiveDecision(
            suggest_mode_change=True,
            suggested_mode="novice",
            reason=f"High cognitive load detected ({load:.0%}). Simpler interface recommended.",
            updated_cognitive_load=load,
            updated_error_rate=error_rate,
            updated_slow_typing=slow_typing,
            updated_help_clicks=help_clicks,
        )
    elif load < LOW_LOAD_THRESHOLD and current_mode != "expert":
        return AdaptiveDecision(
            suggest_mode_change=True,
            suggested_mode="expert",
            reason=f"Low cognitive load ({load:.0%}). Expert mode available.",
            updated_cognitive_load=load,
            updated_error_rate=error_rate,
            updated_slow_typing=slow_typing,
            updated_help_clicks=help_clicks,
        )
    else:
        return AdaptiveDecision(
            suggest_mode_change=False,
            suggested_mode=None,
            reason="No mode change needed.",
            updated_cognitive_load=load,
            updated_error_rate=error_rate,
            updated_slow_typing=slow_typing,
            updated_help_clicks=help_clicks,
        )
