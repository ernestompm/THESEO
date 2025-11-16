import logging
from typing import Iterable, Set

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .. import models

log = logging.getLogger(__name__)


def _clean_participant_ids(participant_ids: Iterable[str]) -> Set[str]:
    """Return a normalized set of participant IDs (stripped, non-empty)."""
    cleaned_ids: Set[str] = set()
    for participant_id in participant_ids or []:
        if not participant_id:
            continue
        normalized = participant_id.strip()
        if normalized:
            cleaned_ids.add(normalized)
    return cleaned_ids


def ensure_participants_exist(db: Session, participant_ids: Iterable[str]) -> int:
    """
    Make sure every participant_id in the iterable exists in the participants table.

    Returns the number of stub entries that were created.
    """
    cleaned_ids = _clean_participant_ids(participant_ids)
    if not cleaned_ids:
        return 0

    existing = (
        db.query(models.Participant.participant_id)
        .filter(models.Participant.participant_id.in_(cleaned_ids))
        .all()
    )
    existing_ids = {participant_id for (participant_id,) in existing}
    new_ids = cleaned_ids - existing_ids
    if not new_ids:
        return 0

    stub_participants = [
        {"participant_id": participant_id, "name": "Pending Info"}
        for participant_id in new_ids
    ]
    stmt = pg_insert(models.Participant).values(stub_participants)
    stmt = stmt.on_conflict_do_nothing(index_elements=["participant_id"])
    db.execute(stmt)

    log.debug("Created %s stub participant(s): %s", len(stub_participants), new_ids)
    return len(stub_participants)
