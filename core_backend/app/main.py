import logging
from fastapi import FastAPI, Request, Response, status, Depends, WebSocket
from sqlalchemy.orm import Session
from . import processing, models, database, schemas, json_generator, websockets # Importamos los nuevos módulos

# --- Configuración del Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
# ---------------------------------

app = FastAPI()

@app.on_event("startup")
def startup_event():
    """
    Función que se ejecuta al iniciar la aplicación.
    Intenta conectar a la BBDD y verifica/crea las tablas.
    """
    logger.info("Iniciando aplicación. Intentando conectar a la base de datos...")
    try:
        # La siguiente línea requiere una conexión exitosa para funcionar.
        models.Base.metadata.create_all(bind=database.engine)
        # Si la línea anterior no falla, la conexión fue exitosa.
        logger.info("¡Conexión con la base de datos establecida y tablas verificadas con éxito!")
    except Exception as e:
        logger.error(f"Error al conectar o verificar las tablas de la BBDD: {e}")
        # Opcional: podrías querer que la app no inicie si no hay BBDD.
        # import sys
        # sys.exit(1)

@app.get("/")
def read_root():
    """ Endpoint 'Hola Mundo' """
    return {"Hello": "ODF Core"}


@app.post("/ingest-odf")
async def ingest_odf(
    request: Request, 
    db: Session = Depends(database.get_db_session) # ¡NUEVA LÍNEA!
):
    """
    Endpoint de ingesta. Ahora "depende" de una sesión de BBDD.
    FastAPI se encargará de crear (yield) y cerrar (finally) la sesión 'db'.
    """
    logger.info("¡Conexión recibida en /ingest-odf!")
    
    try:
        xml_content = await request.body()
        if not xml_content:
            logger.warning("Body vacío recibido.")
            return Response(content='{"error": "Empty body"}', 
                            media_type="application/json", 
                            status_code=status.HTTP_400_BAD_REQUEST)

        xml_string = xml_content.decode('utf-8')
        logger.info(f"ODF XML recibido (primeros 150 chars): {xml_string[:150]}...")
        
        # --- ¡CAMBIO IMPORTANTE! ---
        # Ahora pasamos la sesión 'db' a nuestro módulo de procesamiento
        logger.info("Enviando XML y sesión de BBDD al módulo de procesamiento...")
        processing.parse_odf_message(xml_string, db) # <-- ¡Parámetro 'db' añadido!
        # --------------------------

        await websockets.manager.broadcast("data updated")
        return {"status": "success", "message": "ODF received and sent to parser."}

    except Exception as e:
        logger.error(f"Error crítico al procesar el body del request: {e}", exc_info=True)
        return Response(content='{"error": "Internal server error processing body"}', 
                        media_type="application/json", 
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.post("/tournament-info", response_model=schemas.TournamentInfo)
def create_tournament_info(
    tournament_info: schemas.TournamentInfoCreate,
    db: Session = Depends(database.get_db_session)
):
    db_tournament_info = models.TournamentInfo(**tournament_info.dict())
    db.add(db_tournament_info)
    db.commit()
    db.refresh(db_tournament_info)
    return db_tournament_info

@app.get("/tournament-info", response_model=schemas.TournamentInfo)
def get_tournament_info(db: Session = Depends(database.get_db_session)):
    return db.query(models.TournamentInfo).first()

@app.get("/all-data")
def get_all_data(db: Session = Depends(database.get_db_session)):
    return json_generator.generate_json(db)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websockets.manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # For now, we're just broadcasting the data back to the client.
            # In a real application, you might want to do something more with the data.
            await websockets.manager.broadcast(f"Message text was: {data}")
    except Exception as e:
        pass
    finally:
        websockets.manager.disconnect(websocket)