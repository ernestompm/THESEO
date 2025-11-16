import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert 
from .. import models
import datetime
import re 

logger = logging.getLogger(__name__)

# --- INICIO DE FUNCIONES HELPER ---
# (Copiadas aquí para que no tengas que importarlas)

def _ensure_noc_exists(db: Session, noc: str):
    """Crea un NOC si no existe, para evitar errores de ForeignKey."""
    if not noc: return
    try:
        stmt = pg_insert(models.Noc).values(
            noc=noc, long_name=noc, short_name=noc
        ).on_conflict_do_nothing(index_elements=['noc'])
        db.execute(stmt)
    except Exception as e:
        logger.error(f"Error al asegurar NOC '{noc}': {e}", exc_info=False)
        pass

def _ensure_event_exists(db: Session, event_id_normalized: str):
    """
    Crea un "stub" de evento si no existe, para evitar errores de ForeignKey.
    Extrae el género del event_id para cumplir con NOT NULL.
    """
    if not event_id_normalized: return
    
    gender_code = 'U' 
    if len(event_id_normalized) >= 4:
        g_code = event_id_normalized[3:4] # M, W, o X
        if g_code in ('M', 'W', 'X'):
             gender_code = g_code
        else:
            logger.warning(f"No se pudo determinar género de event_id: {event_id_normalized}")
            
    try:
        stmt = pg_insert(models.Event).values(
            event_id=event_id_normalized,
            name=event_id_normalized, 
            gender=gender_code 
        ).on_conflict_do_nothing(index_elements=['event_id'])
        db.execute(stmt)
    except Exception as e:
        logger.error(f"Error al asegurar Evento '{event_id_normalized}': {e}", exc_info=False)
        pass

# --- FIN DE FUNCIONES HELPER ---


def parse(root: etree._Element, db: Session):
    """ 
    Parsea un mensaje de Récords (DT_RECORD) y hace UPSERT en 'records'.
    
    V3.0:
    - Mantiene los IDs completos (con guiones).
    - De-duplica los récords del XML antes de enviarlos a la BBDD.
    - Asegura que 'events' y 'nocs' existan (crea stubs).
    """
    logger.info("Iniciando parser [parser_records.py] (v3.0)...")

    record_nodes = root.xpath(".//Competition/Record")
    
    if not record_nodes:
        logger.warning("Mensaje DT_RECORD recibido, pero no se encontraron elementos <Record>.")
        return

    records_map = {} 

    try:
        for record_node in record_nodes:
            # --- ¡CAMBIO V3.0! ---
            # No recortamos los guiones. Usamos el ID completo.
            event_id = record_node.get('Code')
            if not event_id:
                continue
            
            event_id = event_id.strip() # Ej: SWMM50MFR---01010-----------------
            # --------------------
            
            _ensure_event_exists(db, event_id) # Asegurar stub de evento

            record_type_nodes = record_node.xpath(".//RecordType")
            for type_node in record_type_nodes:
                record_type = type_node.get('RecordType')
                if not record_type: continue
                
                record_data = type_node.find(".//RecordData")
                if record_data is None:
                    continue

                record_time = record_data.get('Result')
                if not record_time: continue

                # NOC
                record_noc = None
                competitor_node = record_data.find(".//Competitor")
                if competitor_node is not None:
                    record_noc = competitor_node.get('Organisation')
                    _ensure_noc_exists(db, record_noc) 

                # Año
                record_year = None
                date_str = record_data.get('Date')
                if date_str:
                    try:
                        if len(date_str) >= 4 and date_str[:4].isdigit():
                            record_year = int(date_str[:4])
                        else:
                            record_year = datetime.datetime.strptime(date_str.strip(), '%Y-%m-%d').year
                    except ValueError:
                        logger.warning(f"Formato de fecha de récord no reconocido: {date_str}")
                        pass 

                # Nombre del poseedor
                holder_name = ""
                athlete_node = record_data.find(".//Athlete/Description")
                if athlete_node is not None:
                    holder_name = athlete_node.get('PrintName') 
                    if not holder_name:
                        given_name = athlete_node.get('GivenName', '')
                        family_name = athlete_node.get('FamilyName', '')
                        holder_name = f"{family_name} {given_name}".strip().upper()
                else:
                    team_node = record_data.find(".//Competitor/Description")
                    if team_node is not None:
                        holder_name = team_node.get('TeamName')

                # De-duplicación
                key = (event_id, record_type) 
                records_map[key] = {
                    'event_id': event_id, # ID completo
                    'record_type': record_type,
                    'time': record_time,
                    'holder_name': holder_name or None,
                    'holder_noc': record_noc,
                    'year': record_year
                }

        final_records_data = list(records_map.values())
                
        if not final_records_data:
            logger.info("Procesamiento [parser_records.py] completo. No se encontraron récords válidos.")
            db.commit() 
            return

        # --- Ejecutar UPSERT Masivo ---
        stmt = pg_insert(models.Record).values(final_records_data)
        stmt = stmt.on_conflict_do_update(
            constraint='uq_record', 
            set_={
                'time': stmt.excluded.time,
                'holder_name': stmt.excluded.holder_name,
                'holder_noc': stmt.excluded.holder_noc,
                'year': stmt.excluded.year
            }
        )
        db.execute(stmt)
        # db.commit() # Quitado. Se hará en processing.py
        logger.info(f"Procesamiento [parser_records.py] completo. {len(final_records_data)} récords procesados/actualizados.")

    except Exception as e:
        logger.error(f"Error en [parser_records.py]: {e}", exc_info=True)
        db.rollback()
        raise