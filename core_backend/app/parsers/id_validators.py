import re
from dataclasses import dataclass
from typing import Optional

DISCIPLINE_LEN = 3
GENDER_LEN = 1
EVENT_TYPE_LEN = 8
EVENT_MODIFIER_LEN = 10
PHASE_LEN = 4
UNIT_SEGMENT_LEN = 8

EVENT_CORE_LEN = (
    DISCIPLINE_LEN
    + GENDER_LEN
    + EVENT_TYPE_LEN
    + EVENT_MODIFIER_LEN
    + PHASE_LEN
)
EVENT_ID_LEN = EVENT_CORE_LEN + UNIT_SEGMENT_LEN
UNIT_ID_LEN = EVENT_CORE_LEN + UNIT_SEGMENT_LEN
UNIT_PLACEHOLDER = "-" * UNIT_SEGMENT_LEN

DISCIPLINE_RE = re.compile(r"^[A-Z]{3}$")
SEGMENT_RE = re.compile(r"^[A-Z0-9-]+$")
GENDER_ALLOWED = {"M", "W", "X"}


@dataclass(frozen=True)
class EventIdParts:
    discipline: str
    gender: str
    event_type: str
    event_modifier: str
    phase: str


def _has_valid_chars(segment: str) -> bool:
    return bool(SEGMENT_RE.fullmatch(segment))


def _normalize_segment(segment: str, expected_len: int, allow_blank: bool = True) -> Optional[str]:
    if not segment:
        return ("-" * expected_len) if allow_blank else None

    segment = segment.upper()
    if not _has_valid_chars(segment):
        return None
    if len(segment) > expected_len:
        return None

    return segment.ljust(expected_len, "-")


def normalize_event_id(event_id: str) -> Optional[str]:
    """
    Normalize an Event ID to the ODF format (34 chars, últimos 8 siempre '--------').
    Acepta entradas de 22 (sin fase), 26 (solo núcleo) o 34 caracteres.
    """
    if not event_id:
        return None

    event_id = event_id.strip().upper()
    if len(event_id) > EVENT_ID_LEN:
        if any(ch != "-" for ch in event_id[EVENT_ID_LEN:]):
            return None
        event_id = event_id[:EVENT_ID_LEN]

    if len(event_id) < DISCIPLINE_LEN + GENDER_LEN:
        return None

    base_raw = event_id[:EVENT_CORE_LEN]
    unit_raw = event_id[EVENT_CORE_LEN:EVENT_CORE_LEN + UNIT_SEGMENT_LEN]
    extra = event_id[EVENT_CORE_LEN + UNIT_SEGMENT_LEN:]

    if extra and extra.strip("-"):
        return None

    base_raw = base_raw.ljust(EVENT_CORE_LEN, "-")
    discipline = base_raw[:DISCIPLINE_LEN]
    gender = base_raw[DISCIPLINE_LEN : DISCIPLINE_LEN + GENDER_LEN]
    event_type_raw = base_raw[DISCIPLINE_LEN + GENDER_LEN : DISCIPLINE_LEN + GENDER_LEN + EVENT_TYPE_LEN]
    event_modifier_raw = base_raw[DISCIPLINE_LEN + GENDER_LEN + EVENT_TYPE_LEN : DISCIPLINE_LEN + GENDER_LEN + EVENT_TYPE_LEN + EVENT_MODIFIER_LEN]
    phase_raw = base_raw[DISCIPLINE_LEN + GENDER_LEN + EVENT_TYPE_LEN + EVENT_MODIFIER_LEN :]

    if not DISCIPLINE_RE.fullmatch(discipline):
        return None
    if gender not in GENDER_ALLOWED:
        return None
    if not _has_valid_chars(event_type_raw):
        return None
    if not _has_valid_chars(event_modifier_raw):
        return None
    if not _has_valid_chars(phase_raw):
        return None

    # El Event ID no debe incluir la fase real. Siempre normalizamos a '----'.
    phase = "-" * PHASE_LEN

    if unit_raw and unit_raw.strip("-"):
        return None

    return discipline + gender + event_type_raw + event_modifier_raw + phase + UNIT_PLACEHOLDER


