"""One-off, additive SQLite migration for the customer-experience improvement
pass. db.create_all() only creates tables that don't exist yet — it never
ALTERs an existing table — so new columns added to models must be added by
hand here. Safe to re-run: every column add is guarded by a existence check.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "nearcart.db")

COLUMNS = {
    "reservations": [
        ("unit_price_snapshot", "FLOAT"),
        ("payment_method", "VARCHAR(20) DEFAULT 'PAY_AT_SHOP'"),
        ("payment_status", "VARCHAR(20) DEFAULT 'NOT_APPLICABLE'"),
        ("receipt_number", "VARCHAR(30)"),
    ],
}


def existing_columns(cursor, table):
    cursor.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for table, columns in COLUMNS.items():
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        if not cursor.fetchone():
            print(f"skip {table}: table does not exist yet (will be created by db.create_all())")
            continue
        current = existing_columns(cursor, table)
        for name, coltype in columns:
            if name in current:
                continue
            print(f"ALTER TABLE {table} ADD COLUMN {name} {coltype}")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {coltype}")
    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    main()
