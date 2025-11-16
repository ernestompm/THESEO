import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import update
from .. import models 
import re # ¡Asegúrate de importar re!
from .id_validators import extract_event_id_from_unit, normalize_unit_id, validate_event_id
from .participant_helpers import ensure_participants_exist

log = logging.getLogger(__name__)

# --- INICIO DE FUNCIONES HELPER ---

def _get_event_id_from_unit_id(unit_id: str):
    """
    Extrae el Event ID (discipline + gender + event + phase) del Unit ID validado.
    """
    if not unit_id:
        return None

    event_id = extract_event_id_from_unit(unit_id)
    if event_id and validate_event_id(event_id):
        return event_id

    log.warning(f"No se pudo derivar un EventID valido desde UnitID: {unit_id}.")
    return None


def _ensure_event_stub(db: Session, event_id: str):
    """Crea un stub de Evento si no existe (V3.0 - usa ID completo)"""
    if not event_id: return
    
    gender_code = 'U' 
    if len(event_id) >= 4:
        g_code = event_id[3:4]
        if g_code in ('M', 'W', 'X'):
             gender_code = g_code
            
    try:
        stmt = pg_insert(models.Event).values(
            event_id=event_id,
            name=event_id, # Nombre es solo el ID hasta que DT_CODES lo llene
            gender=gender_code 
        ).on_conflict_do_nothing(index_elements=['event_id'])
        db.execute(stmt)
    except Exception as e:
        log.error(f"Error al asegurar Evento '{event_id}': {e}", exc_info=False)
        pass

def _ensure_noc_stub(db: Session, noc: str):
    """Crea un stub de NOC si no existe."""
    if not noc: return
    try:
        stmt = pg_insert(models.Noc).values(
            noc=noc, long_name=noc, short_name=noc
        ).on_conflict_do_nothing(index_elements=['noc'])
        db.execute(stmt)
    except Exception as e:
        log.error(f"Error al asegurar NOC '{noc}': {e}", exc_info=False)
        pass

def _ensure_participant_stub(db: Session, participant_id: str, name: str, noc: str, gender: str):
    """Crea un stub de Participante si no existe."""
    if not participant_id: return
    try:
        stmt = pg_insert(models.Participant).values(
            participant_id=participant_id,
            name=name,
            noc=noc,
            gender=gender
        ).on_conflict_do_nothing(index_elements=['participant_id'])
        db.execute(stmt)
    except Exception as e:
        log.error(f"No se pudo asegurar Participante '{participant_id}': {e}", exc_info=False)
        pass

# --- FIN DE FUNCIONES HELPER ---

def parse_dt_result(message: etree._Element, db: Session):
# -------------------------------
    """
    Despachador principal para todos los mensajes DT_RESULT de SWM.
    V3.2: Orden de argumentos corregido.
    """
    
    unit_id = "Unknown" 
    
    try:
        unit_id = message.get('DocumentCode')
        if not unit_id:
             log.error("Mensaje DT_RESULT inválido. Falta DocumentCode (UnitID).")
             return
        unit_id = unit_id.strip()
        normalized_unit_id = normalize_unit_id(unit_id)
        if not normalized_unit_id:
            log.error(f"Mensaje DT_RESULT con UnitID inválido y no normalizable: {unit_id}")
            return
        unit_id = normalized_unit_id

        result_status = message.get('ResultStatus')
        if not result_status:
            log.error(f"Mensaje DT_RESULT inválido. Falta ResultStatus (UnitID={unit_id}).")
            return

        log.info(f"Procesando SWM DT_RESULT: UnitID={unit_id}, Status={result_status}")
        
        event_id = _get_event_id_from_unit_id(unit_id)
        if event_id:
            _ensure_event_stub(db, event_id)
        else:
            log.warning(f"Se omite la creacion del stub de evento por EventID invalido (UnitID={unit_id}).")

        if result_status == "START_LIST":
            _handle_start_list(db, message, unit_id)
        
        elif result_status in ("LIVE", "UNOFFICIAL", "OFFICIAL"):
            _handle_results(db, message, unit_id, result_status)
        
        else:
            log.warning(f"ResultStatus no manejado: {result_status} para UnitID={unit_id}")

        _update_schedule_status(db, unit_id, result_status)
        
        log.info(f"Procesamiento exitoso (sin commit) para UnitID={unit_id}, Status={result_status}")

    except Exception as e:
        log.error(f"Error parseando DT_RESULT (UnitID={unit_id}): {e}", exc_info=True)
        db.rollback()
        raise


