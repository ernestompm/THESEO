import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .. import models

log = logging.getLogger(__name__)

# --- ¡¡DEFINICIÓN CORREGIDA!! ---
# (message, db) en lugar de (db, message)
def parse_dt_codes_noc(message: etree._Element, db: Session):
# -------------------------------
    """
    Parsea mensajes DT_CODES (Subtipos NOC y ORGANISATION)
    y rellena la tabla 'nocs'.
    
    Usa INSERT ... ON CONFLICT para actualizar Nocs creados 
    como "stubs" por otros parsers.
    """
    log.info("Iniciando parser [parser_nocs.py] (v3.1 - orden args corregido)...")
    
    codeset_elements = message.xpath('/OdfBody/Competition/CodeSet')
    
    if not codeset_elements:
        log.warning("[parser_nocs.py] No se encontraron elementos <CodeSet>.")
        return

    nocs_data = []
    for code in codeset_elements:
        noc_code = code.get('Code')
        if not noc_code:
            continue
        
        lang_element = code.find('Language[@Language="ENG"]')
        if lang_element is None:
            lang_element = code.find('Language')
            
        if lang_element is None:
            continue

        long_name = lang_element.get('LongDescription')
        short_name = lang_element.get('Description')

        if not long_name:
            long_name = short_name
        if not short_name:
            short_name = long_name
            
        if not long_name:
            long_name = noc_code
            short_name = noc_code

        nocs_data.append({
            'noc': noc_code.strip(),
            'long_name': long_name.strip(),
            'short_name': short_name.strip()
        })

    if not nocs_data:
        log.warning("[parser_nocs.py] La lista de NOCs procesada está vacía.")
        return

    try:
        stmt = pg_insert(models.Noc).values(nocs_data)
        
        stmt = stmt.on_conflict_do_update(
            index_elements=['noc'], # 'noc' es la Primary Key
            set_={
                'long_name': stmt.excluded.long_name,
                'short_name': stmt.excluded.short_name
            }
        )
        db.execute(stmt)
        log.info(f"[parser_nocs.py] Procesados y actualizados {len(nocs_data)} NOCs.")
        
    except Exception as e:
        log.error(f"Error en [parser_nocs.py] al hacer upsert en BBDD: {e}", exc_info=True)
        db.rollback() 
        raise