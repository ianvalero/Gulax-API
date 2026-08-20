from sqlmodel import create_engine, Session

from app.config.settings import settings

engine = create_engine(settings.postgres.postgres_url, echo=settings.sql_log, pool_pre_ping=True)

def get_session():
    with Session(engine) as session:
        yield session