"use strict";

/* =====================================================
   CIVICTRACK V3 — ADMIN DASHBOARD
   ===================================================== */

const OVERVIEW_API = "/api/admin/overview";
const DECISION_API = "/api/admin/employees";

let adminUser = null;
let dashboardData = null;

const messageBox = document.querySelector("#admin-message");
const employeeTable = document.querySelector("#employee-table-body");
const complaintTable = document.querySelector("#complaint-table-body");
const employeeFilter = document.querySelector("#employee-filter");


/* =====================================================
   HELPERS
   ===================================================== */

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[character]);
}


function formatDate(value) {
    if (!value) return "—";

    const date = new Date(value.replace(" ", "T") + "Z");

    if (Number.isNaN(date.getTime())) {
        return escapeHTML(value);
    }

    return date.toLocaleDateString();
}


function showMessage(message, type = "") {
    messageBox.textContent = message;
    messageBox.className = "admin-message";

    if (type) {
        messageBox.classList.add(type);
    }
}


async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        credentials: "same-origin",
        cache: "no-store",
        headers: {
            ...(options.body ? {
                "Content-Type": "application/json"
            } : {}),
            ...options.headers
        }
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(
            data.error || `Request failed (${response.status}).`
        );
    }

    return data;
}


/* =====================================================
   ADMIN IDENTITY
   ===================================================== */

async function loadAdminIdentity() {
    const data = await apiRequest("/api/auth/me");

    if (!data.user) {
        throw new Error("Administrator session not found.");
    }

    if (data.user.role !== "admin") {
        throw new Error("Administrator access is required.");
    }

    adminUser = data.user;

    const name = adminUser.full_name || "Administrator";

    document.querySelector("#admin-name").textContent = name;
    document.querySelector("#welcome-admin-name").textContent = name;
    document.querySelector("#account-admin-name").textContent = name;

    document.querySelector("#account-admin-email").textContent =
        adminUser.email || "Email unavailable";
}


/* =====================================================
   STATISTICS
   ===================================================== */

function updateStatistics(data) {
    const employees = data.employee_statistics || {};
    const complaints = data.complaint_statistics || {};

    document.querySelector("#stat-employees-total").textContent =
        employees.total ?? 0;

    document.querySelector("#stat-employees-pending").textContent =
        employees.pending ?? 0;

    document.querySelector("#stat-employees-active").textContent =
        employees.active ?? 0;

    document.querySelector("#stat-employees-rejected").textContent =
        employees.rejected ?? 0;

    document.querySelector("#stat-complaints-total").textContent =
        complaints.total ?? 0;

    document.querySelector("#stat-complaints-pending").textContent =
        complaints.pending_review ?? 0;

    document.querySelector("#stat-complaints-progress").textContent =
        complaints.in_progress ?? 0;

    document.querySelector("#stat-complaints-resolved").textContent =
        complaints.resolved ?? 0;

    document.querySelector("#sidebar-pending-count").textContent =
        employees.pending ?? 0;
}


/* =====================================================
   EMPLOYEE TABLE
   ===================================================== */

function getEmployeeStatusClass(status) {
    if (status === "active") return "status-active";
    if (status === "pending_approval") return "status-pending";
    if (status === "rejected") return "status-rejected";

    return "status-neutral";
}


function getEmployeeStatusLabel(status) {
    const labels = {
        active: "Active",
        pending_approval: "Pending Approval",
        rejected: "Rejected",
        suspended: "Suspended"
    };

    return labels[status] || status || "Unknown";
}


function renderEmployees() {
    if (!dashboardData) return;

    const filter = employeeFilter.value;

    const employees = (dashboardData.employees || []).filter(employee => {
        return filter === "all" || employee.account_status === filter;
    });

    if (!employees.length) {
        employeeTable.innerHTML = `
            <tr>
                <td colspan="6" class="table-empty">
                    No employees found for this filter.
                </td>
            </tr>
        `;
        return;
    }

    employeeTable.innerHTML = employees.map(employee => {
        const status = employee.account_status;
        const pending = status === "pending_approval";

        const actions = pending ? `
            <div class="admin-actions">
                <button
                    class="admin-action-button approve-button"
                    data-id="${Number(employee.id)}"
                    data-action="approve"
                    type="button"
                >
                    Approve
                </button>

                <button
                    class="admin-action-button reject-button"
                    data-id="${Number(employee.id)}"
                    data-action="reject"
                    type="button"
                >
                    Reject
                </button>
            </div>
        ` : `
            <span class="table-secondary">No action required</span>
        `;

        return `
            <tr>
                <td>
                    <span class="table-primary">
                        ${escapeHTML(employee.full_name)}
                    </span>
                    <span class="table-secondary">
                        @${escapeHTML(employee.username)}
                    </span>
                </td>

                <td>${escapeHTML(employee.department || "Unassigned")}</td>

                <td>
                    <span class="table-status ${
                        employee.email_verified
                            ? "status-active"
                            : "status-pending"
                    }">
                        ${employee.email_verified ? "Verified" : "Unverified"}
                    </span>
                </td>

                <td>
                    <span class="table-status ${getEmployeeStatusClass(status)}">
                        ${escapeHTML(getEmployeeStatusLabel(status))}
                    </span>
                </td>

                <td>${formatDate(employee.created_at)}</td>

                <td>${actions}</td>
            </tr>
        `;
    }).join("");
}


