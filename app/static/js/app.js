
/*
 * CivicTrack v2
 * Citizen portal: SQLite complaints and tracking timeline.
 */

let complaints = [];

const complaintForm = document.querySelector("#complaint-form");
const complaintList = document.querySelector("#complaint-list");
const statusFilter = document.querySelector("#status-filter");
const formMessage = document.querySelector("#form-message");


// ==========================================
// SAFE HTML ELEMENT CREATION
// ==========================================

function createElement(tag, className = "", text = "") {

    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    element.textContent = text;

    return element;
}


// ==========================================
// DASHBOARD STATISTICS
// ==========================================

function updateStatistics(statistics) {

    document.querySelector("#total-count").textContent =
        statistics.total;

    document.querySelector("#pending-count").textContent =
        statistics.pending;

    document.querySelector("#resolved-count").textContent =
        statistics.resolved;

}


// ==========================================
// STATUS DISPLAY
// ==========================================

function getStatusClass(status) {

    return status.toLowerCase().replaceAll(" ", "-");

}


// ==========================================
// COMPLAINT TABLE
// ==========================================

function renderComplaints() {

    complaintList.replaceChildren();

    const selectedStatus = statusFilter.value;

    const filtered = complaints.filter(complaint => {

        return (
            selectedStatus === "All" ||
            complaint.status === selectedStatus
        );

    });


    if (filtered.length === 0) {

        const row = document.createElement("tr");

        const cell = createElement(
            "td",
            "empty-row",
            "No complaints found."
        );

        cell.colSpan = 6;

        row.appendChild(cell);
        complaintList.appendChild(row);

        return;

    }


    for (const complaint of filtered) {

        // Main complaint row.

        const row = document.createElement("tr");

        row.append(
            createElement("td", "", complaint.reference),
            createElement("td", "", complaint.title),
            createElement("td", "", complaint.category),
            createElement("td", "", complaint.location)
        );


        // Status cell.

        const statusCell = document.createElement("td");

        const status = createElement(
            "span",
            `status ${getStatusClass(complaint.status)}`,
            complaint.status
        );

        statusCell.appendChild(status);

        row.appendChild(statusCell);


        // Tracking button.

        const trackingCell = document.createElement("td");

        const trackingButton = createElement(
            "button",
            "track-button",
            "View Tracking"
        );

        trackingButton.type = "button";

        trackingButton.dataset.reference = complaint.reference;

        trackingCell.appendChild(trackingButton);

        row.appendChild(trackingCell);


        // Expandable tracking row.

        const historyRow = document.createElement("tr");

        historyRow.className = "tracking-row";
        historyRow.hidden = true;

        const historyCell = document.createElement("td");

        historyCell.colSpan = 6;
        historyCell.className = "tracking-cell";

        historyRow.appendChild(historyCell);

        complaintList.append(row, historyRow);

    }

}


// ==========================================
// TRACKING TIMELINE
// ==========================================

function renderTracking(data) {

    const complaint = data.complaint;

    const panel = createElement("div", "tracking-panel");


    // Complaint heading.

    const heading = createElement("div", "tracking-heading");

    const headingText = createElement("div");

    headingText.append(
        createElement(
            "span",
            "tracking-reference",
            complaint.reference
        ),

        createElement(
            "h3",
            "",
            complaint.title
        ),

        createElement(
            "p",
            "tracking-subtitle",
            `${complaint.category} · ${complaint.department}`
        )
    );


    const currentStatus = createElement(
        "span",
        `status ${getStatusClass(complaint.status)}`,
        `Current status: ${complaint.status}`
    );

    heading.append(headingText, currentStatus);

    panel.appendChild(heading);


    // Description.

    panel.appendChild(
        createElement(
            "p",
            "tracking-description",
            complaint.description
        )
    );


    // Rejection reason.

    if (complaint.rejection_reason) {

        panel.appendChild(
            createElement(
                "p",
                "tracking-important",
                `Rejection reason: ${complaint.rejection_reason}`
            )
        );

    }


    // Resolution details.

    if (complaint.resolution_note) {

        panel.appendChild(
            createElement(
                "p",
                "tracking-resolution",
                `Resolution: ${complaint.resolution_note}`
            )
        );

    }


    panel.appendChild(
        createElement(
            "h4",
            "timeline-title",
            "Complaint Activity History"
        )
    );


    const timeline = createElement(
        "div",
        "tracking-timeline"
    );


    if (data.updates.length === 0) {

        timeline.appendChild(
            createElement(
                "p",
                "empty-row",
                "No activity has been recorded yet."
            )
        );

    }


    const actionNames = {
        submitted: "Complaint Submitted",
        approve: "Complaint Approved",
        reject: "Complaint Rejected",
        take: "Employee Took Responsibility",
        update: "Progress Update",
        resolve: "Complaint Resolved"
    };


    // Display oldest event first.

    for (const update of data.updates) {

        const event = createElement(
            "article",
            "timeline-event"
        );


        const eventTop = createElement(
            "div",
            "timeline-event-top"
        );

        eventTop.append(
            createElement(
                "strong",
                "",
                actionNames[update.action] || update.action
            ),

            createElement(
                "time",
                "",
                update.created_at
            )
        );

        event.appendChild(eventTop);


        // Previous status → New status.

        const transition = createElement(
            "div",
            "status-transition"
        );

        transition.append(
            createElement(
                "span",
                "transition-from",
                update.previous_status || "New"
            ),

            createElement(
                "span",
                "transition-arrow",
                "→"
            ),

            createElement(
                "span",
                "transition-to",
                update.new_status || "Pending Review"
            )
        );

        event.appendChild(transition);


        // Employee or citizen message.

        event.appendChild(
            createElement(
                "p",
                "timeline-message",
                update.message
            )
        );


        event.appendChild(
            createElement(
                "small",
                "timeline-actor",
                `Recorded by: ${update.actor_name}`
            )
        );


        timeline.appendChild(event);

    }


    panel.appendChild(timeline);

    return panel;

}


