
/*
 * CivicTrack v0.1
 * Frontend application logic.
 */


/* ==========================================
   INITIAL DATA
   ========================================== */

const STORAGE_KEY = "civictrack-complaints";


const defaultComplaints = [

    {
        id: "CT-1003",
        title: "Damaged road surface",
        category: "Road Damage",
        location: "Central Avenue",
        status: "Pending"
    },

    {
        id: "CT-1002",
        title: "Streetlight not working",
        category: "Streetlight",
        location: "Lake View Road",
        status: "Pending"
    },

    {
        id: "CT-1001",
        title: "Garbage collection delayed",
        category: "Garbage",
        location: "Market Street",
        status: "Resolved"
    }

];


/* ==========================================
   APPLICATION STATE
   ========================================== */

// Load complaints previously stored in the browser.

function loadComplaints() {

    try {

        const saved = localStorage.getItem(STORAGE_KEY);

        if (saved === null) {
            return [...defaultComplaints];
        }

        const parsed = JSON.parse(saved);

        if (!Array.isArray(parsed)) {
            return [...defaultComplaints];
        }

        return parsed;

    } catch (error) {

        console.error("Could not load complaints:", error);

        return [...defaultComplaints];

    }

}


let complaints = loadComplaints();


/* ==========================================
   HTML ELEMENT REFERENCES
   ========================================== */

const complaintForm = document.querySelector(
    "#complaint-form"
);

const complaintList = document.querySelector(
    "#complaint-list"
);

const statusFilter = document.querySelector(
    "#status-filter"
);

const formMessage = document.querySelector(
    "#form-message"
);


/* ==========================================
   SAVE DATA
   ========================================== */

function saveComplaints() {

    try {

        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(complaints)
        );

        return true;

    } catch (error) {

        console.error("Could not save complaints:", error);

        return false;

    }

}


/* ==========================================
   CREATE TABLE CELLS
   ========================================== */

// Create elements using textContent.
// This avoids interpreting user-provided text as HTML.

function createCell(value) {

    const cell = document.createElement("td");

    const text = document.createElement("span");

    text.textContent = value;

    cell.appendChild(text);

    return cell;

}


/* ==========================================
   RENDER COMPLAINTS
   ========================================== */

function renderComplaints() {

    complaintList.replaceChildren();


    // Apply the selected status filter.

    const selectedStatus = statusFilter.value;

    const filteredComplaints = complaints.filter(
        complaint => {

            return (
                selectedStatus === "All" ||
                complaint.status === selectedStatus
            );

        }
    );


    // Display empty-state message.

    if (filteredComplaints.length === 0) {

        const row = document.createElement("tr");

        const cell = document.createElement("td");

        cell.colSpan = 5;

        cell.className = "empty-row";

        cell.textContent = "No complaints found.";

        row.appendChild(cell);

        complaintList.appendChild(row);

    }


    // Build each complaint row.

    for (const complaint of filteredComplaints) {

        const row = document.createElement("tr");


        // Reference number.

        const referenceCell = document.createElement("td");

        const reference = document.createElement("strong");

        reference.textContent = complaint.id;

        referenceCell.appendChild(reference);


        // Issue title.

        const titleCell = document.createElement("td");

        const title = document.createElement("strong");

        title.textContent = complaint.title;

        titleCell.appendChild(title);


        // Category.

        const categoryCell = createCell(
            complaint.category
        );


        // Location.

        const locationCell = createCell(
            complaint.location
        );


        // Status.

        const statusCell = document.createElement("td");

        const status = document.createElement("span");

        const statusClass = complaint.status
            .toLowerCase()
            .replaceAll(" ", "-");

        status.className = `status ${statusClass}`;

        status.textContent = complaint.status;

        statusCell.appendChild(status);


        // Add cells to the row.

        row.append(
            referenceCell,
            titleCell,
            categoryCell,
            locationCell,
            statusCell
        );


        complaintList.appendChild(row);

    }


    updateStatistics();

}


/* ==========================================
   UPDATE DASHBOARD STATISTICS
   ========================================== */

function updateStatistics() {

    const total = complaints.length;

    const pending = complaints.filter(
        complaint => complaint.status === "Pending"
    ).length;

    const resolved = complaints.filter(
        complaint => complaint.status === "Resolved"
    ).length;


    document.querySelector(
        "#total-count"
    ).textContent = total;


    document.querySelector(
        "#pending-count"
    ).textContent = pending;


    document.querySelector(
        "#resolved-count"
    ).textContent = resolved;

}


/* ==========================================
   SUBMIT COMPLAINT
   ========================================== */

complaintForm.addEventListener("submit", event => {

    // Prevent the browser from reloading the page.

    event.preventDefault();


    // Read form values.

    const formData = new FormData(complaintForm);


    const title = String(
        formData.get("title") || ""
    ).trim();


    const category = String(
        formData.get("category") || ""
    );


    const location = String(
        formData.get("location") || ""
    ).trim();


    const description = String(
        formData.get("description") || ""
    ).trim();


    // Basic validation.

    if (!title || !category || !location || !description) {

        formMessage.textContent =
            "Please complete every field.";

        return;

    }


    // Create a new complaint object.

    const complaint = {

        id: `CT-${Date.now()}`,

        title: title,

        category: category,

        location: location,

        description: description,

        status: "Pending",

        createdAt: new Date().toISOString()

    };


    // Add the new complaint to application state.

    complaints.unshift(complaint);


    // Save and refresh the dashboard.

    const saved = saveComplaints();

    renderComplaints();

    complaintForm.reset();


    if (saved) {

        formMessage.textContent =
            `Complaint ${complaint.id} submitted successfully.`;

    } else {

        formMessage.textContent =
            "Complaint added for this session, but browser storage failed.";

    }

});


/* ==========================================
   FILTER COMPLAINTS
   ========================================== */

statusFilter.addEventListener("change", () => {

    renderComplaints();

});


/* ==========================================
   START APPLICATION
   ========================================== */

renderComplaints();