/* =====================================================
   COMPLAINT TABLE
   ===================================================== */

function getComplaintStatusClass(status) {
    if (status === "Resolved") return "status-active";
    if (status === "In Progress") return "status-progress";
    if (status === "Rejected") return "status-rejected";
    if (status === "Pending Review") return "status-pending";

    return "status-neutral";
}


function renderComplaints() {
    if (!dashboardData) return;

    const complaints = dashboardData.recent_complaints || [];

    if (!complaints.length) {
        complaintTable.innerHTML = `
            <tr>
                <td colspan="6" class="table-empty">
                    No complaints found.
                </td>
            </tr>
        `;
        return;
    }

    complaintTable.innerHTML = complaints.map(complaint => {
        const status = complaint.review_status || complaint.status;

        return `
            <tr>
                <td>
                    <span class="table-primary">
                        ${escapeHTML(complaint.reference)}
                    </span>
                </td>

                <td>
                    <span class="table-primary">
                        ${escapeHTML(complaint.title)}
                    </span>
                    <span class="table-secondary">
                        ${escapeHTML(complaint.location)}
                    </span>
                </td>

                <td>${escapeHTML(complaint.category)}</td>

                <td>${escapeHTML(complaint.department)}</td>

                <td>
                    <span class="table-status ${getComplaintStatusClass(status)}">
                        ${escapeHTML(status)}
                    </span>
                </td>

                <td>${formatDate(complaint.created_at)}</td>
            </tr>
        `;
    }).join("");
}


/* =====================================================
   EMPLOYEE APPROVAL / REJECTION
   ===================================================== */

async function decideEmployee(employeeId, action, button) {
    const actionLabel = action === "approve" ? "approve" : "reject";

    const confirmed = window.confirm(
        `Are you sure you want to ${actionLabel} this employee account?`
    );

    if (!confirmed) return;

    button.disabled = true;

    try {
        await apiRequest(
            `${DECISION_API}/${employeeId}/decision`,
            {
                method: "POST",
                body: JSON.stringify({ action })
            }
        );

        showMessage(
            `Employee account ${actionLabel}d successfully.`,
            "success"
        );

        await loadOverview(false);

    } catch (error) {
        showMessage(error.message, "error");
        button.disabled = false;
    }
}


/* =====================================================
   LOAD ADMIN OVERVIEW
   ===================================================== */

async function loadOverview(showLoading = true) {
    if (showLoading) {
        showMessage("Loading administrator dashboard...");
    }

    try {
        const data = await apiRequest(OVERVIEW_API);

        dashboardData = data;

        updateStatistics(data);
        renderEmployees();
        renderComplaints();

        showMessage("Administrator dashboard updated.", "success");

    } catch (error) {
        showMessage(error.message, "error");
        throw error;
    }
}


/* =====================================================
   INITIALIZATION
   ===================================================== */

async function initializeDashboard() {
    try {
        await loadAdminIdentity();
        await loadOverview();

    } catch (error) {
        console.error("Admin dashboard:", error);

        if (
            error.message.includes("401") ||
            error.message.includes("session")
        ) {
            window.location.href = "/templates/login.html";
            return;
        }

        showMessage(error.message, "error");
    }
}


/* =====================================================
   EVENT LISTENERS
   ===================================================== */

employeeFilter.addEventListener("change", renderEmployees);

employeeTable.addEventListener("click", event => {
    const button = event.target.closest("[data-action]");

    if (!button || button.disabled) return;

    const employeeId = Number(button.dataset.id);
    const action = button.dataset.action;

    if (!Number.isInteger(employeeId) || employeeId <= 0) return;

    decideEmployee(employeeId, action, button);
});


document.querySelector("#admin-refresh").addEventListener(
    "click",
    () => initializeDashboard()
);


document.querySelector("#admin-logout").addEventListener(
    "click",
    async () => {
        try {
            await apiRequest(
                "/api/auth/logout",
                { method: "POST" }
            );
        } finally {
            window.location.href = "/templates/login.html";
        }
    }
);


document.querySelectorAll(".admin-nav-link").forEach(link => {
    link.addEventListener("click", () => {
        document.querySelectorAll(".admin-nav-link").forEach(item => {
            item.classList.remove("active");
        });

        link.classList.add("active");
    });
});


initializeDashboard();