// ==========================================
// FETCH COMPLAINT TRACKING
// ==========================================

async function loadTracking(reference, historyCell) {

    const response = await fetch(
        `/api/complaints/${encodeURIComponent(reference)}/tracking`,
        {
            cache: "no-store"
        }
    );

    const data = await response.json();

    if (!response.ok) {

        throw new Error(
            data.error || "Unable to load complaint history."
        );

    }

    historyCell.replaceChildren(
        renderTracking(data)
    );

}


// ==========================================
// LOAD CITIZEN DASHBOARD
// ==========================================

async function loadDashboard() {

    try {

        const response = await fetch(
            "/api/complaints",
            {
                cache: "no-store"
            }
        );

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.error || "Could not load complaints."
            );

        }

        complaints = data.complaints;

        updateStatistics(data.statistics);

        renderComplaints();

    } catch (error) {

        console.error("Dashboard error:", error);

        formMessage.textContent =
            "Could not connect to CivicTrack. Refresh the page.";

    }

}


// ==========================================
// SUBMIT CITIZEN COMPLAINT
// ==========================================

complaintForm.addEventListener("submit", async event => {

    event.preventDefault();

    const formData = new FormData(complaintForm);

    const complaintData = {

        title: String(
            formData.get("title") || ""
        ).trim(),

        category: String(
            formData.get("category") || ""
        ),

        location: String(
            formData.get("location") || ""
        ).trim(),

        description: String(
            formData.get("description") || ""
        ).trim()

    };


    const button = complaintForm.querySelector(
        'button[type="submit"]'
    );

    button.disabled = true;

    formMessage.textContent = "Submitting complaint...";


    try {

        const response = await fetch(
            "/api/complaints",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(complaintData)
            }
        );

        const data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.error || "Complaint submission failed."
            );

        }

        complaintForm.reset();

        formMessage.textContent =
            `Complaint ${data.complaint.reference} submitted successfully.`;

        statusFilter.value = "All";

        await loadDashboard();

    } catch (error) {

        formMessage.textContent = error.message;

    } finally {

        button.disabled = false;

    }

});


// ==========================================
// TRACKING BUTTON
// ==========================================

complaintList.addEventListener("click", async event => {

    const button = event.target.closest(
        "button[data-reference]"
    );

    if (!button) {
        return;
    }


    const mainRow = button.closest("tr");

    const historyRow = mainRow.nextElementSibling;

    const historyCell = historyRow.querySelector(
        ".tracking-cell"
    );


    // Toggle an already loaded timeline.

    if (
        !historyRow.hidden &&
        button.dataset.loaded === "true"
    ) {

        historyRow.hidden = true;
        button.textContent = "View Tracking";

        return;

    }


    historyRow.hidden = false;

    button.disabled = true;
    button.textContent = "Loading...";

    try {

        await loadTracking(
            button.dataset.reference,
            historyCell
        );

        button.dataset.loaded = "true";
        button.textContent = "Hide Tracking";

    } catch (error) {

        historyCell.replaceChildren(
            createElement("p", "empty-row", error.message)
        );

        button.textContent = "Retry Tracking";

    } finally {

        button.disabled = false;

    }

});


// ==========================================
// FILTER AND START APPLICATION
// ==========================================

statusFilter.addEventListener(
    "change",
    renderComplaints
);

loadDashboard();

