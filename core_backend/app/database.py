import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


def _load_env_file(dotenv_path: str) -> None:
    """Load .env handling legacy encodings gracefully."""
    if not os.path.exists(dotenv_path):
        logger.warning(".env file not found at %s", dotenv_path)
        return

    encodings_to_try = ("utf-8", "latin-1", None)
    for encoding in encodings_to_try:
        try:
            load_dotenv(dotenv_path=dotenv_path, encoding=encoding)
            return
        except UnicodeDecodeError:
            if encoding is None:
                raise
            logger.warning(
                "Failed loading .env with %s encoding, trying next fallback...",
                encoding,
            )


# Load environment variables from .env file located in the parent directory
# The .env file is in 'core_backend', and this script is in 'core_backend/app'
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
_load_env_file(dotenv_path)

# Get database credentials from environment variables
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# Construct the database URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?client_encoding=utf8"

# --- SQLAlchemy Engine Setup ---
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# --- DB Session Dependency ---
def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
