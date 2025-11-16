import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import update
from .. import models
from datetime import datetime
import re
from .id_validators import (
    extract_event_id_from_unit,
    normalize_event_id,
    normalize_unit_id,
    parse_event_id,
    validate_event_id,
)
from .participant_helpers import ensure_participants_exist

log = logging.getLogger(__name__)

# --- INICIO DE FUNCIONES HELPER ---

def _derive_para_class(event_modifier: str, stroke_code: str) -> str | None:
    """Extrae la clase paralímpica a partir del modificador y el tipo de prueba."""
    modifier = (event_modifier or "").rstrip("-")
    if len(modifier) < 2 or not modifier[:2].isdigit():
        return None

    class_num = int(modifier[:2])
    if class_num <= 0:
        return None

    prefix = "S"
    if stroke_code in ("BR",):
        prefix = "SB"
    elif stroke_code in ("IM",):
        prefix = "SM"

    return f"{prefix}{class_num}"


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Convierte un string de fecha/hora ODF a un objeto datetime."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        log.warning(f"Formato de fecha no reconocido: {dt_str}")
        return None

def _get_event_id_from_unit_id(unit_id: str) -> str | None:
    """
    Extrae y valida el Event ID (discipline + gender + event + phase) de un Unit ID.
    Retorna el Event ID canonico o None si el Unit ID es invalido.
    """
    if not unit_id:
        return None

    event_id = extract_event_id_from_unit(unit_id)
    # La nueva funcion extract_event_id_from_unit ya es la fuente de verdad.
    return event_id

def _parse_event_code(event_id: str):
    """ 
    Parsea el Event Code (ahora con ID completo) 
    Ej: SWMW4X200MFR----------FNL-
    Ej: SWMM400MFR--08010-----HEAT
    """
    try:
        event_parts = parse_event_id(event_id)
        if event_parts is None:
            raise ValueError("Formato invalido de EventID")

        gender_map = {'M': 'Men', 'W': 'Women', 'X': 'Mixed'}
        stroke_map = {
            'FR': 'Freestyle', 'MFR': 'Freestyle', 'BA': 'Backstroke',
            'BR': 'Breaststroke', 'BF': 'Butterfly', 'IM': 'Individual Medley',
            'MFR': 'Freestyle Relay', 'MMD': 'Medley Relay', 'MD': 'Medley Relay'
        }
        
        gender_code = event_parts.gender
        gender = gender_map.get(gender_code, 'Unknown')
        
        event_base = event_parts.event_type.rstrip('-') # Ej: 4X200MFR o 400MFR
        match = re.search(r'(\d+M|4X\d+M)(.+)', event_base)
        
        distance = None
        stroke_code = None
        
        if match:
            distance = match.group(1)
            stroke_code = match.group(2)
        else:
            stroke_code = event_base
        
        stroke = stroke_map.get(stroke_code, stroke_code)

        name = f"{gender}'s {distance.replace('M','m')} {stroke}" if distance else f"{gender}'s {stroke}"

        para_class_code = _derive_para_class(event_parts.event_modifier, stroke_code)
        if para_class_code:
            name = f"{name} {para_class_code}"

        return {
            'name': name.strip(), 
            'gender': gender_code, 
            'distance': distance, 
            'stroke': stroke_code
        }
    except Exception as e:
        log.error(f"Error parseando Event Code '{event_id}': {e}")
        return {'name': event_id, 'gender': 'U', 'distance': None, 'stroke': None}

def _get_phase_details(unit_node: etree._Element, unit_name: str):
    """
    Extrae la Fase y el UnitNum.
    DT_SCHEDULE_UPDATE tiene <Unit UnitNum="1">
    DT_CODES.EVENT_UNIT tiene <CodeSet Phase="FNL-" EventUnit="000100--">
    """
    unit_num_str = unit_node.get('UnitNum') # Para DT_SCHEDULE
    if not unit_num_str:
        unit_num_str = unit_node.get('EventUnit', '').rstrip('-') # Para DT_CODES
        
    unit_num = int(unit_num_str) if unit_num_str.isdigit() else None
    
    phase = unit_node.get('Phase') # Para DT_CODES
    if not phase:
        # Para DT_SCHEDULE, lo derivamos del nombre
        name_lower = unit_name.lower()
        if 'final' in name_lower: phase = 'Final'
        elif 'heat' in name_lower: phase = 'Heat'
        elif 'semifinal' in name_lower: phase = 'Semifinal'
        elif 'victory' in name_lower or 'medals' in name_lower: phase = 'Medal'
        else: phase = 'Other'
    
    # Limpiar Fases de ODF (ej. FNL-, HEAT)
    if 'FNL' in phase: phase = 'Final'
    if 'HEAT' in phase: phase = 'Heat'
    if 'SFNL' in phase: phase = 'Semifinal'
    if 'VICT' in phase: phase = 'Medal'

    return phase, unit_num


