import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .. import models
import re

log = logging.getLogger(__name__)

# --- (La función helper _parse_event_code ya no es necesaria aquí) ---

def parse_dt_codes_event(message: etree._Element, db: Session):
    """
    Parsea mensajes DT_CODES (Subtipos EVENT y RECORD)
    y rellena la tabla 'events'.
    
    V3.3: 
    - Filtra para excluir cabeceras (donde Event="------------------").
    - Coge el nombre de 'Description' o 'LongDescription'.
    - De-duplica los eventos antes de insertar (soluciona CardinalityViolation).
    """
    log.info("Iniciando parser [parser_events.py] (v3.3)...")
    
    # --- ¡FILTRO CORREGIDO v3.3! ---
    # Selecciona todos los CodeSet que NO tengan Event="------------------"
    codeset_elements = message.xpath(
        '/OdfBody/Competition/CodeSet[@Event and @Event!="------------------"]'
    )
    
    if not codeset_elements:
        log.warning("[parser_events.py] No se encontraron elementos <CodeSet> con un Event ID específico.")
        return

    # Usar un diccionario para de-duplicar (soluciona CardinalityViolation)
    events_map = {}

    for code in codeset_elements:
        event_id = code.get('Code') 
        gender = code.get('Gender')
        if not event_id or not gender:
            continue
            
        event_id = event_id.strip()

        lang_element = code.find('Language[@Language="ENG"]')
        if lang_element is None:
            lang_element = code.find('Language')
            
        name = event_id # Fallback
        if lang_element is not None:
            # Coger el nombre largo primero, si no, el corto
            name = lang_element.get('LongDescription')
            if not name:
                name = lang_element.get('Description')
        
        # Añadir al map (de-duplica automáticamente si el event_id ya existe)
        events_map[event_id] = {
            'event_id': event_id,
            'name': name.strip(),
            'gender': gender.strip()
            # Dejamos 'distance' y 'stroke' como NULL
            # El parser de schedule (v3.2) los rellenará
        }

    events_data = list(events_map.values())

    if not events_data:
        log.warning("[parser_events.py] La lista de Eventos procesada está vacía.")
        return

    try:
        stmt = pg_insert(models.Event).values(events_data)
        
        # Si el evento ya existe (creado como stub), actualiza el nombre y género
        stmt = stmt.on_conflict_do_update(
            index_elements=['event_id'],
            set_={
                'name': stmt.excluded.name,
                'gender': stmt.excluded.gender
                # No tocamos distance/stroke, dejamos que schedule los gestione
            }
        )
        db.execute(stmt)
        log.info(f"[parser_events.py] Procesados y actualizados {len(events_data)} Eventos.")
        
    except Exception as e:
        log.error(f"Error en [parser_events.py] al hacer upsert en BBDD: {e}", exc_info=True)
        db.rollback()
        raise