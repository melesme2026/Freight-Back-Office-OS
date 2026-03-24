from app.core.database import SessionLocal
from app.core.seed_loader import run_all_seeds


def main():
    db = SessionLocal()
    try:
        run_all_seeds(db)
        print("✅ Seeding complete")
    finally:
        db.close()


if __name__ == "__main__":
    main()