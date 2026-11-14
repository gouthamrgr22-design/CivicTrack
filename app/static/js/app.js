
/*
 * CivicTrack v2
 * Citizen portal: SQLite complaints and tracking timeline.
 * Multilingual interface: English + Kannada.
 */

let complaints = [];

const complaintForm = document.querySelector("#complaint-form");
const complaintList = document.querySelector("#complaint-list");
const statusFilter = document.querySelector("#status-filter");
const formMessage = document.querySelector("#form-message");

// Cache tracking responses so expanded timelines can be
// redrawn when the user changes the language.
const trackingDataCache = new Map();


// ==========================================
// CIVICTRACK TRANSLATION HELPERS
// ==========================================

function tr(key, replacements = {}) {

    let translation = key;

    if (
        typeof CivicI18n !== "undefined" &&
        typeof CivicI18n.translate === "function"
    ) {
        translation = CivicI18n.translate(key) || key;
    }

    for (const [name, value] of Object.entries(replacements)) {
        translation = translation.replaceAll(
            `{${name}}`,
            String(value)
        );
    }

    return translation;
}


// ==========================================
// STATUS TRANSLATION
// ==========================================

function translateStatus(status) {

    const statusKeys = {
        "New": "status.new",
        "Pending": "status.pending",
        "Pending Review": "status.pendingReview",
        "Approved": "status.approved",
        "In Progress": "status.inProgress",
        "Rejected": "status.rejected",
        "Resolved": "status.resolved"
    };

    const key = statusKeys[status];

    return key ? tr(key) : status;
}


// ==========================================
// CATEGORY TRANSLATION
// ==========================================

function translateCategory(category) {

    const categoryKeys = {
        "Road Damage": "categories.roadDamage",
        "Streetlight": "categories.streetlight",
        "Water Leakage": "categories.waterLeakage",
        "Drainage": "categories.drainage",
        "Garbage": "categories.garbage",
        "Garbage Collection": "categories.garbage",
        "Other": "categories.other"
    };

    const key = categoryKeys[category];

    return key ? tr(key) : category;
}


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
// STATUS DISPLAY CLASS
// ==========================================