def _process_start_list_in_schedule(db: Session, unit_node: etree._Element, unit_code: str):
    """
    Busca <StartList> dentro de <Unit> y hace upsert en start_list_entries.
    """
    start_list_node = unit_node.find('StartList')
    if start_list_node is None:
        return 

    start_nodes = start_list_node.xpath('Start')
    start_list_data = []
    participant_data = []
    noc_stubs = set() 
    participant_ids_in_message = set()

    for start in start_nodes:
        competitor = start.find('Competitor')
        if competitor is None: continue
        participant_id = competitor.get('Code')
        lane = start.get('StartOrder') 
        noc = competitor.get('Organisation')
        if not participant_id: continue
        participant_id = participant_id.strip()
        participant_ids_in_message.add(participant_id)
        if noc: noc_stubs.add(noc)
        composition = []
        athlete_elements = competitor.xpath('Composition/Athlete')
        for ath in athlete_elements:
            desc = ath.find('Description')
            if desc is not None:
                composition.append({
                    "Code": ath.get('Code').strip(), "Order": ath.get('Order'),
                    "IFId": desc.get('IFId'), "GivenName": desc.get('GivenName'),
                    "FamilyName": desc.get('FamilyName')
                })
        start_list_data.append({
            'unit_id': unit_code, 'participant_id': participant_id,
            'lane': int(lane) if lane and lane.isdigit() else None,
            'composition': composition or None
        })
        desc = competitor.find('Description')
        if desc is not None and competitor.get('Type') == 'T':
            participant_data.append({
                'participant_id': participant_id, 'name': desc.get('TeamName'),
                'noc': noc, 'gender': 'X'
            })

    if noc_stubs:
        noc_data = [{'noc': n, 'long_name': n, 'short_name': n} for n in noc_stubs]
        stmt_noc = pg_insert(models.Noc).values(noc_data)
        stmt_noc = stmt_noc.on_conflict_do_nothing(index_elements=['noc'])
        db.execute(stmt_noc)

    if participant_ids_in_message:
        created_stub_count = ensure_participants_exist(db, participant_ids_in_message)
        if created_stub_count:
            log.info(f"Created {created_stub_count} stub participant(s).")

    if participant_data:
        stmt_part = pg_insert(models.Participant).values(participant_data)
        stmt_part = stmt_part.on_conflict_do_update(
            index_elements=['participant_id'],
            set_={'name': stmt_part.excluded.name, 'noc': stmt_part.excluded.noc}
        )
        db.execute(stmt_part)
    if start_list_data:
        stmt_sl = pg_insert(models.StartListEntry).values(start_list_data)
        stmt_sl = stmt_sl.on_conflict_do_update(
            constraint='_unit_participant_uc',
            set_={'lane': stmt_sl.excluded.lane, 'composition': stmt_sl.excluded.composition}
        )
        db.execute(stmt_sl)
        log.info(f"Start list actualizada desde DT_SCHEDULE para UnitID={unit_code} ({len(start_list_data)} entradas).")

# --- Parser Principal ---

def parse(root: etree._Element, db: Session):
    """
    Función de entrada para el router. Determina el tipo de mensaje.
    V3.4: Corregido NotNullViolation para 'phase'.
    """
    doc_type = root.get('DocumentType')
    doc_subtype = root.get('DocumentSubtype')
    
    log.info(f"Iniciando parser [parser_schedule.py] (v3.4) para {doc_type}/{doc_subtype}...")
    
    try:
        if doc_type == "DT_CODES" and doc_subtype == "EVENT_UNIT":
            _parse_codes_event_unit(db, root)
        
        elif doc_type == "DT_SCHEDULE" or doc_type == "DT_SCHEDULE_UPDATE":
            _parse_schedule_update(db, root) 
        
        else:
            log.warning(f"Tipo de documento no soportado por parser_schedule.py: {doc_type}/{doc_subtype}")
        
    except Exception as e:
        log.error(f"Error en [parser_schedule.py]: {e}", exc_info=True)
        db.rollback() 
        raise


