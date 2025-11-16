import logging
from lxml import etree
from sqlalchemy.orm import Session
from . import models, database

# Importar TODOS los parsers
from .parsers import (
    parser_results_swm,
    parser_records,
    parser_participants,
    parser_schedule,    # <-- Este maneja DT_CODES.EVENT_UNIT y DT_SCHEDULE_UPDATE
    parser_result,
    parser_teams,
    parser_nocs,
    parser_events,
    parser_config
)

log = logging.getLogger(__name__)

# --- ¡MAPA DE ENRUTAMIENTO ACTUALIZADO! ---
ROUTING_MAP = {
    # --- RESULTADOS SWM (Natación) ---
    ("DT_RESULT", "SWM", "ANY"): parser_results_swm.parse_dt_result,
    
    # --- RÉCORDS SWM (Natación) ---
    ("DT_RECORD", "SWM", "ANY"): parser_records.parse,
    
    # --- PARTICIPANTES (Todos los deportes) ---
    ("DT_PARTIC", "ANY", "ANY"): parser_participants.parse,
    ("DT_PARTIC_UPDATE", "ANY", "ANY"): parser_participants.parse,
    
    # --- EQUIPOS (Todos los deportes) ---
    ("DT_PARTIC_TEAMS", "ANY", "ANY"): parser_teams.parse,
    ("DT_PARTIC_TEAMS_UPDATE", "ANY", "ANY"): parser_teams.parse,
    
    # --- RESULTADOS GENÉRICOS (Otros deportes) ---
    ("DT_RESULT", "ANY", "ANY"): parser_result.parse,

    # --- DT_CODES ---
    ("DT_CODES", "ANY", "NOC"): parser_nocs.parse_dt_codes_noc,
    ("DT_CODES", "ANY", "ORGANISATION"): parser_nocs.parse_dt_codes_noc,
    
    ("DT_CODES", "ANY", "EVENT"): parser_events.parse_dt_codes_event,
    ("DT_CODES", "ANY", "RECORD"): parser_events.parse_dt_codes_event,

    # --- SCHEDULE (MAESTRO Y ACTUALIZACIONES) ---
    ("DT_CODES", "ANY", "EVENT_UNIT"): parser_schedule.parse, # <-- ¡NUEVO!
    ("DT_SCHEDULE_UPDATE", "ANY", "ANY"): parser_schedule.parse, # <-- ¡NUEVO!
    ("DT_SCHEDULE", "ANY", "ANY"): parser_schedule.parse, # <-- ¡NUEVO!

    ("DT_CONFIG", "ANY", "ANY"): parser_config.parse, # <-- ¡NUEVO!
}
# ---------------------------------------------------

def get_parser_function(doc_type, discipline, subtype):
    """
    Busca el parser apropiado en el ROUTING_MAP.
    """
    # 1. Intento de match exacto (Tipo, Disciplina, Subtipo)
    parser_func = ROUTING_MAP.get((doc_type, discipline, subtype))
    if parser_func:
        return parser_func, f"Exact match: ({doc_type}, {discipline}, {subtype})"

    # 2. Intento de match (Tipo, Disciplina, ANY Subtipo)
    parser_func = ROUTING_MAP.get((doc_type, discipline, "ANY"))
    if parser_func:
        return parser_func, f"Discipline match: ({doc_type}, {discipline}, ANY)"

    # 3. Intento de match (Tipo, ANY Disciplina, Subtipo)
    parser_func = ROUTING_MAP.get((doc_type, "ANY", subtype))
    if parser_func:
        return parser_func, f"Subtype match: ({doc_type}, ANY, {subtype})"

    # 4. Intento de match (Tipo, ANY Disciplina, ANY Subtipo)
    parser_func = ROUTING_MAP.get((doc_type, "ANY", "ANY"))
    if parser_func:
        return parser_func, f"Type match: ({doc_type}, ANY, ANY)"

    return None, "No parser found"

def parse_odf_message(xml_string: str, db: Session):
    """
    Punto de entrada principal. Parsea el XML y lo enruta al parser correcto.
    """
    try:
        root = etree.fromstring(xml_string.encode('utf-8'), parser=etree.XMLParser(recover=True))
        
        odf_body = root.find('.//OdfBody')
        if odf_body is None:
            if root.tag == 'OdfBody':
                odf_body = root
            else:
                log.error("No se pudo encontrar el nodo <OdfBody> en el XML.")
                return

        doc_type = odf_body.get('DocumentType')
        discipline = odf_body.get('DocumentCode', 'GEN')[:3] 
        subtype = odf_body.get('DocumentSubtype')

        if not doc_type:
            log.error("XML inválido: No se encontró DocumentType en <OdfBody>.")
            return
            
        if not subtype:
            subtype = "ANY" 
            
        log.info(f"XML parseado. Tipo: {doc_type}, Disciplina: {discipline}, Subtipo: {subtype}. Enrutando a parser...")

        parser_func, reason = get_parser_function(doc_type, discipline, subtype)
        
        if parser_func:
            log.info(f"Parser encontrado ({reason}). Ejecutando...")
            # ¡¡Importante!! Pasamos 'odf_body' al parser
            parser_func(odf_body, db) 
            db.commit() 
            log.info(f"Procesamiento de {doc_type} (Sub: {subtype}) completado con éxito.")
        else:
            log.warning(f"No se encontró un parser para la combinación: Tipo={doc_type}, Disciplina={discipline}, Subtipo={subtype}")
            db.rollback() 

    except etree.XMLSyntaxError as e:
        log.error(f"Error de sintaxis XML: {e}", exc_info=True)
        db.rollback()
    except Exception as e:
        log.error(f"Error inesperado durante el parseo de XML o procesamiento: {e}", exc_info=True)
        db.rollback()
        raise