def _handle_start_list(db: Session, message: etree._Element, unit_id: str):
    """
    Procesa un DT_RESULT con ResultStatus="START_LIST".
    (V3.0 - Mantiene IDs completos)
    """
    start_list_data = []
    participant_data = [] 
    noc_stubs = set()
    participant_ids_in_message = set()
    
    result_elements = message.xpath('/OdfBody/Competition/Result')

    for res in result_elements:
        competitor = res.find('Competitor')
        if competitor is None:
            continue
        
        participant_id = competitor.get('Code').strip()
        lane = res.get('StartOrder')
        noc = competitor.get('Organisation')
        
        if not participant_id:
            continue
        
        participant_ids_in_message.add(participant_id)
        if noc: noc_stubs.add(noc)
            
        composition = []
        athlete_elements = competitor.xpath('Composition/Athlete')
        for ath in athlete_elements:
            desc = ath.find('Description')
            if desc is None: continue 
            
            composition.append({
                "Code": ath.get('Code').strip(),
                "Order": ath.get('Order'),
                "IFId": desc.get('IFId'),
                "GivenName": desc.get('GivenName'),
                "FamilyName": desc.get('FamilyName')
            })

        start_list_data.append({
            'unit_id': unit_id,
            'participant_id': participant_id,
            'lane': int(lane) if lane and lane.isdigit() else None,
            'composition': composition or None 
        })
        
        desc = competitor.find('Description')
        if desc is not None and competitor.get('Type') == 'T':
            participant_data.append({
                'participant_id': participant_id,
                'name': desc.get('TeamName'),
                'noc': noc,
                'gender': 'X' 
            })

    # --- Stubs ---
    if noc_stubs:
        noc_data = [{'noc': n, 'long_name': n, 'short_name': n} for n in noc_stubs]
        stmt_noc = pg_insert(models.Noc).values(noc_data).on_conflict_do_nothing(index_elements=['noc'])
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
    # -------------

    if start_list_data:
        stmt_sl = pg_insert(models.StartListEntry).values(start_list_data)
        stmt_sl = stmt_sl.on_conflict_do_update(
            constraint='_unit_participant_uc', 
            set_={
                'lane': stmt_sl.excluded.lane,
                'composition': stmt_sl.excluded.composition
            }
        )
        db.execute(stmt_sl)
    
    log.info(f"START_LIST: Procesadas {len(start_list_data)} entradas para UnitID={unit_id}")


