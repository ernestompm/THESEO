from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, TIMESTAMP, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base

class Noc(Base):
    __tablename__ = 'nocs'
    
    noc = Column(String(3), primary_key=True)
    long_name = Column(String(100), nullable=False)
    short_name = Column(String(50))
    flag_path_local = Column(Text)
    flag_url_cloud = Column(Text)

class Participant(Base):
    __tablename__ = 'participants'

    participant_id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    noc = Column(String(3), ForeignKey('nocs.noc'))
    gender = Column(String(10)) 
    photo_url = Column(Text)

class Event(Base):
    __tablename__ = 'events'

    event_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    gender = Column(String(10))
    stroke = Column(String(10))
    distance = Column(String(20)) # VARCHAR para '4x100m'

class Schedule(Base):
    __tablename__ = 'schedule'
    
    unit_id = Column(String(50), primary_key=True)
    event_id = Column(String(50), ForeignKey('events.event_id'))
    name = Column(String(100), nullable=True) # Ej: "Men's 400m Freestyle S8 Heat 1"
    phase = Column(String(50))
    unit_num = Column(Integer)
    start_time = Column(TIMESTAMP(timezone=True)) 
    status = Column(String(20), default='SCHEDULED')
    config_data = Column(JSONB)

class Record(Base):
    __tablename__ = 'records'

    record_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(50), ForeignKey('events.event_id'))
    record_type = Column(String(10), nullable=False)
    time = Column(String(20), nullable=False)
    holder_name = Column(String(255))
    holder_noc = Column(String(3), ForeignKey('nocs.noc'))
    year = Column(Integer)

class MedalTally(Base):
    __tablename__ = 'medaltally'

    noc = Column(String(3), ForeignKey('nocs.noc'), primary_key=True)
    golds = Column(Integer, nullable=False, default=0)
    silvers = Column(Integer, nullable=False, default=0)
    bronzes = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)
    rank = Column(Integer, nullable=False, default=999)
    sort_rank = Column(Integer, nullable=True) # Puede ser NULL si no viene en el XML

class EventEntry(Base):
    __tablename__ = 'event_entries'

    entry_id = Column(Integer, primary_key=True, autoincrement=True)
    participant_id = Column(String(50), ForeignKey('participants.participant_id'))
    event_id = Column(String(50), ForeignKey('events.event_id'))
    qualification_mark = Column(String(20))
    qualification_details = Column(JSONB)

# --- NUEVOS MODELOS PARA DATOS EN VIVO DE SWM ---

class StartListEntry(Base):
    __tablename__ = 'start_list_entries'

    start_list_entry_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # El 'unit_id' vendrá del OdfBody @DocumentCode (ej: SWMW4X200MFR----------FNL-000100--)
    unit_id = Column(String(50), ForeignKey('schedule.unit_id'), nullable=False)
    
    # El 'participant_id' es el código de equipo/competidor (Result/Competitor @Code)
    participant_id = Column(String(50), ForeignKey('participants.participant_id'), nullable=False)
    
    # La calle vendrá de Result @StartOrder
    lane = Column(Integer)
    
    # Usamos JSONB para guardar la composición del equipo de relevos
    # Ej: [{"Code": "1946183", "Order": "1", "Name": "Iona Anderson"}, ...]
    composition = Column(JSONB) 

    # Restricciones para asegurar la integridad de los datos
    __table_args__ = (
        # Solo un competidor por calle en esta serie
        UniqueConstraint('unit_id', 'lane', name='_unit_lane_uc'), 
        # Solo una entrada por competidor en esta serie
        UniqueConstraint('unit_id', 'participant_id', name='_unit_participant_uc') 
    )

class Result(Base):
    __tablename__ = 'results'
    
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    unit_id = Column(String(50), ForeignKey('schedule.unit_id'), nullable=False)
    participant_id = Column(String(50), ForeignKey('participants.participant_id'), nullable=False)
    
    rank = Column(Integer, nullable=True)
    time = Column(String(20), nullable=True)
    diff = Column(String(20), nullable=True) # <-- Asegúrate de tener esta también
    reaction_time = Column(Float, nullable=True)
    splits = Column(JSONB, nullable=True)
    qualification_mark = Column(String(10), nullable=True) 
    irm = Column(String(10), nullable=True) 

    # --- ¡¡ESTA LÍNEA ES LA CRUCIAL!! ---
    record_mark = Column(String(10), nullable=True) 
    # ------------------------------------

    # Tu restricción única
    __table_args__ = (
        UniqueConstraint('unit_id', 'participant_id', name='_unit_participant_result_uc'),
    )

class Medallist(Base):
    __tablename__ = 'medallists'

    medallist_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # El ID del EVENTO (ej: SWMW400MIM------------------------)
    # Lo sacamos del DocumentCode del DT_MEDALLISTS
    event_id = Column(String(50), ForeignKey('events.event_id'), nullable=False)
    
    # El ID del participante (atleta o equipo)
    participant_id = Column(String(50), ForeignKey('participants.participant_id'), nullable=False)
    
    # El tipo de medalla ('G', 'S', 'B')
    medal_type = Column(String(1), nullable=False)
    
    # Opcional pero útil: El UnitID de la final donde se ganó
    final_unit_id = Column(String(50), ForeignKey('schedule.unit_id'), nullable=True)

    # Aseguramos que solo haya una medalla por participante por evento
    __table_args__ = (
        UniqueConstraint('event_id', 'participant_id', name='_event_participant_medal_uc'),
        # Podríamos añadir también ('event_id', 'medal_type') si queremos asegurar solo un oro, etc.
    )

class TournamentInfo(Base):
    __tablename__ = 'tournament_info'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    logo_path_local = Column(Text)
    logo_url_cloud = Column(Text)
    website_url = Column(Text)