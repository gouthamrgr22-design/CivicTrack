
"""
CivicTrack complaint service.
Validation and employee workflow rules.
"""

from models.complaint import (
    create_complaint,
    get_all_complaints,
    get_complaint_statistics,
    get_employee_dashboard,
    get_complaint_updates,
    perform_employee_action,
)

from models.complaint import (
    create_complaint,
    get_all_complaints,
    get_complaint_statistics,
    get_employee_dashboard,
    get_complaint_updates,
    perform_employee_action,
    get_public_complaint_tracking,
)

ALLOWED_CATEGORIES = {
    "Road Damage",
    "Streetlight",
    "Water Leakage",
    "Drainage",
    "Garbage",
    "Other",
}


def validate_text(data, field, max_length):

    value = data.get(field)

    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")

    value = value.strip()

    if not value:
        raise ValueError(f"{field} is required.")

    if len(value) > max_length:
        raise ValueError(
            f"{field} must not exceed {max_length} characters."
        )

    return value


def submit_complaint(data):

    if not isinstance(data, dict):
        raise ValueError("Invalid complaint data.")

    title = validate_text(data, "title", 80)
    category = validate_text(data, "category", 40)
    location = validate_text(data, "location", 120)
    description = validate_text(data, "description", 1000)

    if category not in ALLOWED_CATEGORIES:
        raise ValueError("Invalid complaint category.")

    return create_complaint({
        "title": title,
        "category": category,
        "location": location,
        "description": description,
    })


def list_complaints():
    return get_all_complaints()


def get_dashboard_statistics():
    return get_complaint_statistics()


def get_employee_data(department):
    return get_employee_dashboard(department)


def get_employee_history(complaint_id, department):
    return get_complaint_updates(complaint_id, department)


def employee_action(
    complaint_id,
    action,
    employee_name,
    department,
    message="",
):

    if not isinstance(message, str):
        raise ValueError("Message must be text.")

    if len(message) > 1000:
        raise ValueError("Message must not exceed 1000 characters.")

    return perform_employee_action(
        complaint_id,
        action,
        employee_name,
        department,
        message,
    )


def get_public_tracking(reference):

    return get_public_complaint_tracking(reference)

