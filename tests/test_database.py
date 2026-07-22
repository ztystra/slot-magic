"""Database schema migration tests."""

import sqlite3

from database import Database


def test_legacy_slot_constraint_is_migrated(tmp_path):
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.executescript("""
        CREATE TABLE services (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            duration_minutes INTEGER NOT NULL,
            price FLOAT NOT NULL,
            description TEXT
        );
        CREATE TABLE bookings (
            id VARCHAR(200) PRIMARY KEY,
            service_id VARCHAR(50) NOT NULL,
            date VARCHAR(10) NOT NULL,
            time VARCHAR(5) NOT NULL,
            client_name VARCHAR(200) NOT NULL,
            client_phone VARCHAR(50) NOT NULL,
            client_telegram_id INTEGER NOT NULL,
            status VARCHAR(20),
            created_at DATETIME,
            reminder_sent_24h BOOLEAN,
            reminder_sent_2h BOOLEAN,
            CONSTRAINT uq_slot UNIQUE (date, time, service_id),
            FOREIGN KEY(service_id) REFERENCES services (id)
        );
        """)
    connection.close()

    Database(str(db_path))

    connection = sqlite3.connect(db_path)
    table_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='bookings'"
    ).fetchone()[0]
    indexes = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='bookings'"
    ).fetchall()
    connection.close()

    assert "uq_slot" not in table_sql
    assert any(
        sql and "UNIQUE" in sql and "WHERE status = 'confirmed'" in sql
        for (sql,) in indexes
    )
