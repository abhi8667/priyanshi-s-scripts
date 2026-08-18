from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.engine import Engine
from config import DATABASE_URL, DB_PATH
import os

class Base(DeclarativeBase):
    pass

# Ensure directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Render / PostgreSQL compatibility fix (postgres:// -> postgresql://)
db_url = DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode, Foreign Keys, and optimal SQLite PRAGMAs for performance."""
    if engine.url.drivername.startswith("sqlite"):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA cache_size=-64000;")  # 64MB cache
            cursor.close()
        except Exception:
            pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    """Context-friendly database session factory."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def init_db():
    """Creates all database tables defined in models and applies schema migrations."""
    from database.models import Student, Department, Program, Venue, TimeSlot, ImportHistory, BackupHistory, AuditLog, AppSettings, StudentEventAllocation
    Base.metadata.create_all(bind=engine)

    # Auto-migration for SQLite: ensure import_history_id exists on students table
    if engine.url.drivername.startswith("sqlite"):
        with engine.connect() as conn:
            cursor = conn.exec_driver_sql("PRAGMA table_info(students)")
            columns = [row[1] for row in cursor.fetchall()]
            if "import_history_id" not in columns:
                conn.exec_driver_sql("ALTER TABLE students ADD COLUMN import_history_id INTEGER REFERENCES import_history(id)")
                conn.commit()

