
/*
 * CivicTrack Employee Dashboard
 * Reads and manages actual SQLite complaints.
 */

const API = "/api/employee/complaints";

let complaints = [];
let employee = {};

const complaintList = document.querySelector("#complaint-list");
const complaintFilter = document.querySelector("#complaint-filter");
const messageBox = document.querySelector("#dashboard-message");


function effectiveStatus(complaint) {

    if (complaint.review_status === "Rejected") {
        return "Rejected";
    }

    if (complaint.status === "Resolved") {
        return "Resolved";
    }

    if (complaint.status === "In Progress") {
        return "In Progress";
    }

    if (complaint.review_status === "Approved") {
        return "Approved";
    }

    return "Pending Review";
}


function makeElement(tag, className, text) {

    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== undefined) {
        element.textContent = text;
    }

    return element;
}


function makeButton(label, action, id, style) {

    const button = makeElement(
        "button",
        `action-button ${style}`,
        label
    );

    button.type = "button";
    button.dataset.action = action;
    button.dataset.id = id;

    return button;
}


function updateStatistics(data) {

    document.querySelector("#pending-count").textContent =
        data.pending;

    document.querySelector("#approved-count").textContent =
        data.approved;

    document.querySelector("#progress-count").textContent =
        data.in_progress;

    document.querySelector("#resolved-count").textContent =
        data.resolved;

}


function createComplaintCard(complaint) {

    const card = makeElement("article", "complaint-card");

    const statusName = effectiveStatus(complaint);

    const top = makeElement("div", "complaint-top");

    const heading = makeElement("div");

    heading.appendChild(
        makeElement(
            "span",
            "complaint-reference",
            complaint.reference
        )
    );

    heading.appendChild(
        makeElement("h3", "", complaint.title)
    );

    const badgeClass = statusName
        .toLowerCase()
        .replaceAll(" ", "-");

    const badge = makeElement(
        "span",
        `employee-status ${badgeClass}`,
        statusName
    );

    top.append(heading, badge);

    card.appendChild(top);


    card.appendChild(
        makeElement(
            "p",
            "complaint-description",
            complaint.description
        )
    );


    const meta = makeElement("div", "complaint-meta");

    meta.appendChild(
        makeElement("span", "", `Category: ${complaint.category}`)
    );

    meta.appendChild(
        makeElement("span", "", `Location: ${complaint.location}`)
    );

    meta.appendChild(
        makeElement("span", "", `Department: ${complaint.department}`)
    );

    if (complaint.assigned_employee) {
        meta.appendChild(
            makeElement(
                "span",
                "",
                `Assigned to: ${complaint.assigned_employee}`
            )
        );
    }

    card.appendChild(meta);


    const actions = makeElement("div", "complaint-actions");

    if (complaint.review_status === "Pending Review") {

        actions.append(
            makeButton(
                "Approve Complaint",
                "approve",
                complaint.id,
                "approve-button"
            ),
            makeButton(
                "Reject Complaint",
                "reject",
                complaint.id,
                "reject-button"
            )
        );

    } else if (
        complaint.review_status === "Approved" &&
        complaint.status === "Pending"
    ) {

        actions.appendChild(
            makeButton(
                "Take Responsibility",
                "take",
                complaint.id,
                "take-button"
            )
        );

    } else if (
        complaint.status === "In Progress" &&
        complaint.assigned_employee === employee.name
    ) {

        actions.append(
            makeButton(
                "Add Progress Update",
                "update",
                complaint.id,
                "update-button"
            ),
            makeButton(
                "Mark Resolved",
                "resolve",
                complaint.id,
                "resolve-button"
            )
        );

    }

    actions.appendChild(
        makeButton(
            "View History",
            "history",
            complaint.id,
            "history-button"
        )
    );

    card.appendChild(actions);

    return card;
}


