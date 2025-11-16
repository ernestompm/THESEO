import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
# Make sure Event is imported here if it wasn't already
from ..models import Medallist, Event

log = logging.getLogger(__name__)

MEDAL_MAP = {
    "ME_GOLD": "G",
    "ME_SILVER": "S",
    "ME_BRONZE": "B"
}

def _normalize_event_id(raw_event_id: str) -> str:
    """Removes trailing dashes from an event ID."""
    return raw_event_id.rstrip('-')

# --- ¡FUNCIÓN CORREGIDA! ---
def _ensure_event_exists(db: Session, event_id_normalized: str, message: etree._Element):
    """
    Checks if an event exists (using the normalized ID),
    and creates a basic stub if not.
    Extracts gender from the event_id.
    """
    event_name = "Unknown Event"
    # --- Lógica Mejorada para Gender ---
    gender_code = 'U' # Default to Unknown
    if len(event_id_normalized) >= 4:
        # Extraer el 4to caracter (M, W, X)
        g_code = event_id_normalized[3:4]
        if g_code in ('M', 'W', 'X'):
            gender_code = g_code
        else:
             log.warning(f"Could not determine gender from event_id: {event_id_normalized}")
    # --- Fin Lógica Mejorada ---

    # Intentar obtener un nombre más descriptivo si es posible
    try:
        # Buscar SportDescription a nivel de Competición (puede ser genérico)
        sport_desc_comp = message.find('Competition/ExtendedInfos/SportDescription')
        if sport_desc_comp is not None:
             # Podríamos intentar construir un nombre genérico aquí, pero es complejo
             pass # Por ahora, mantenemos "Unknown Event" como placeholder

    except Exception as e:
        log.warning(f"Could not extract event details from DT_MEDALLISTS for {event_id_normalized}: {e}")

    event_data = {
        'event_id': event_id_normalized,
        'name': event_name, # Se actualizará con un DT_CONFIG o DT_SCHEDULE
        'gender': gender_code # <- ¡AHORA SIEMPRE TENDRÁ UN VALOR!
    }

    stmt = pg_insert(Event).values(event_data)

    # Si el event_id ya existe, no hagas nada.
    # Si no existe, inserta la fila stub.
    stmt = stmt.on_conflict_do_nothing(index_elements=['event_id'])

    db.execute(stmt)
    log.debug(f"Ensured event exists: {event_id_normalized} with gender {gender_code}")

# --- El resto del parser_medallists.py no cambia ---

def parse_dt_medallists(db: Session, message: etree._Element):
    """
    Parsea un mensaje DT_MEDALLISTS y hace UPSERT en la tabla 'medallists'.
    Normaliza el event_id eliminando guiones finales.
    """

    raw_event_id = message.get('DocumentCode')
    if not raw_event_id:
        log.error("DT_MEDALLISTS: No se pudo obtener el DocumentCode (event_id).")
        return

    event_id = _normalize_event_id(raw_event_id.strip())

    medal_elements = message.xpath('/OdfBody/Competition/Medal')
    if not medal_elements:
        log.warning(f"DT_MEDALLISTS para Evento {event_id}: No se encontraron elementos <Medal>.")
        return

    medallist_data = []

    try:
        _ensure_event_exists(db, event_id, message) # Ahora esta llamada es segura

        for medal in medal_elements:
            final_unit_id = medal.get('Unit')
            medal_code = medal.get('Code')

            competitor = medal.find('Competitor')
            if competitor is None:
                continue

            participant_id = competitor.get('Code')

            medal_type = MEDAL_MAP.get(medal_code)

            if not all([final_unit_id, participant_id, medal_type]):
                log.warning(f"DT_MEDALLISTS Evento {event_id}: Faltan datos en {final_unit_id}, {participant_id}, {medal_code}")
                continue

            medallist_data.append({
                'event_id': event_id,
                'participant_id': participant_id.strip(),
                'medal_type': medal_type,
                'final_unit_id': final_unit_id.strip()
            })

        if not medallist_data:
            log.info(f"DT_MEDALLISTS Evento {event_id}: No se procesaron medallistas.")
            db.commit() # Commit por si creamos el evento stub
            return

        stmt = pg_insert(Medallist).values(medallist_data)
        stmt = stmt.on_conflict_do_update(
            constraint='_event_participant_medal_uc',
            set_={
                'medal_type': stmt.excluded.medal_type,
                'final_unit_id': stmt.excluded.final_unit_id
            }
        )
        db.execute(stmt)

        db.commit()
        log.info(f"Medallistas (DT_MEDALLISTS) actualizados en tabla 'medallists' para Evento={event_id}")

    except Exception as e:
        log.error(f"Error parseando DT_MEDALLISTS (Evento={event_id}): {e}", exc_info=True)
        db.rollback()
        raise