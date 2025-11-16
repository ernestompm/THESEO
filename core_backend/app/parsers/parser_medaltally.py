import logging
from lxml import etree
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..models import MedalTally

log = logging.getLogger(__name__)

def parse_dt_medals(db: Session, message: etree._Element):
    """
    Parsea un mensaje DT_MEDALS y actualiza la tabla medaltally (medallero),
    incluyendo ahora el SortRank.
    """
    
    medals_table = message.find('Competition/MedalStandings/MedalsTable')
    if medals_table is None:
        log.warning("DT_MEDALS recibido, pero no se encontró MedalsTable.")
        return

    medal_lines = medals_table.xpath('MedalLine')
    tally_data = []

    try:
        for line in medal_lines:
            noc = line.get('Organisation')
            rank = line.get('Rank')
            # --- ¡LEER SORT RANK! ---
            sort_rank = line.get('SortRank') 
            
            total_medals_node = line.find('MedalNumber[@Type="TOT"]')
            
            if total_medals_node is None:
                continue 

            gold = total_medals_node.get('Gold', '0')
            silver = total_medals_node.get('Silver', '0')
            bronze = total_medals_node.get('Bronze', '0')
            total = total_medals_node.get('Total', '0')

            tally_data.append({
                'noc': noc,
                'rank': int(rank),
                # --- ¡AÑADIR SORT RANK A LOS DATOS! ---
                'sort_rank': int(sort_rank) if sort_rank else None,
                'golds': int(gold),
                'silvers': int(silver),
                'bronzes': int(bronze),
                'total': int(total)
            })

        if not tally_data:
            log.info("DT_MEDALS procesado, pero no se encontraron datos de medallero.")
            return

        # --- Ejecutar "Upsert" de Medallero ---
        stmt = pg_insert(MedalTally).values(tally_data)
        
        # Si el NOC ya existe, actualiza todos los contadores
        stmt = stmt.on_conflict_do_update(
            index_elements=['noc'], # Tu Primary Key
            set_={
                'rank': stmt.excluded.rank,
                # --- ¡AÑADIR SORT RANK AL UPDATE! ---
                'sort_rank': stmt.excluded.sort_rank, 
                'golds': stmt.excluded.golds,
                'silvers': stmt.excluded.silvers,
                'bronzes': stmt.excluded.bronzes,
                'total': stmt.excluded.total
            }
        )
        db.execute(stmt)
        db.commit()
        log.info(f"Medallero (DT_MEDALS) actualizado con {len(tally_data)} NOCs (incl. SortRank).")

    except Exception as e:
        log.error(f"Error parseando DT_MEDALS: {e}", exc_info=True)
        db.rollback()
        raise