
"""
CivicTrack complaint model.
SQLite data access and employee workflow operations.
"""

import sqlite3
from uuid import uuid4

from core.database import get_connection


DEPARTMENT_BY_CATEGORY = {
    "Road Damage": "Public Works",
    "Streetlight": "Electrical",
    "Water Leakage": "Water Supply",
    "Drainage": "Drainage",
    "Garbage": "Sanitation",
    "Other": "General Services",
}

def get_public_status(complaint):

    if complaint["review_status"] == "Rejected":
        return "Rejected"

    if complaint["status"] == "Resolved":
        return "Resolved"

    if complaint["status"] == "In Progress":
        return "In Progress"

    if complaint["review_status"] == "Approved":
        return "Approved"

    return "Pending Review"


def create_complaint(data):

    reference = f"CT-{uuid4().hex[:12].upper()}"

    department = DEPARTMENT_BY_CATEGORY.get(
        data["category"],
        "General Services",
    )

    with get_connection() as connection:

        cursor = connection.execute("""
            INSERT INTO complaints (
                reference,
                title,
                category,
                location,
                description,
                department
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            reference,
            data["title"],
            data["category"],
            data["location"],
            data["description"],
            department,
        ))

        row = connection.execute(
            "SELECT * FROM complaints WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return dict(row)




def get_all_complaints():

    with get_connection() as connection:

        rows = connection.execute("""
            SELECT *
            FROM complaints
            ORDER BY id DESC
        """).fetchall()

        results = []

        for row in rows:

            complaint = dict(row)

            complaint["status"] = get_public_status(
                complaint
            )

            results.append(complaint)

        return results



def get_complaint_statistics():

    with get_connection() as connection:

        row = connection.execute("""
            SELECT
                COUNT(*) AS total,

                SUM(
                    CASE WHEN review_status = 'Pending Review'
                    THEN 1 ELSE 0 END
                ) AS pending,

                SUM(
                    CASE WHEN status = 'Resolved'
                    THEN 1 ELSE 0 END
                ) AS resolved

            FROM complaints
        """).fetchone()

        return {
            "total": row["total"],
            "pending": row["pending"] or 0,
            "resolved": row["resolved"] or 0,
        }



def get_employee_dashboard(department):

    with get_connection() as connection:

        if department == "ALL":

            rows = connection.execute("""
                SELECT *
                FROM complaints
                ORDER BY id DESC
            """).fetchall()

            statistics = connection.execute("""
                SELECT
                    COUNT(*) AS total,

                    SUM(CASE
                        WHEN review_status = 'Pending Review'
                        THEN 1 ELSE 0 END
                    ) AS pending,

                    SUM(CASE
                        WHEN review_status = 'Approved'
                        THEN 1 ELSE 0 END
                    ) AS approved,

                    SUM(CASE
                        WHEN review_status = 'Rejected'
                        THEN 1 ELSE 0 END
                    ) AS rejected,

                    SUM(CASE
                        WHEN status = 'In Progress'
                        THEN 1 ELSE 0 END
                    ) AS in_progress,

                    SUM(CASE
                        WHEN status = 'Resolved'
                        THEN 1 ELSE 0 END
                    ) AS resolved

                FROM complaints
            """).fetchone()

        else:

            rows = connection.execute("""
                SELECT *
                FROM complaints
                WHERE department = ?
                ORDER BY id DESC
            """, (department,)).fetchall()

            statistics = connection.execute("""
                SELECT
                    COUNT(*) AS total,

                    SUM(CASE
                        WHEN review_status = 'Pending Review'
                        THEN 1 ELSE 0 END
                    ) AS pending,

                    SUM(CASE
                        WHEN review_status = 'Approved'
                        THEN 1 ELSE 0 END
                    ) AS approved,

                    SUM(CASE
                        WHEN review_status = 'Rejected'
                        THEN 1 ELSE 0 END
                    ) AS rejected,

                    SUM(CASE
                        WHEN status = 'In Progress'
                        THEN 1 ELSE 0 END
                    ) AS in_progress,

                    SUM(CASE
                        WHEN status = 'Resolved'
                        THEN 1 ELSE 0 END
                    ) AS resolved

                FROM complaints
                WHERE department = ?
            """, (department,)).fetchone()

        return {
            "complaints": [dict(row) for row in rows],
            "statistics": {
                key: statistics[key] or 0
                for key in (
                    "total",
                    "pending",
                    "approved",
                    "rejected",
                    "in_progress",
                    "resolved",
                )
            },
        }


def get_complaint_updates(complaint_id, department):

    with get_connection() as connection:

        if department == "ALL":

            complaint = connection.execute("""
                SELECT id
                FROM complaints
                WHERE id = ?
            """, (complaint_id,)).fetchone()

        else:

            complaint = connection.execute("""
                SELECT id
                FROM complaints
                WHERE id = ? AND department = ?
            """, (complaint_id, department)).fetchone()

        if complaint is None:
            raise LookupError("Complaint not found.")

        rows = connection.execute("""
            SELECT
                actor_name,
                action,
                message,
                previous_status,
                new_status,
                created_at

            FROM complaint_updates

            WHERE complaint_id = ?

            ORDER BY id ASC
        """, (complaint_id,)).fetchall()

        return [dict(row) for row in rows]


def get_public_complaint_tracking(reference):

    with get_connection() as connection:

        row = connection.execute("""
            SELECT
                id,
                reference,
                title,
                category,
                location,
                description,
                status,
                review_status,
                department,
                rejection_reason,
                resolution_note,
                created_at,
                updated_at

            FROM complaints

            WHERE reference = ?
        """, (reference,)).fetchone()

        if row is None:
            return None

        complaint = dict(row)

        # Calculate the status displayed to citizens.
        complaint["status"] = get_public_status(complaint)

        updates = connection.execute("""
            SELECT
                actor_name,
                action,
                message,
                previous_status,
                new_status,
                created_at

            FROM complaint_updates

            WHERE complaint_id = ?

            ORDER BY id ASC
        """, (complaint["id"],)).fetchall()

        return {
            "complaint": complaint,
            "updates": [dict(update) for update in updates],
        }


def perform_employee_action(
    complaint_id,
    action,
    employee_name,
    department,
    message="",
):

    with get_connection() as connection:

        complaint = connection.execute("""
            SELECT *
            FROM complaints
            WHERE id = ?
        """, (complaint_id,)).fetchone()

        if complaint is None:
            raise LookupError("Complaint not found.")

      
        if department != "ALL" and complaint["department"] != department:
            raise PermissionError(
                "This complaint belongs to another department."
            )
 

        review = complaint["review_status"]
        work_status = complaint["status"]
        assigned = complaint["assigned_employee"]

        message = message.strip()

        if action == "approve":

            if review != "Pending Review":
                raise ValueError("Complaint is not awaiting review.")

            connection.execute("""
                UPDATE complaints
                SET review_status = 'Approved',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (complaint_id,))

            message = "Complaint approved for action."

        elif action == "reject":

            if review != "Pending Review":
                raise ValueError("Complaint is not awaiting review.")

            if not message:
                raise ValueError("A rejection reason is required.")

            connection.execute("""
                UPDATE complaints
                SET review_status = 'Rejected',
                    rejection_reason = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (message, complaint_id))

        elif action == "take":

            if review != "Approved":
                raise ValueError("Approve the complaint before taking it.")

            if assigned:
                raise ValueError("Complaint is already assigned.")

            connection.execute("""
                UPDATE complaints
                SET assigned_employee = ?,
                    status = 'In Progress',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (employee_name, complaint_id))

            message = "Employee accepted responsibility for this complaint."

        elif action == "update":

            if work_status != "In Progress":
                raise ValueError("Complaint is not in progress.")

            if assigned != employee_name:
                raise PermissionError("This complaint is not assigned to you.")

            if not message:
                raise ValueError("Enter a progress update.")

            connection.execute("""
                UPDATE complaints
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (complaint_id,))

        elif action == "resolve":

            if work_status != "In Progress":
                raise ValueError("Complaint must be in progress first.")

            if assigned != employee_name:
                raise PermissionError("This complaint is not assigned to you.")

            if not message:
                raise ValueError("A resolution report is required.")

            connection.execute("""
                UPDATE complaints
                SET status = 'Resolved',
                    resolution_note = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (message, complaint_id))

        else:
            raise ValueError("Unknown employee action.")

        connection.execute("""
            INSERT INTO complaint_updates (
                complaint_id,
                actor_name,
                action,
                message
            )
            VALUES (?, ?, ?, ?)
        """, (
            complaint_id,
            employee_name,
            action,
            message,
        ))

        updated = connection.execute("""
            SELECT *
            FROM complaints
            WHERE id = ?
        """, (complaint_id,)).fetchone()

        return dict(updated)