def parse_event_id(event_id: str) -> Optional[EventIdParts]:
    """Validate, format, and split an Event ID into its components."""
    normalized = normalize_event_id(event_id)
    if not normalized:
        return None

    event_type_start = DISCIPLINE_LEN + GENDER_LEN
    event_type_end = event_type_start + EVENT_TYPE_LEN
    event_modifier_end = event_type_end + EVENT_MODIFIER_LEN

    return EventIdParts(
        discipline=normalized[:DISCIPLINE_LEN],
        gender=normalized[DISCIPLINE_LEN : DISCIPLINE_LEN + GENDER_LEN],
        event_type=normalized[event_type_start:event_type_end],
        event_modifier=normalized[event_type_end:event_modifier_end],
        phase=normalized[event_modifier_end : event_modifier_end + PHASE_LEN],
    )


def validate_event_id(event_id: str) -> bool:
    """Return True when the Event ID conforms to (or can be padded to) the ODF spec."""
    return normalize_event_id(event_id) is not None


def normalize_unit_id(unit_id: str) -> Optional[str]:
    """Return the Unit ID padded with '-' when segments are shorter."""
    if not unit_id:
        return None

    unit_id = unit_id.strip().upper()
    if len(unit_id) > UNIT_ID_LEN:
        if any(ch != "-" for ch in unit_id[UNIT_ID_LEN:]):
            return None
        unit_id = unit_id[:UNIT_ID_LEN]

    base_raw = unit_id[:EVENT_CORE_LEN]
    unit_segment_raw = unit_id[EVENT_CORE_LEN:EVENT_CORE_LEN + UNIT_SEGMENT_LEN]
    extra = unit_id[EVENT_CORE_LEN + UNIT_SEGMENT_LEN:]

    if extra and extra.strip("-"):
        return None

    base_padded = base_raw.ljust(EVENT_CORE_LEN, "-")
    discipline = base_padded[:DISCIPLINE_LEN]
    gender = base_padded[DISCIPLINE_LEN : DISCIPLINE_LEN + GENDER_LEN]
    event_type = base_padded[DISCIPLINE_LEN + GENDER_LEN : DISCIPLINE_LEN + GENDER_LEN + EVENT_TYPE_LEN]
    event_modifier = base_padded[DISCIPLINE_LEN + GENDER_LEN + EVENT_TYPE_LEN : DISCIPLINE_LEN + GENDER_LEN + EVENT_TYPE_LEN + EVENT_MODIFIER_LEN]
    phase = base_padded[DISCIPLINE_LEN + GENDER_LEN + EVENT_TYPE_LEN + EVENT_MODIFIER_LEN :]

    if not DISCIPLINE_RE.fullmatch(discipline):
        return None
    if gender not in GENDER_ALLOWED:
        return None
    if not _has_valid_chars(event_type):
        return None
    if not _has_valid_chars(event_modifier):
        return None
    if not _has_valid_chars(phase):
        return None

    unit_segment = _normalize_segment(unit_segment_raw, UNIT_SEGMENT_LEN)
    if unit_segment is None:
        return None

    return discipline + gender + event_type + event_modifier + phase + unit_segment


def validate_unit_id(unit_id: str) -> bool:
    """Return True when the Unit ID conforms to (or can be padded to) the ODF spec."""
    return normalize_unit_id(unit_id) is not None


def extract_event_id_from_unit(unit_id: str) -> Optional[str]:
    """Return the normalized Event ID portion of a Unit ID."""
    if not unit_id:
        return None

    normalized_unit = normalize_unit_id(unit_id)
    if normalized_unit:
        event_core = normalized_unit[:EVENT_CORE_LEN]
        # Normalizamos la fase a '----' para Event IDs canónicos.
        event_core = event_core[: EVENT_CORE_LEN - PHASE_LEN] + "-" * PHASE_LEN
        return event_core + UNIT_PLACEHOLDER

    normalized_event = normalize_event_id(unit_id)
    if normalized_event:
        return normalized_event

    return None
