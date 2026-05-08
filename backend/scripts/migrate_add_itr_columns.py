"""Add ITR form-type and capital-gains / income columns to itr1_filings.

Run once after pulling this change:
    python -m scripts.migrate_add_itr_columns
"""
from sqlalchemy import text
from app.database import engine

COLUMNS = [
    ("form_type",                    "VARCHAR(10) DEFAULT 'ITR-1' NOT NULL"),
    ("capital_gains_stcg_equity",    "FLOAT DEFAULT 0.0"),
    ("capital_gains_ltcg_equity",    "FLOAT DEFAULT 0.0"),
    ("capital_gains_stcg_tax",       "FLOAT DEFAULT 0.0"),
    ("capital_gains_ltcg_tax",       "FLOAT DEFAULT 0.0"),
    ("house_property_income",        "FLOAT DEFAULT 0.0"),
    ("business_income",              "FLOAT DEFAULT 0.0"),
]

def run():
    with engine.connect() as conn:
        for col, definition in COLUMNS:
            conn.execute(text(
                f"ALTER TABLE itr1_filings ADD COLUMN IF NOT EXISTS {col} {definition}"
            ))
            print(f"  OK {col}")
        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    run()
