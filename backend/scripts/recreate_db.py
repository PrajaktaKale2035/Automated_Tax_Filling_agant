"""Drop and recreate all tables from current SQLAlchemy models.

DEV ONLY. Destroys data. No production safeguard.
Usage: python -m scripts.recreate_db    (run from backend/ directory)
"""
import sys
from app.database import Base, engine
from app import models  # noqa: F401  -- ensures all models are registered


def main() -> None:
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables from current models...")
    Base.metadata.create_all(bind=engine)
    print("Done.")
    print("Tables now defined:")
    for table_name in sorted(Base.metadata.tables.keys()):
        print(f"  - {table_name}")


if __name__ == "__main__":
    if "--force" in sys.argv:
        main()
    else:
        confirm = input("This will DROP ALL DATA. Type 'yes' to continue: ")
        if confirm != "yes":
            print("Aborted.")
            sys.exit(1)
        main()
