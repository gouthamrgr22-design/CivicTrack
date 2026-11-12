
"""
CivicTrack database infrastructure and migrations.

Features:
- Citizen account management
- Secure session storage
- Complaint ownership
- Complaint history and status tracking
- Automatic database migrations
"""

import sqlite3

from contextlib import contextmanager
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = PROJECT_ROOT / "data" / "civictrack.db"


# ==========================================
# DATABASE CONNECTION
# ==========================================

@contextmanager
def get_connection():

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=10,
    )

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    try:
        yield connection
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def initialize_database():

    with get_connection() as connection:

        # ==========================================
        # CITIZEN ACCOUNTS
        # ==========================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                full_name TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE COLLATE NOCASE,

                password_hash TEXT NOT NULL,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

            )
        """)

        # ==========================================
        # AUTHENTICATION SESSIONS
        # ==========================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                token_hash TEXT NOT NULL UNIQUE,

                expires_at TEXT NOT NULL,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE

            )
        """)

        # ==========================================
        # COMPLAINTS
        # ==========================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS complaints (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                reference TEXT NOT NULL UNIQUE,

                title TEXT NOT NULL,

                category TEXT NOT NULL,

                location TEXT NOT NULL,

                description TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'Pending'
                    CHECK(status IN (
                        'Pending',
                        'In Progress',
                        'Resolved'
                    )),

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

            )
        """)

        # ==========================================
        # COMPLAINT TABLE MIGRATIONS
        # ==========================================

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(complaints)"
            ).fetchall()
        }

        # Associate complaints with registered citizens.
        # Existing complaints remain unassigned.

        if "user_id" not in existing_columns:

            connection.execute("""
                ALTER TABLE complaints
                ADD COLUMN user_id INTEGER
                REFERENCES users(id)
                ON DELETE SET NULL
            """)

        new_columns = {

            "review_status": "TEXT NOT NULL DEFAULT 'Pending Review'",

            "department": "TEXT NOT NULL DEFAULT 'General Services'",

            "assigned_employee": "TEXT",

            "rejection_reason": "TEXT",

            "resolution_note": "TEXT",

            "updated_at": "TEXT",

        }

        for name, definition in new_columns.items():

            if name not in existing_columns:

                connection.execute(
                    f"ALTER TABLE complaints ADD COLUMN "
                    f"{name} {definition}"
                )

        # ==========================================
        # AUTOMATIC DEPARTMENT ROUTING
        # ==========================================

        connection.execute("""
            UPDATE complaints

            SET department = CASE category

                WHEN 'Road Damage' THEN 'Public Works'

                WHEN 'Streetlight' THEN 'Electrical'

                WHEN 'Water Leakage' THEN 'Water Supply'

                WHEN 'Drainage' THEN 'Drainage'

                WHEN 'Garbage' THEN 'Sanitation'

                ELSE 'General Services'

            END

            WHERE department = 'General Services'
        """)

        # ==========================================
        # COMPLAINT TIMESTAMPS
        # ==========================================

        connection.execute("""
            UPDATE complaints

            SET updated_at = COALESCE(updated_at, created_at)
        """)

        # ==========================================
        # COMPLAINT HISTORY
        # ==========================================

        connection.execute("""
            CREATE TABLE IF NOT EXISTS complaint_updates (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                complaint_id INTEGER NOT NULL,

                actor_name TEXT NOT NULL,

                action TEXT NOT NULL,

                message TEXT NOT NULL,

                previous_status TEXT,

                new_status TEXT,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (complaint_id)
                    REFERENCES complaints(id)
                    ON DELETE CASCADE

            )
        """)

        # ==========================================
        # HISTORY TABLE MIGRATIONS
        # ==========================================

        history_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(complaint_updates)"
            ).fetchall()
        }

        if "previous_status" not in history_columns:

            connection.execute("""
                ALTER TABLE complaint_updates
                ADD COLUMN previous_status TEXT
            """)

        if "new_status" not in history_columns:

            connection.execute("""
                ALTER TABLE complaint_updates
                ADD COLUMN new_status TEXT
            """)

        # ==========================================
        # RECOVER OLD STATUS TRANSITIONS
        # ==========================================

        connection.execute("""
            UPDATE complaint_updates

            SET previous_status = CASE action

                WHEN 'approve' THEN 'Pending Review'

                WHEN 'reject' THEN 'Pending Review'

                WHEN 'take' THEN 'Approved'

                WHEN 'update' THEN 'In Progress'

                WHEN 'resolve' THEN 'In Progress'

                ELSE previous_status

            END

            WHERE previous_status IS NULL
        """)

        connection.execute("""
            UPDATE complaint_updates

            SET new_status = CASE action

                WHEN 'approve' THEN 'Approved'

                WHEN 'reject' THEN 'Rejected'

                WHEN 'take' THEN 'In Progress'

                WHEN 'update' THEN 'In Progress'

                WHEN 'resolve' THEN 'Resolved'

                ELSE new_status

            END

            WHERE new_status IS NULL
        """)

        # ==========================================
        # BACKFILL OLD COMPLAINT SUBMISSIONS
        # ==========================================

        connection.execute("""
            INSERT INTO complaint_updates (

                complaint_id,

                actor_name,

                action,

                message,

                previous_status,

                new_status,

                created_at

            )

            SELECT

                c.id,

                'Citizen',

                'submitted',

                'Complaint submitted and routed to '
                    || c.department || '.',

                NULL,

                'Pending Review',

                c.created_at

            FROM complaints AS c

            WHERE NOT EXISTS (

                SELECT 1

                FROM complaint_updates AS u

                WHERE u.complaint_id = c.id

                  AND u.action = 'submitted'

            )
        """)

        # ==========================================
        # DATABASE INDEXES
        # ==========================================

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaints_user

            ON complaints(user_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user

            ON user_sessions(user_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaint_review

            ON complaints(review_status, department)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaint_updates

            ON complaint_updates(complaint_id, created_at)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_expiry

            ON user_sessions(expires_at)
        """)


# ==========================================
# DIRECT EXECUTION
# ==========================================

if __name__ == "__main__":

    initialize_database()

    print("CivicTrack database initialized successfully.")

    print(f"Database: {DATABASE_PATH}")

