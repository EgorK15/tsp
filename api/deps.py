from db.database import SessionLocal


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
