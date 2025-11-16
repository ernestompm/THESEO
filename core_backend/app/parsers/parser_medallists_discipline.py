import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Importamos los modelos y helpers necesarios
from ..models import Medallist, Event
# Reutilizamos los helpers de parser_medallists
from .parser_medallists import MEDAL_MAP, _normalize_event_id, _ensure_event_exists

log = logging.getLogger(__name__)

def parse_dt_medallists_discipline(db: Session, message: etree._Element):
    """
    Parsea un mensaje DT_MEDALLISTS_DISCIPLINE y hace UPSERT
    en la tabla 'medallists' para todos los eventos listados.
    """
    discipline_node = message.find('Competition/Discipline')
    if discipline_node is None:
        log.warning("DT_MEDALLISTS_DISCIPLINE: No se encontró el nodo <Discipline>.")
        return

    # Extraer el código de disciplina (opcional, para logging)
    discipline_code = discipline_node.get('Code', 'Unknown Discipline').strip()
    log.info(f"Procesando DT_MEDALLISTS_DISCIPLINE para {discipline_code}...")

    event_nodes = discipline_node.xpath('Event')
    if not event_nodes:
        log.warning(f"DT_MEDALLISTS_DISCIPLINE ({discipline_code}): No se encontraron nodos <Event>.")
        return

    medallists_to_upsert = [] # Lista para acumular todos los medallistas

    try:
        for event_node in event_nodes:
            raw_event_id = event_node.get('Code')
            if not raw_event_id:
                continue

            # --- Normalizamos el event_id ---
            event_id = _normalize_event_id(raw_event_id.strip())

            # --- Aseguramos que el evento exista (crea stub si no) ---
            # Pasamos 'message' para que pueda intentar sacar nombre/género
            _ensure_event_exists(db, event_id, message)

            medal_nodes = event_node.xpath('Medal')
            for medal_node in medal_nodes:
                medal_code = medal_node.get('Code') # ME_GOLD, etc.
                medal_type = MEDAL_MAP.get(medal_code) # G, S, B

                competitor_node = medal_node.find('Competitor')
                if competitor_node is None:
                    continue

                participant_id = competitor_node.get('Code')

                if not participant_id or not medal_type:
                    log.warning(f"DT_MEDALLISTS_DISCIPLINE ({event_id}): Faltan datos en Medalla {medal_code}, Competidor {participant_id}")
                    continue

                # Acumulamos los datos para un solo UPSERT masivo al final
                medallists_to_upsert.append({
                    'event_id': event_id,
                    'participant_id': participant_id.strip(),
                    'medal_type': medal_type,
                    # Este mensaje no suele tener el UnitID de la final, lo dejamos NULL
                    'final_unit_id': None
                })

        if not medallists_to_upsert:
            log.info(f"DT_MEDALLISTS_DISCIPLINE ({discipline_code}): No se encontraron medallistas para procesar.")
            db.commit() # Commit por si creamos stubs de eventos
            return

        # --- Ejecutar UPSERT masivo en la tabla 'medallists' ---
        stmt = pg_insert(Medallist).values(medallists_to_upsert)

        # Si ya existe (mismo event_id y participant_id), actualizamos solo el tipo
        # IMPORTANTE: NO actualizamos final_unit_id aquí, para no borrarlo si ya lo teníamos
        #             del DT_MEDALLISTS específico.
        stmt = stmt.on_conflict_do_update(
            constraint='_event_participant_medal_uc', # Usamos la restricción UNIQUE
            set_={
                'medal_type': stmt.excluded.medal_type
                # No incluimos 'final_unit_id' en el SET
            }
        )
        db.execute(stmt)

        db.commit()
        log.info(f"Medallistas (DT_MEDALLISTS_DISCIPLINE) procesados para {discipline_code}. Total: {len(medallists_to_upsert)}.")

    except Exception as e:
        log.error(f"Error parseando DT_MEDALLISTS_DISCIPLINE ({discipline_code}): {e}", exc_info=True)
        db.rollback()
        raise