function getStatusClass(status) {

    // Keep the original English status for CSS classes.
    // Only the visible text is translated.

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
            tr("common.noComplaints")
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
            createElement(
                "td",
                "",
                complaint.reference
            ),

            createElement(
                "td",
                "",
                complaint.title
            ),

            createElement(
                "td",
                "",
                translateCategory(complaint.category)
            ),

            createElement(
                "td",
                "",
                complaint.location
            )
        );


        // Status cell.

        const statusCell = document.createElement("td");

        const status = createElement(
            "span",
            `status ${getStatusClass(complaint.status)}`,
            translateStatus(complaint.status)
        );

        statusCell.appendChild(status);

        row.appendChild(statusCell);


        // Tracking button.

        const trackingCell = document.createElement("td");

        const trackingButton = createElement(
            "button",
            "track-button",
            tr("common.viewTracking")
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
            `${translateCategory(complaint.category)} · ${complaint.department}`
        )
    );


    // Current status.

    const currentStatus = createElement(
        "span",
        `status ${getStatusClass(complaint.status)}`,
        `${tr("tracking.currentStatus")}: ${translateStatus(complaint.status)}`
    );

    heading.append(headingText, currentStatus);

    panel.appendChild(heading);


    // Original complaint description.
    // User-submitted content stays unchanged.

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
                `${tr("tracking.rejectionReason")}: ${complaint.rejection_reason}`
            )
        );

    }


    // Resolution details.

    if (complaint.resolution_note) {

        panel.appendChild(
            createElement(
                "p",
                "tracking-resolution",
                `${tr("tracking.resolution")}: ${complaint.resolution_note}`
            )
        );

    }


    // Activity history heading.

    panel.appendChild(
        createElement(
            "h4",
            "timeline-title",
            tr("tracking.activityHistory")
        )
    );


    const timeline = createElement(
        "div",
        "tracking-timeline"
    );


    // No activity.

    if (data.updates.length === 0) {

        timeline.appendChild(
            createElement(
                "p",
                "empty-row",
                tr("tracking.noActivity")
            )
        );

    }


    // Translate activity names.

    const actionNames = {
        submitted: tr("tracking.actions.submitted"),
        approve: tr("tracking.actions.approve"),
        reject: tr("tracking.actions.reject"),
        take: tr("tracking.actions.take"),
        update: tr("tracking.actions.update"),
        resolve: tr("tracking.actions.resolve")
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


        // Previous status -> New status.

        const transition = createElement(
            "div",
            "status-transition"
        );

        transition.append(
            createElement(
                "span",
                "transition-from",
                translateStatus(update.previous_status || "New")
            ),

            createElement(
                "span",
                "transition-arrow",
                "→"
            ),

            createElement(
                "span",
                "transition-to",
                translateStatus(update.new_status || "Pending Review")
            )
        );

        event.appendChild(transition);


        // Original employee/citizen message.
        // Do not automatically translate user-written content.

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
                `${tr("tracking.recordedBy")}: ${update.actor_name}`
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

    // Reuse cached tracking information when available.

    let data = trackingDataCache.get(reference);

    if (!data) {

        const response = await fetch(
            `/api/complaints/${encodeURIComponent(reference)}/tracking`,
            {
                cache: "no-store"
            }
        );

        data = await response.json();

        if (!response.ok) {

            throw new Error(
                data.error || tr("errors.unableToLoadHistory")
            );

        }

        trackingDataCache.set(reference, data);

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
                data.error || tr("errors.couldNotLoadComplaints")
            );

        }

        complaints = data.complaints;

        updateStatistics(data.statistics);

        renderComplaints();

    } catch (error) {

        console.error("Dashboard error:", error);

        formMessage.textContent =
            tr("errors.couldNotConnect");

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

    formMessage.textContent = tr("form.submitting");


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
                data.error || tr("form.submitFailed")
            );

        }

        complaintForm.reset();

        formMessage.textContent = tr("form.submitted", {
            reference: data.complaint.reference
        });

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

        button.textContent = tr("common.viewTracking");

        return;

    }


    historyRow.hidden = false;

    button.disabled = true;
    button.textContent = tr("common.loading");


    try {

        await loadTracking(
            button.dataset.reference,
            historyCell
        );

        button.dataset.loaded = "true";

        button.textContent = tr("common.hideTracking");

    } catch (error) {

        historyCell.replaceChildren(
            createElement("p", "empty-row", error.message)
        );

        button.textContent = tr("common.retryTracking");

    } finally {

        button.disabled = false;

    }

});


// ==========================================
// LANGUAGE CHANGE EVENT
// ==========================================

document.addEventListener(
    "civictrack:languageChanged",
    () => {

        // Remember which tracking panels are currently open.

        const expandedReferences = Array.from(
            complaintList.querySelectorAll("button[data-reference]")
        )
            .filter(button => {

                const historyRow =
                    button.closest("tr").nextElementSibling;

                return (
                    !historyRow.hidden &&
                    button.dataset.loaded === "true"
                );

            })
            .map(button => button.dataset.reference);


        // Re-render complaint rows in the selected language.

        renderComplaints();


        // Restore previously expanded tracking panels.

        for (const reference of expandedReferences) {

            const button = Array.from(
                complaintList.querySelectorAll("button[data-reference]")
            ).find(item => item.dataset.reference === reference);

            if (!button) {
                continue;
            }

            const historyRow =
                button.closest("tr").nextElementSibling;

            const historyCell =
                historyRow.querySelector(".tracking-cell");

            historyRow.hidden = false;

            button.dataset.loaded = "true";
            button.textContent = tr("common.hideTracking");

            const cachedData = trackingDataCache.get(reference);

            if (cachedData) {

                historyCell.replaceChildren(
                    renderTracking(cachedData)
                );

            }

        }

    }
);


// ==========================================
// FILTER AND START APPLICATION
// ==========================================

statusFilter.addEventListener(
    "change",
    renderComplaints
);


loadDashboard();

