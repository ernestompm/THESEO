import logging
from fastapi import FastAPI, Request, Response, status, Depends
from sqlalchemy.orm import Session
from . import processing, models, database # Importamos los nuevos módulos

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

        return {"status": "success", "message": "ODF received and sent to parser."}

    except Exception as e:
        logger.error(f"Error crítico al procesar el body del request: {e}", exc_info=True)
        return Response(content='{"error": "Internal server error processing body"}', 
                        media_type="application/json", 
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)