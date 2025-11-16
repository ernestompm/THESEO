import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from .. import models
from .id_validators import normalize_unit_id

logger = logging.getLogger(__name__)

def _get_phase_from_code(unit_code: str):
    # ¡HELPER CORREGIDO!
    if 'SFNL' in unit_code: return 'Semifinal' # <-- Arreglo para SFNL
    if 'FNL' in unit_code: return 'Final'
    if 'HEAT' in unit_code: return 'Heat'
    return 'Unknown'

def parse(root: etree._Element, db: Session):
    """ 
    Parsea un mensaje de Configuración (DT_CONFIG).
    
    Versión 2.2:
    - Arreglado el helper _get_phase_from_code.
    - Añadido filtro para ignorar unidades "paraguas" (sin UnitNum).
    """
    logger.info("Iniciando parser [parser_config.py] (v2.2)...")

    #
    config_nodes = root.xpath(".//Competition/Configs/Config")
    
    if not config_nodes:
        logger.warning("DT_CONFIG: No se encontraron <Config>.")
        return

    processed_count = 0
    ignored_count = 0
    try:
        for config_node in config_nodes:
            unit_id = config_node.get('Unit')
            if not unit_id:
                continue
            unit_id = unit_id.strip()

            normalized_unit_id = normalize_unit_id(unit_id)
            if not normalized_unit_id:
                logger.warning(f"DT_CONFIG: UnitID fuera de especificacion: {unit_id}")
                continue
            unit_id = normalized_unit_id

            # --- ¡NUEVO FILTRO! ---
            # El ODF de DT_CONFIG no tiene 'UnitNum'. ¡Pero podemos
            # deducirlo! Las unidades "paraguas" terminan en '--------'.
            if unit_id.endswith('--------'):
                ignored_count += 1
                continue
            # --- FIN DEL FILTRO ---

            phase = _get_phase_from_code(unit_id)

            config_dict = {}
            for ext_config in config_node.xpath("./ExtendedConfig"):
                code = ext_config.get('Code')
                value = ext_config.get('Value')
                pos = ext_config.get('Pos', 'F')
                
                if code == 'INTERMEDIATE':
                    stroke_node = ext_config.find(".//ExtendedConfigItem")
                    if stroke_node is not None:
                        config_dict[f'INT_{pos}_STROKE'] = stroke_node.get('Value')
                    config_dict[f'INT_{pos}'] = value
                else:
                    config_dict[code] = value
            
            if not config_dict:
                continue 

            stmt = insert(models.Schedule).values(
                unit_id=unit_id,
                phase=phase,
                config_data=config_dict
            ).on_conflict_do_update(
                index_elements=['unit_id'],
                set_={
                    'phase': phase, # Asegurarnos de actualizar la fase
                    'config_data': models.Schedule.config_data.op('||')(config_dict)
                }
            )
            db.execute(stmt)
            processed_count += 1

        db.commit()
        logger.info(f"Procesamiento [parser_config.py] completo. "
                    f"Unidades procesadas: {processed_count}, Paraguas ignoradas: {ignored_count}.")
    except Exception as e:
        logger.error(f"Error en [parser_config.py]: {e}", exc_info=True)
        db.rollback()
