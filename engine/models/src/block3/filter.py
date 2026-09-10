from .config import (
    TARGET_CLASSES,
    CONFIDENCE_THRESHOLD,
    DECIBEL_THRESHOLD,
)

def validate_input(event_class, confidence, decibel):
    """
    Validate input received from Block 2A and Block 2B.

    Returns:
        (is_valid, reason)
    """

    if event_class is None:
        return False, "missing_event_class"

    if confidence is None:
        return False, "missing_confidence"

    if decibel is None:
        return False, "missing_decibel"

    if not isinstance(event_class, str):
        return False, "invalid_event_class_type"

    if not isinstance(confidence, (int, float)):
        return False, "invalid_confidence_type"

    if not isinstance(decibel, (int, float)):
        return False, "invalid_decibel_type"

    if confidence < 0 or confidence > 1:
        return False, "confidence_out_of_range"

    return True, "input_valid"

# =========================================================
# 3.2 TARGET CLASS FILTER
# =========================================================

def check_target_class(event_class):
    return event_class in TARGET_CLASSES

# =========================================================
# 3.3 AI CONFIDENCE FILTER
# =========================================================

def check_confidence(confidence):
    return confidence > CONFIDENCE_THRESHOLD

# =========================================================
# 3.4 DECIBEL FILTER
# =========================================================

def check_decibel(decibel):
    return decibel > DECIBEL_THRESHOLD

# =========================================================
# 3.5 DUAL-THRESHOLD DECISION
# =========================================================

def make_decision(target_gate, confidence_gate, db_gate):
    return target_gate and confidence_gate and db_gate

# =========================================================
# 3.6 OUTPUT PACKAGING
# =========================================================

def build_output(
    filter_pass,
    event_class,
    confidence,
    decibel,
    target_gate,
    confidence_gate,
    db_gate,
    reason,
):
    return {
        "filter_pass": filter_pass,
        "event_class": event_class,
        "confidence": confidence,
        "decibel": decibel,
        "target_gate": target_gate,
        "confidence_gate": confidence_gate,
        "db_gate": db_gate,
        "reason": reason,
    }

# =========================================================
# BLOCK 3 MAIN PIPELINE
# =========================================================

def block3_filter(event_class, confidence, decibel):

    # 3.1 INPUT VALIDATION
    is_valid, validation_reason = validate_input(
        event_class,
        confidence,
        decibel,
    )

    if not is_valid:
        return build_output(
            filter_pass=False,
            event_class=event_class,
            confidence=confidence,
            decibel=decibel,
            target_gate=False,
            confidence_gate=False,
            db_gate=False,
            reason=validation_reason,
        )

    # 3.2 TARGET CLASS FILTER
    target_gate = check_target_class(event_class)

    # 3.3 AI CONFIDENCE FILTER
    confidence_gate = check_confidence(confidence)

    # 3.4 DECIBEL FILTER
    db_gate = check_decibel(decibel)

    # 3.5 DUAL-THRESHOLD DECISION
    filter_pass = make_decision(
        target_gate,
        confidence_gate,
        db_gate,
    )

    # Determine reason
    if not target_gate:
        reason = "non_target_class"

    elif not confidence_gate:
        reason = "confidence_below_threshold"

    elif not db_gate:
        reason = "decibel_below_threshold"

    else:
        reason = "all_conditions_passed"

    # 3.6 OUTPUT PACKAGING
    return build_output(
        filter_pass=filter_pass,
        event_class=event_class,
        confidence=confidence,
        decibel=decibel,
        target_gate=target_gate,
        confidence_gate=confidence_gate,
        db_gate=db_gate,
        reason=reason,
    )