def _parse_codes_event_unit(db: Session, message: etree._Element):
    """ 
    Parsea DT_CODES con Subtipo EVENT_UNIT 
    V3.4: De-duplica y rellena phase/unit_num.
    """
    
    codeset_elements = message.xpath('/OdfBody/Competition/CodeSet[@Group="Unit"]')
    
    if not codeset_elements:
        log.warning("[parser_schedule.py] No se encontraron <CodeSet Group=\"Unit\"> en DT_CODES.EVENT_UNIT.")
        return

    schedule_map = {}
    events_map = {}

    for code in codeset_elements:
        unit_id = code.get('Code')
        gender = code.get('Gender')
        discipline = code.get('Discipline')
        event_code = code.get('Event') 
        
        if not all([unit_id, gender, discipline, event_code]) or gender == '-':
            continue
            
        unit_id = unit_id.strip()
        normalized_unit_id = normalize_unit_id(unit_id)
        if not normalized_unit_id:
            log.warning(f"[parser_schedule.py] UnitID invalido en DT_CODES: {unit_id}")
            continue
        unit_id = normalized_unit_id

        raw_event_id = f"{discipline}{gender}{event_code}".strip()
        event_id = normalize_event_id(raw_event_id)
        if not event_id:
            log.warning(f"[parser_schedule.py] EventID invalido en DT_CODES: {raw_event_id}")
            continue

        event_id_from_unit = _get_event_id_from_unit_id(unit_id)
        if event_id_from_unit and event_id_from_unit != event_id:
            log.warning(
                f"[parser_schedule.py] EventID inconsistente para {unit_id}: "
                f"{event_id_from_unit} (desde Unit) != {event_id} (desde CodeSet)"
            )

        lang_element = code.find('Language[@Language="ENG"]')
        if lang_element is None:
            lang_element = code.find('Language')
        
        name = lang_element.get('Description') if lang_element is not None else unit_id
        
        # --- ¡LÓGICA CORREGIDA PARA PHASE Y UNIT_NUM! ---
        phase, unit_num = _get_phase_details(code, name)
        # -----------------------------------------------
        
        if event_id not in events_map:
            event_info = _parse_event_code(event_id)
            events_map[event_id] = {
                'event_id': event_id,
                'name': event_info['name'],
                'gender': event_info['gender'],
                'distance': event_info['distance'],
                'stroke': event_info['stroke']
            }

        if unit_id not in schedule_map:
            schedule_map[unit_id] = {
                'unit_id': unit_id,
                'event_id': event_id,
                'name': name.strip(),
                'phase': phase, # ¡Añadido!
                'unit_num': unit_num, # ¡Añadido!
                'status': 'SCHEDULED', 
            }
        
    events_data = list(events_map.values())
    schedule_data = list(schedule_map.values())

    if not schedule_data:
        log.warning("[parser_schedule.py] La lista de Schedule (desde DT_CODES) está vacía.")
        return

    if events_data:
        stmt_event = pg_insert(models.Event).values(events_data)
        stmt_event = stmt_event.on_conflict_do_update(
            index_elements=['event_id'],
            set_={
                'name': stmt_event.excluded.name, 
                'gender': stmt_event.excluded.gender,
                'distance': stmt_event.excluded.distance,
                'stroke': stmt_event.excluded.stroke
            }
        )
        db.execute(stmt_event)
        log.info(f"[parser_schedule.py] {len(events_data)} Eventos procesados/actualizados.")
    
    # --- ¡SQL CORREGIDO! ---
    # Asegúrate de que tu modelo Schedule tiene 'phase' y 'unit_num'
    stmt_sched = pg_insert(models.Schedule).values(schedule_data)
    stmt_sched = stmt_sched.on_conflict_do_update(
        index_elements=['unit_id'],
        set_={
            'event_id': stmt_sched.excluded.event_id,
            'name': stmt_sched.excluded.name,
            'phase': stmt_sched.excluded.phase,
            'unit_num': stmt_sched.excluded.unit_num
            # No tocamos 'start_time' ni 'status'
        }
    )
    db.execute(stmt_sched)
    # -----------------------
    log.info(f"[parser_schedule.py] Procesadas y actualizadas {len(schedule_data)} unidades desde DT_CODES.")
        