def _handle_results(db: Session, message: etree._Element, unit_id: str, status: str):
    """
    Procesa DT_RESULT con Status="LIVE", "UNOFFICIAL" u "OFFICIAL".
    (V3.0 - Mantiene IDs completos)
    """
    results_data = []
    participant_ids_in_message = set()
    
    result_elements = message.xpath('/OdfBody/Competition/Result')

    for res in result_elements:
        competitor = res.find('Competitor')
        if competitor is None:
            continue 
            
        participant_id = competitor.get('Code').strip()
        if not participant_id:
            continue

        participant_ids_in_message.add(participant_id)

        rank = res.get('Rank')
        time = res.get('Result')
        diff = res.get('Diff')
        irm = res.get('IRM')
        qual_mark = res.get('QualificationMark')

        reaction_time_elem = res.find(
            'Composition/Athlete[@Order="1"]/ExtendedResults/ExtendedResult[@Type="ER"][@Code="REACT_TIME"]'
        )
        reaction_time = reaction_time_elem.get('Value') if reaction_time_elem is not None else None
        
        record_mark = None
        record_nodes = res.xpath('./ExtendedResults/ExtendedResult[@Type="RECORD"]')
        
        for rec in record_nodes:
            code = rec.get('Code') 
            if code == 'WR':
                record_mark = 'WR'
                break 
            elif code == 'OR':
                record_mark = 'OR'
            elif code == 'CR' and not record_mark:
                record_mark = 'CR'

        splits_json = {
            "team_splits": [],
            "athlete_splits": {}
        }

        team_splits_elems = res.xpath('ExtendedResults/ExtendedResult[@Type="PROGRESS"][@Code="INTERMEDIATE"]')
        for split in team_splits_elems:
            splits_json["team_splits"].append({
                "Pos": split.get('Pos'),
                "Value": split.get('Value'),
                "Rank": split.get('Rank'),
                "Diff": split.get('Diff')
            })
        
        athlete_elements = competitor.xpath('Composition/Athlete')
        for ath in athlete_elements:
            athlete_code = ath.get('Code').strip()
            athlete_splits = []
            ath_splits_elems = ath.xpath('ExtendedResults/ExtendedResult[@Type="PROGRESS"][@Code="INTERMEDIATE"]')
            for split in ath_splits_elems:
                athlete_splits.append({
                    "Pos": split.get('Pos'),
                    "Value": split.get('Value'),
                    "Rank": split.get('Rank'),
                    "Value2": split.get('Value2') 
                })
            if athlete_splits:
                splits_json["athlete_splits"][athlete_code] = athlete_splits

        results_data.append({
            'unit_id': unit_id,
            'participant_id': participant_id,
            'rank': int(rank) if rank and rank.isdigit() else None,
            'time': time,
            'diff': diff,
            'reaction_time': reaction_time,
            'irm': irm,
            'qualification_mark': qual_mark,
            'splits': splits_json if splits_json["team_splits"] or splits_json["athlete_splits"] else None,
            'record_mark': record_mark
        })

    if participant_ids_in_message:
        created_stub_count = ensure_participants_exist(db, participant_ids_in_message)
        if created_stub_count:
            log.info(f"Created {created_stub_count} stub participant(s).")

    if results_data:
        stmt_res = pg_insert(models.Result).values(results_data)
        
        stmt_res = stmt_res.on_conflict_do_update(
            constraint='_unit_participant_result_uc',
            set_={
                'rank': stmt_res.excluded.rank,
                'time': stmt_res.excluded.time,
                'diff': stmt_res.excluded.diff,
                'reaction_time': stmt_res.excluded.reaction_time,
                'irm': stmt_res.excluded.irm,
                'qualification_mark': stmt_res.excluded.qualification_mark,
                'splits': stmt_res.excluded.splits,
                'record_mark': stmt_res.excluded.record_mark 
            }
        )
        db.execute(stmt_res)
    
    log.info(f"{status}: Procesados {len(results_data)} resultados para UnitID={unit_id}")


def _update_schedule_status(db: Session, unit_id: str, status: str):
    """
    Actualiza el estado de la prueba en la tabla Schedule.
    (V3.0 - Usa ID completo)
    """
    
    log.debug(f"Ejecutando UPDATE en schedule para UnitID={unit_id}, Status={status}")
    
    stmt = (
        update(models.Schedule)
        .where(models.Schedule.unit_id == unit_id)
        .values(status=status)
        .execution_options(synchronize_session=False) 
    )
    
    try:
        db.execute(stmt)
    except Exception as e:
        log.error(f"No se pudo actualizar el estado del schedule para {unit_id}: {e}", exc_info=False)
        pass
