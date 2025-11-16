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
    # ... (código existente - OJO: Asegúrate que esta es la versión
    #      que extrae el gender del event_id, como hicimos antes) ...
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
    logger.info("Iniciando parser [parser_participants.py] (v1.5 - con normalización)...")

    participants_list = root.xpath(".//Competition/Participant") or \
                        root.xpath(".//Participants/Participant") or \
                        root.xpath(".//Participant")

    if not participants_list:
        logger.warning("DT_PARTIC(_UPDATE): No se encontraron <Participant>.")
        return

    skip_count = 0
    try:
        for node in participants_list:
            status = node.get('Status')
            main_function = node.get('MainFunctionId')

            if status != 'ACTIVE' or main_function != 'AA01':
                skip_count += 1
                continue

            participant_id = node.get('Code')
            if not participant_id: continue
            participant_id = participant_id.strip() # Limpiar ID participante

            noc = node.get('Organisation')
            _ensure_noc_exists(noc, db)

            # 1. "Upsert" del Participante
            stmt_participant = insert(models.Participant).values(
                participant_id=participant_id, name=node.get('PrintName'),
                first_name=node.get('GivenName'), last_name=node.get('FamilyName'),
                noc=noc, gender=node.get('Gender')
            ).on_conflict_do_update(
                index_elements=['participant_id'],
                set_={ 'name': node.get('PrintName'), 'first_name': node.get('GivenName'),
                       'last_name': node.get('FamilyName'), 'noc': noc,
                       'gender': node.get('Gender') }
            )
            db.execute(stmt_participant)

            # 2. Parsear <RegisteredEvent>
            reg_events = node.xpath(".//RegisteredEvent")
            for reg_event in reg_events:
                event_id_long = reg_event.get('Event')
                if not event_id_long: continue

                # --- ¡¡NORMALIZACIÓN AQUÍ!! ---
                event_id_base = event_id_long.split('-')[0]
                event_id = event_id_base.rstrip('-') # Quitar guiones finales
                # ------------------------------

                if not event_id: continue # Si queda vacío después de quitar guiones

                _ensure_event_exists(event_id, db) # Llamar con el ID normalizado

                qual_mark = None
                details = {}
                for entry in reg_event.xpath(".//EventEntry"):
                    code = entry.get('Code')
                    value = entry.get('Value', '').strip()
                    if code == 'QUAL_BEST': qual_mark = value
                    else: details[code] = value

                # "Upsert" de la inscripción (usando ID normalizado)
                stmt_entry = insert(models.EventEntry).values(
                    participant_id=participant_id,
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
        logger.info(f"Procesamiento [parser_participants.py] completo. Ignorados: {skip_count}.")
    except Exception as e:
        logger.error(f"Error en [parser_participants.py]: {e}", exc_info=True)
        db.rollback()
        raise # Relanzar error