def _parse_schedule_update(db: Session, message: etree._Element):
    """ 
    Parsea DT_SCHEDULE y DT_SCHEDULE_UPDATE 
    V3.4: De-duplica y rellena phase/unit_num.
    """
    
    unit_elements = message.xpath('/OdfBody/Competition/Unit')
    if not unit_elements:
        log.warning("[parser_schedule.py] No se encontraron <Unit> en DT_SCHEDULE(_UPDATE).")
        return

    schedule_map = {}
    events_map = {}

    for unit in unit_elements:
        unit_id = unit.get('Code')
        if not unit_id:
            continue
            
        unit_id = unit_id.strip()
        normalized_unit_id = normalize_unit_id(unit_id)
        if not normalized_unit_id:
            log.warning(f"[parser_schedule.py] UnitID invalido en DT_SCHEDULE: {unit_id}")
            continue
        unit_id = normalized_unit_id

        status = unit.get('ScheduleStatus')
        start_time = _parse_datetime(unit.get('StartDate'))
        
        item_name_element = unit.find('ItemName[@Language="ENG"]')
        if item_name_element is None:
            item_name_element = unit.find('ItemName')
            
        name = item_name_element.get('Value') if item_name_element is not None else unit_id

        # --- ¡LÓGICA CORREGIDA v3.4! ---
        event_id = _get_event_id_from_unit_id(unit_id)
        phase, unit_num = _get_phase_details(unit, name)
        # ---------------------------------
        
        if not event_id or not validate_event_id(event_id):
            log.warning(f"[parser_schedule.py] EventID invalido para UnitID {unit_id}: {event_id}")
            continue

        if event_id not in events_map:
            event_info = _parse_event_code(event_id)
            events_map[event_id] = {
                'event_id': event_id,
                'name': event_info['name'],
                'gender': event_info['gender'],
                'distance': event_info['distance'],
                'stroke': event_info['stroke']
            }
            
        schedule_map[unit_id] = {
            'unit_id': unit_id,
            'event_id': event_id,
            'name': name.strip(),
            'status': status.strip() if status else 'SCHEDULED',
            'start_time': start_time,
            'phase': phase,       # ¡Añadido!
            'unit_num': unit_num  # ¡Añadido!
        }
        
        _process_start_list_in_schedule(db, unit, unit_id)
        
    events_data = list(events_map.values())
    schedule_data = list(schedule_map.values())

    if not schedule_data:
        log.warning("[parser_schedule.py] La lista de Schedule (desde DT_SCHEDULE_UPDATE) está vacía.")
        return

    if events_data:
        stmt_event = pg_insert(models.Event).values(events_data)
        stmt_event = stmt_event.on_conflict_do_update(
            index_elements=['event_id'],
            set_={
                'name': stmt_event.excluded.name, 
                'gender': stmt_event.excluded.gender,
                'distance': stmt_event.excluded.distance,
                'stroke': stmt_event.excluded.stroke
            }
        )
        db.execute(stmt_event)
        log.info(f"[parser_schedule.py] {len(events_data)} Eventos (stubs) procesados/actualizados.")

    # --- ¡SQL CORREGIDO! ---
    stmt_sched = pg_insert(models.Schedule).values(schedule_data)
    stmt_sched = stmt_sched.on_conflict_do_update(
        index_elements=['unit_id'],
        set_={
            'event_id': stmt_sched.excluded.event_id,
            'name': stmt_sched.excluded.name,
            'status': stmt_sched.excluded.status,
            'start_time': stmt_sched.excluded.start_time,
            'phase': stmt_sched.excluded.phase,      # ¡Añadido!
            'unit_num': stmt_sched.excluded.unit_num # ¡Añadido!
        }
    )
    db.execute(stmt_sched)
    # -----------------------
    log.info(f"[parser_schedule.py] Procesadas y actualizadas {len(schedule_data)} unidades desde DT_SCHEDULE_UPDATE.")
