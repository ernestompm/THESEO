import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .. import models
from .id_validators import normalize_unit_id
from .participant_helpers import ensure_participants_exist

logger = logging.getLogger(__name__)

def parse(root: etree._Element, db: Session):
    """ 
    Parsea un mensaje genérico de Resultados (DT_RESULT).
    
    NOTA: Este es un parser genérico. Para deportes específicos
    como SWM (Natación), se utiliza un parser especializado.
    """
    
    # Extraer el DocumentCode (UnitID) del OdfBody
    odf_body = root.find('.//OdfBody')
    if odf_body is None:
        if root.tag == 'OdfBody': odf_body = root
        else:
            logger.warning("[parser_result] No se pudo encontrar OdfBody.")
            return

    unit_id = odf_body.get('DocumentCode')
    if not unit_id:
        logger.warning("[parser_result] No se pudo encontrar DocumentCode en OdfBody.")
        return
        
    unit_id = unit_id.strip()
    normalized_unit_id = normalize_unit_id(unit_id)
    if not normalized_unit_id:
        logger.warning(f"[parser_result] UnitID fuera de especificacion y no normalizable: {unit_id}")
        return
    unit_id = normalized_unit_id

    logger.info(f"Iniciando parser genérico [parser_result.py] para UnitID: {unit_id}...")

    # --- INICIO DE LÓGICA DE PARSEO GENÉRICO ---
    # Esta es una implementación básica. La ajustaremos
    # si necesitamos parsear otros deportes.
    
    results_data = []
    result_nodes = root.xpath(".//Competition/Result")
    participant_ids_in_message = set()
    
    try:
        for res_node in result_nodes:
            competitor_node = res_node.find('Competitor')
            if competitor_node is None:
                continue
                
            participant_id = competitor_node.get('Code')
            if not participant_id:
                continue
            
            participant_id = participant_id.strip()
            participant_ids_in_message.add(participant_id)
            
            rank = res_node.get('Rank')
            result_time = res_node.get('Result')
            irm = res_node.get('IRM')
            qual_mark = res_node.get('QualificationMark')
            
            results_data.append({
                'unit_id': unit_id,
                'participant_id': participant_id,
                'rank': int(rank) if rank and rank.isdigit() else None,
                'time': result_time,
                'irm': irm,
                'qualification_mark': qual_mark,
                # Otros campos (diff, reaction_time, splits) se dejan como NULL
            })

        if not results_data:
            logger.warning(f"[parser_result] No se encontraron datos de <Result> para {unit_id}.")
            return

        if participant_ids_in_message:
            created_stub_count = ensure_participants_exist(db, participant_ids_in_message)
            if created_stub_count:
                logger.info(f"Created {created_stub_count} stub participant(s).")

        stmt_res = pg_insert(models.Result).values(results_data)
        stmt_res = stmt_res.on_conflict_do_update(
            constraint='_unit_participant_result_uc',
            set_={
                'rank': stmt_res.excluded.rank,
                'time': stmt_res.excluded.time,
                'irm': stmt_res.excluded.irm,
                'qualification_mark': stmt_res.excluded.qualification_mark
            }
        )
        db.execute(stmt_res)
        
        logger.info(f"Procesamiento genérico [parser_result.py] completo para {unit_id}. {len(results_data)} resultados guardados.")
        db.commit()

    except Exception as e:
        logger.error(f"Error en [parser_result.py] (UnitID={unit_id}): {e}", exc_info=True)
        db.rollback()
        raise
