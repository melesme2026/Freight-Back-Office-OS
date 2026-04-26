from app.core.config import get_settings
from app.core.database import get_session_factory, init_db
from app.core.seed_loader import run_all_seeds


def main() -> None:
    init_db(import_models=True)

    session_factory = get_session_factory()
    db = session_factory()
    try:
        settings = get_settings()
        results = run_all_seeds(db)
        print(f"✅ Seeding complete (mode={settings.seed_mode})")
        print(results)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
