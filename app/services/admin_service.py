"""
CivicTrack V3 — Administrator Service

Handles administrator dashboard data and employee approvals.
"""

from core.database import get_connection


def get_admin_overview():
    """Return employee and complaint information for administrators."""

    with get_connection() as connection:

        employee_stats = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(
                    CASE WHEN account_status = 'pending_approval'
                    THEN 1 ELSE 0 END
                ), 0) AS pending,
                COALESCE(SUM(
                    CASE WHEN account_status = 'active'
                    THEN 1 ELSE 0 END
                ), 0) AS active,
                COALESCE(SUM(
                    CASE WHEN account_status = 'rejected'
                    THEN 1 ELSE 0 END
                ), 0) AS rejected
            FROM users
            WHERE role = 'employee'
            """
        ).fetchone()

        employees = connection.execute(
            """
            SELECT
                id,
                full_name,
                username,
                email,
                department,
                account_status,
                email_verified,
                created_at
            FROM users
            WHERE role = 'employee'
            ORDER BY
                CASE account_status
                    WHEN 'pending_approval' THEN 0
                    ELSE 1
                END,
                created_at DESC
            """
        ).fetchall()

        complaint_stats = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(
                    CASE WHEN review_status = 'Pending Review'
                    THEN 1 ELSE 0 END
                ), 0) AS pending_review,
                COALESCE(SUM(
                    CASE WHEN review_status = 'Approved'
                    THEN 1 ELSE 0 END
                ), 0) AS approved,
                COALESCE(SUM(
                    CASE WHEN review_status = 'Rejected'
                    THEN 1 ELSE 0 END
                ), 0) AS rejected,
                COALESCE(SUM(
                    CASE WHEN status = 'In Progress'
                    THEN 1 ELSE 0 END
                ), 0) AS in_progress,
                COALESCE(SUM(
                    CASE WHEN status = 'Resolved'
                    THEN 1 ELSE 0 END
                ), 0) AS resolved
            FROM complaints
            """
        ).fetchone()

        recent_complaints = connection.execute(
            """
            SELECT
                id,
                reference,
                title,
                category,
                location,
                status,
                review_status,
                department,
                assigned_employee,
                created_at
            FROM complaints
            ORDER BY created_at DESC, id DESC
            LIMIT 10
            """
        ).fetchall()

        return {
            "employees": [dict(row) for row in employees],
            "employee_statistics": dict(employee_stats),
            "complaint_statistics": dict(complaint_stats),
            "recent_complaints": [
                dict(row) for row in recent_complaints
            ],
        }


def decide_employee_account(employee_id, action):
    """Approve or reject an employee awaiting administrator review."""

    if not isinstance(employee_id, int) or employee_id <= 0:
        raise ValueError("Invalid employee ID.")

    if action not in ("approve", "reject"):
        raise ValueError("Action must be approve or reject.")

    new_status = (
        "active" if action == "approve" else "rejected"
    )

    with get_connection() as connection:

        connection.execute("BEGIN IMMEDIATE")

        employee = connection.execute(
            """
            SELECT id, role, account_status
            FROM users
            WHERE id = ?
            """,
            (employee_id,),
        ).fetchone()

        if employee is None or employee["role"] != "employee":
            raise LookupError("Employee account not found.")

        if employee["account_status"] != "pending_approval":
            raise ValueError(
                "This employee account is no longer awaiting approval."
            )

        result = connection.execute(
            """
            UPDATE users
            SET account_status = ?
            WHERE id = ?
              AND role = 'employee'
              AND account_status = 'pending_approval'
            """,
            (new_status, employee_id),
        )

        if result.rowcount != 1:
            raise ValueError("Employee account could not be updated.")

    return {
        "employee_id": employee_id,
        "account_status": new_status,
    }
