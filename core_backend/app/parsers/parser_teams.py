import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from .. import models
import re

logger = logging.getLogger(__name__)

# --- _ensure_noc_exists y _ensure_event_exists no cambian ---
def _ensure_noc_exists(noc: str, db: Session):
     # ... (código existente) ...
    if not noc: return
    stmt = insert(models.Noc).values(
        noc=noc, long_name=noc, short_name=noc
    ).on_conflict_do_nothing(index_elements=['noc'])
    db.execute(stmt)

def _ensure_event_exists(event_id: str, db: Session):
    # ... (código existente - Asegúrate que es la versión
    #      que extrae gender del event_id) ...
    if not event_id: return
    gender_code = 'U'
    if len(event_id) >= 4:
        g_code = event_id[3:4]
        if g_code in ('M', 'W', 'X'): gender_code = g_code
    stmt = insert(models.Event).values(
        event_id=event_id, name=event_id, gender=gender_code
    ).on_conflict_do_nothing(index_elements=['event_id'])
    db.execute(stmt)

def parse(root: etree._Element, db: Session):
    logger.info("Iniciando parser [parser_teams.py] (v2.3 - con normalización)...")

    teams_list = root.xpath(".//Competition/Team")
    if not teams_list:
        logger.warning("DT_PARTIC_TEAMS(_UPDATE): No se encontraron <Team>.")
        return

    skip_count = 0
    try:
        for team_node in teams_list:
            if team_node.get('Current') != 'true':
                skip_count += 1
                continue

            team_id = team_node.get('Code')
            if not team_id: continue
            team_id = team_id.strip() # Limpiar ID equipo

            noc = team_node.get('Organisation')
            _ensure_noc_exists(noc, db)

            # 1. "Upsert" del Equipo (Participante)
            stmt_team = insert(models.Participant).values(
                participant_id=team_id, name=team_node.get('Name'),
                noc=noc, gender=team_node.get('Gender')
            ).on_conflict_do_update(
                index_elements=['participant_id'],
                set_={ 'name': team_node.get('Name'), 'noc': noc,
                       'gender': team_node.get('Gender') }
            )
            db.execute(stmt_team)

            # 2. Parsear <RegisteredEvent>
            reg_events = team_node.xpath(".//RegisteredEvent")
            for reg_event in reg_events:
                event_id_long = reg_event.get('Event')
                if not event_id_long: continue

                # --- ¡¡NORMALIZACIÓN AQUÍ!! ---
                event_id_base = event_id_long.split('-')[0]
                event_id = event_id_base.rstrip('-') # Quitar guiones finales
                # ------------------------------

                if not event_id: continue # Si queda vacío

                _ensure_event_exists(event_id, db) # Llamar con ID normalizado

                qual_mark = None
                details = {}
                for entry in reg_event.xpath(".//EventEntry"):
                    code = entry.get('Code')
                    value = entry.get('Value', '').strip()
                    if code == 'QUAL_BEST': qual_mark = value
                    else: details[code] = value

                # "Upsert" de la inscripción (usando ID normalizado)
                stmt_entry = insert(models.EventEntry).values(
                    participant_id=team_id,
                    event_id=event_id, # <- Usar ID normalizado
                    qualification_mark=qual_mark,
                    qualification_details=details if details else None
                ).on_conflict_do_update(
                    index_elements=['participant_id', 'event_id'],
                    set_={ 'qualification_mark': qual_mark,
                           'qualification_details': details if details else None }
                )
                db.execute(stmt_entry)

        db.commit()
        logger.info(f"Procesamiento [parser_teams.py] completo. Ignorados: {skip_count}.")
    except Exception as e:
        logger.error(f"Error en [parser_teams.py]: {e}", exc_info=True)
        db.rollback()
        raise # Relanzar error