function renderComplaints() {

    complaintList.replaceChildren();

    const filter = complaintFilter.value;

    const filtered = complaints.filter(complaint => {

        return (
            filter === "All" ||
            effectiveStatus(complaint) === filter
        );

    });

    if (filtered.length === 0) {

        complaintList.appendChild(
            makeElement(
                "div",
                "empty-state",
                "No complaints found in this category."
            )
        );

        return;
    }

    for (const complaint of filtered) {
        complaintList.appendChild(
            createComplaintCard(complaint)
        );
    }
}


async function loadDashboard() {

    messageBox.textContent = "Loading employee dashboard...";

    try {

        const response = await fetch(API, {
            cache: "no-store"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Dashboard request failed.");
        }

        complaints = data.complaints;
        employee = data.employee;

        document.querySelector("#employee-name").textContent =
            employee.name;

        document.querySelector("#employee-department").textContent =
            employee.department;

        updateStatistics(data.statistics);

        renderComplaints();

        messageBox.textContent =
            `${complaints.length} complaints found for your department.`;

    } catch (error) {

        console.error(error);

        messageBox.textContent = error.message;

        complaintList.replaceChildren(
            makeElement(
                "div",
                "empty-state",
                "Unable to load complaints. Check the CivicTrack server."
            )
        );

    }
}


async function performAction(id, action, message = "") {

    const response = await fetch(
        `${API}/${id}/action`,
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                action,
                message
            })
        }
    );

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || "Action failed.");
    }

    await loadDashboard();
}


async function showHistory(id, card) {

    const response = await fetch(
        `${API}/${id}/updates`,
        { cache: "no-store" }
    );

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || "Could not load history.");
    }

    const history = makeElement(
        "div",
        "complaint-history"
    );

    history.appendChild(
        makeElement("h4", "", "Complaint Activity History")
    );

    if (result.updates.length === 0) {

        history.appendChild(
            makeElement("p", "", "No updates recorded yet.")
        );

    }

    for (const item of result.updates) {

        const entry = makeElement(
            "div",
            "history-entry"
        );

        entry.appendChild(
            makeElement(
                "strong",
                "",
                `${item.action.toUpperCase()} · ${item.actor_name}`
            )
        );

        entry.appendChild(
            makeElement("p", "", item.message)
        );

        entry.appendChild(
            makeElement("time", "", item.created_at)
        );

        history.appendChild(entry);

    }

    card.appendChild(history);
}


complaintList.addEventListener("click", async event => {

    const button = event.target.closest("button[data-action]");

    if (!button || button.disabled) {
        return;
    }

    const { action, id } = button.dataset;

    if (action === "history") {

        const card = button.closest(".complaint-card");

        try {
            button.disabled = true;
            await showHistory(id, card);
        } catch (error) {
            messageBox.textContent = error.message;
        } finally {
            button.disabled = false;
        }

        return;
    }


    let message = "";

    if (action === "reject") {

        message = prompt(
            "Enter the reason for rejecting this complaint:"
        );

        if (message === null || !message.trim()) {
            return;
        }

    } else if (action === "update") {

        message = prompt(
            "Describe the progress made on this complaint:"
        );

        if (message === null || !message.trim()) {
            return;
        }

    } else if (action === "resolve") {

        message = prompt(
            "Describe how the civic issue was resolved:"
        );

        if (message === null || !message.trim()) {
            return;
        }

        if (!confirm("Confirm that this complaint is resolved?")) {
            return;
        }

    } else if (action === "approve") {

        if (!confirm("Approve this complaint for action?")) {
            return;
        }

    } else if (action === "take") {

        if (!confirm("Take responsibility for this complaint?")) {
            return;
        }

    }


    button.disabled = true;
    messageBox.textContent = "Processing employee action...";

    try {

        await performAction(id, action, message);

        messageBox.textContent =
            "Complaint successfully updated.";

    } catch (error) {

        messageBox.textContent = error.message;

    } finally {

        button.disabled = false;

    }

});


complaintFilter.addEventListener(
    "change",
    renderComplaints
);

document.querySelector("#refresh-button").addEventListener(
    "click",
    loadDashboard
);


loadDashboard();


