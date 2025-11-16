import sys
import time
import logging
import os
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Configuración ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOTFOLDER_PATH = os.path.join(BASE_DIR, "hotfolder")
PROCESADOS_PATH = os.path.join(BASE_DIR, "procesados")
ERROR_PATH = os.path.join(BASE_DIR, "error")
CORE_BACKEND_URL = "http://127.0.0.1:8000/ingest-odf"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
# ---------------------

def safe_move(source_filepath: str, dest_folder: str):
    """
    NUEVA FUNCIÓN: Mueve un fichero de forma segura.
    Si el destino ya existe, renombra el fichero fuente 
    añadiendo un timestamp para evitar colisiones.
    """
    filename = os.path.basename(source_filepath)
    dest_filepath = os.path.join(dest_folder, filename)
    
    # Comprobar si el destino ya existe
    if os.path.exists(dest_filepath):
        # Crear un nuevo nombre de fichero único
        filename_without_ext, ext = os.path.splitext(filename)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        new_filename = f"{filename_without_ext}_{timestamp}{ext}"
        dest_filepath = os.path.join(dest_folder, new_filename)
        logger.warning(f"El destino '{filename}' ya existe. Renombrando a '{new_filename}'.")
        
    try:
        os.rename(source_filepath, dest_filepath)
        logger.info(f"Fichero movido con éxito a: {dest_filepath}")
    except Exception as e:
        logger.error(f"¡FALLO CRÍTICO AL MOVER! No se pudo mover '{source_filepath}' a '{dest_filepath}': {e}")


def process_file(filepath):
    """
    Función centralizada para procesar un fichero ODF.
    Ahora usa safe_move().
    """
    # Damos un pequeño margen
    time.sleep(0.5)
    
    filename = os.path.basename(filepath)
    
    if not os.path.exists(filepath):
        logger.warning(f"Se intentó procesar '{filename}' pero ya no existe.")
        return

    logger.info(f"Procesando fichero: {filename}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        logger.info(f"Enviando '{filename}' al Core Backend...")
        headers = {'Content-Type': 'application/xml'}
        response = requests.post(CORE_BACKEND_URL, 
                                 data=xml_content.encode('utf-8'), 
                                 headers=headers, 
                                 timeout=10)

        # --- ¡CAMBIO IMPORTANTE! ---
        if response.status_code == 200:
            logger.info(f"Backend procesó '{filename}' con éxito. Moviendo a 'procesados'.")
            safe_move(filepath, PROCESADOS_PATH) # Usamos safe_move
        else:
            logger.error(f"Backend falló al procesar '{filename}' (Status: {response.status_code}). Moviendo a 'error'.")
            logger.error(f"Respuesta del Backend: {response.text}")
            safe_move(filepath, ERROR_PATH) # Usamos safe_move

    except requests.exceptions.ConnectionError:
        logger.error(f"No se pudo conectar al Core Backend en {CORE_BACKEND_URL}. ¿Está corriendo?")
        # NO movemos el fichero. Se re-intentará en el próximo escaneo o reinicio.
    
    except Exception as e:
        # Este 'except' ahora solo capturará errores de 'open()', 'read()' o 'requests.post()'
        logger.error(f"Error general procesando '{filename}': {e}")
        safe_move(filepath, ERROR_PATH) # Usamos safe_move


class ODFFileHandler(FileSystemEventHandler):
    """ Manejador de eventos que reacciona a la creación de ficheros. """
    def on_created(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.xml'):
            return
            
        logger.info(f"Fichero nuevo detectado por 'on_created': {event.src_path}")
        process_file(event.src_path)


def process_existing_files():
    """ Escanea el hotfolder al arrancar y procesa ficheros existentes. """
    logger.info(f"Escaneando ficheros existentes en: {HOTFOLDER_PATH}")
    found_files = 0
    for filename in os.listdir(HOTFOLDER_PATH):
        if filename.endswith('.xml'):
            found_files += 1
            filepath = os.path.join(HOTFOLDER_PATH, filename)
            process_file(filepath)
    
    if found_files == 0:
        logger.info("No se encontraron ficheros existentes. Esperando nuevos...")


def start_monitoring():
    os.makedirs(PROCESADOS_PATH, exist_ok=True)
    os.makedirs(ERROR_PATH, exist_ok=True)
    
    logger.info(f"Iniciando monitor... (Enviando datos a: {CORE_BACKEND_URL})")

    # 1. Procesamos los ficheros que ya existan
    process_existing_files()
    
    # 2. Iniciamos el observador para ficheros nuevos
    logger.info("El vigilante está activo. Esperando ficheros ODF nuevos...")
    event_handler = ODFFileHandler()
    observer = Observer()
    observer.schedule(event_handler, HOTFOLDER_PATH, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Monitor detenido por el usuario.")
    observer.join()

if __name__ == "__main__":
    start_monitoring()