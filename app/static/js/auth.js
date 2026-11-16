
"use strict";

/* =====================================================
   CIVICTRACK V3 — AUTHENTICATION
   Citizen, Employee and Administrator Login
   ===================================================== */


/* =====================================================
   ELEMENT REFERENCES
   ===================================================== */

const authForm = document.querySelector("#auth-form");

const authHeading = document.querySelector("#auth-heading");
const authSubheading = document.querySelector("#auth-subheading");
const authMessage = document.querySelector("#auth-message");

const fullNameField = document.querySelector("#full-name-field");
const usernameField = document.querySelector("#username-field");
const departmentField = document.querySelector("#department-field");
const confirmPasswordField = document.querySelector("#confirm-password-field");

const employeeNotice = document.querySelector("#employee-notice");

const fullNameInput = document.querySelector("#full-name");
const usernameInput = document.querySelector("#username");
const identityInput = document.querySelector("#identity");
const passwordInput = document.querySelector("#password");
const confirmPasswordInput = document.querySelector("#confirm-password");
const departmentInput = document.querySelector("#department");

const identityLabel = document.querySelector("#identity-label");
const forgotPassword = document.querySelector("#forgot-password");

const submitButton = document.querySelector("#auth-submit");
const submitText = document.querySelector("#submit-text");
const googleButton = document.querySelector("#google-login");


/* =====================================================
   AUTHENTICATION CONFIGURATION
   ===================================================== */

const MIN_PASSWORD_LENGTH = 12;

const DASHBOARD_ROUTES = Object.freeze({

    citizen: "/",

    employee: "/employee",

    admin: "/admin"

});


/* =====================================================
   AUTHENTICATION STATE
   ===================================================== */

let selectedRole = "citizen";
let selectedMode = "login";
let isSubmitting = false;


/* =====================================================
   MESSAGE HANDLING
   ===================================================== */

function showMessage(message, type = "error") {

    authMessage.textContent = message;
    authMessage.dataset.type = type;

}


function clearMessage() {

    authMessage.textContent = "";

    delete authMessage.dataset.type;

}


/* =====================================================
   SUBMISSION STATE
   ===================================================== */

function setSubmitting(submitting) {

    isSubmitting = submitting;

    submitButton.disabled = submitting;

    submitText.textContent = submitting
        ? "Please wait..."
        : getSubmitLabel();

}


function getSubmitLabel() {

    if (selectedMode === "register") {

        return selectedRole === "employee"
            ? "Request Access"
            : "Create Account";

    }

    return selectedRole === "employee"
        ? "Employee Sign In"
        : "Sign In";

}


/* =====================================================
   INTERFACE UPDATE
   ===================================================== */

function updateInterface() {

    const isLogin = selectedMode === "login";

    const isEmployee = selectedRole === "employee";

    const isRegisteringEmployee = !isLogin && isEmployee;

    fullNameField.hidden = isLogin;

    usernameField.hidden = isLogin;

    confirmPasswordField.hidden = isLogin;

    departmentField.hidden = !isRegisteringEmployee;

    employeeNotice.hidden = !isRegisteringEmployee;

    forgotPassword.hidden = !isLogin;

    fullNameInput.required = !isLogin;

    usernameInput.required = !isLogin;

    identityInput.required = true;

    passwordInput.required = true;

    confirmPasswordInput.required = !isLogin;

    departmentInput.required = isRegisteringEmployee;


    /* Identity input */

    if (isLogin) {

        identityInput.type = "text";

        identityLabel.textContent = "Email or Username";

        identityInput.placeholder =
            "Enter your email or username";

        identityInput.autocomplete = "username";

    } else {

        identityInput.type = "email";

        identityLabel.textContent = "Email Address";

        identityInput.placeholder = "you@example.com";

        identityInput.autocomplete = "email";

    }


    /* Password autocomplete */

    passwordInput.autocomplete = isLogin
        ? "current-password"
        : "new-password";


    /* Page headings */

    if (isLogin && !isEmployee) {

        authHeading.textContent = "Welcome back.";

        authSubheading.textContent =
            "Sign in to continue to your CivicTrack account. Administrators can use their administrator username here too.";

    } else if (isLogin && isEmployee) {

        authHeading.textContent = "Employee access.";

        authSubheading.textContent =
            "Sign in to access your employee workspace.";

    } else if (!isLogin && !isEmployee) {

        authHeading.textContent = "Join your community.";

        authSubheading.textContent =
            "Create your CivicTrack citizen account.";

    } else {

        authHeading.textContent = "Request employee access.";

        authSubheading.textContent =
            "Register your details for administrator review.";

    }


    /* Role selector */

    document.querySelectorAll(".role-option").forEach(button => {

        const active = button.dataset.role === selectedRole;

        button.classList.toggle("active", active);

        button.setAttribute(
            "aria-pressed",
            String(active)
        );

    });


    /* Login / registration tabs */

    document.querySelectorAll(".auth-tab").forEach(button => {

        const active = button.dataset.mode === selectedMode;

        button.classList.toggle("active", active);

        button.setAttribute(
            "aria-pressed",
            String(active)
        );

    });


    submitText.textContent = getSubmitLabel();

    clearMessage();

}


/* =====================================================
   ROLE SELECTION
   Public registration supports only:
   - Citizen
   - Employee

   Administrator accounts are created separately.
   ===================================================== */

document.querySelectorAll(".role-option").forEach(button => {

    button.addEventListener("click", () => {

        if (isSubmitting) return;

        const role = button.dataset.role;

        if (!["citizen", "employee"].includes(role)) {

            showMessage(
                "This account type cannot be selected for public registration."
            );

            return;

        }

        selectedRole = role;

        updateInterface();

    });

});


/* =====================================================
   LOGIN / REGISTRATION SWITCHING
   ===================================================== */

document.querySelectorAll(".auth-tab").forEach(button => {

    button.addEventListener("click", () => {

        if (isSubmitting) return;

        selectedMode = button.dataset.mode;

        updateInterface();

    });

});


/* =====================================================
   PASSWORD VISIBILITY
   ===================================================== */

document.querySelectorAll(".toggle-password").forEach(button => {

    button.addEventListener("click", () => {

        const input = document.getElementById(
            button.dataset.target
        );

        if (!input) return;

        const isHidden = input.type === "password";

        input.type = isHidden
            ? "text"
            : "password";

        button.textContent = isHidden
            ? "HIDE"
            : "SHOW";

        button.setAttribute(
            "aria-label",
            isHidden
                ? "Hide password"
                : "Show password"
        );

        button.setAttribute(
            "aria-pressed",
            String(isHidden)
        );

    });

});


/* =====================================================
   API RESPONSE HANDLING
   ===================================================== */

async function readAPIResponse(response) {

    const contentType =
        response.headers.get("content-type") || "";

    if (!contentType.includes("application/json")) {

        throw new Error(
            "The server returned an unexpected response. Please try again."
        );

    }

    return await response.json();

}


/* =====================================================
   AUTHENTICATED ROLE REDIRECTION
   The backend/database role is authoritative.
   ===================================================== */

function redirectAuthenticatedUser(user) {

    if (!user || typeof user.role !== "string") {

        showMessage(
            "The server returned an incomplete account response."
        );

        return false;

    }

    const destination = DASHBOARD_ROUTES[user.role];

    if (!destination) {

        showMessage(
            "Your account has an unsupported role. Please contact the administrator."
        );

        return false;

    }

    showMessage(
        "Login successful. Opening your dashboard...",
        "success"
    );

    window.location.assign(destination);

    return true;

}


/* =====================================================
   LOGIN API
   ===================================================== */

async function loginAccount() {

    const payload = {

        identifier: identityInput.value.trim(),

        password: passwordInput.value

    };


    const response = await fetch("/api/auth/login", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        credentials: "same-origin",

        body: JSON.stringify(payload)

    });


    const result = await readAPIResponse(response);


    if (!response.ok) {

        showMessage(
            result.error || "Sign in failed. Please try again."
        );

        return;

    }


    const user = result.user;


    if (!user || !user.role) {

        showMessage(
            "The server returned an incomplete account response."
        );

        return;

    }


    /* The backend determines the actual account role. */

    const destination = DASHBOARD_ROUTES[user.role];

    if (!destination) {

        showMessage(
            "Unknown account role. Please contact the administrator."
        );

        return;

    }


    passwordInput.value = "";

    redirectAuthenticatedUser(user);

}


/* =====================================================
   REGISTRATION API
   ===================================================== */

async function registerAccount() {

    const payload = {

        full_name: fullNameInput.value.trim(),

        username: usernameInput.value.trim(),

        email: identityInput.value.trim(),

        password: passwordInput.value,

        role: selectedRole,

        department: selectedRole === "employee"
            ? departmentInput.value
            : ""

    };


    resendEmailInput.value = payload.email;

    const response = await fetch("/api/auth/register", {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        credentials: "same-origin",

        body: JSON.stringify(payload)

    });


    const result = await readAPIResponse(response);


    if (!response.ok) {

        showMessage(
            result.error || "Account registration failed."
        );

        return;

    }


    passwordInput.value = "";

    confirmPasswordInput.value = "";


    showMessage(
        result.message ||
        "Account created. Please check your email for verification.",
        "success"
    );

}


/* =====================================================
   FORM SUBMISSION
   ===================================================== */

authForm.addEventListener("submit", async event => {

    event.preventDefault();

    if (isSubmitting) return;

    clearMessage();


    if (!authForm.checkValidity()) {

        authForm.reportValidity();

        return;

    }


    /* Match the backend password requirement. */

    if (passwordInput.value.length < MIN_PASSWORD_LENGTH) {

        showMessage(
            `Password must contain at least ${MIN_PASSWORD_LENGTH} characters.`
        );

        passwordInput.focus();

        return;

    }


    /* Registration password confirmation. */

    if (
        selectedMode === "register" &&
        passwordInput.value !== confirmPasswordInput.value
    ) {

        showMessage(
            "Passwords do not match. Please check again."
        );

        confirmPasswordInput.focus();

        return;

    }


    setSubmitting(true);


    try {

        if (selectedMode === "login") {

            await loginAccount();

        } else {

            await registerAccount();

        }

    } catch (error) {

        console.error(
            "CivicTrack authentication error:",
            error
        );

        showMessage(
            error.message ||
            "Unable to contact CivicTrack. Check your connection."
        );

    } finally {

        setSubmitting(false);

    }

});


/* =====================================================
   GOOGLE IDENTITY SERVICES
   Server-verified ID token + nonce-bound same-origin session.
   ===================================================== */

async function handleGoogleCredential(credentialResponse) {

    if (isSubmitting) return;

    if (
        selectedMode === "register" &&
        selectedRole === "employee" &&
        !departmentInput.value
    ) {
        showMessage("Select your department before requesting employee access.");
        departmentInput.focus();
        return;
    }

    if (!credentialResponse || !credentialResponse.credential) {
        showMessage("Google did not return an identity token. Please try again.");
        return;
    }

    setSubmitting(true);
    googleButton.setAttribute("aria-busy", "true");

    try {
        const response = await fetch("/api/auth/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({
                credential: credentialResponse.credential,
                mode: selectedMode,
                role: selectedRole,
                department: selectedRole === "employee"
                    ? departmentInput.value
                    : ""
            })
        });

        const result = await readAPIResponse(response);

        if (result.requires_email_verification) {
            showMessage(
                result.message || "Check your inbox for a verification link.",
                "success"
            );
            return;
        }

        if (result.pending_approval) {
            showMessage(
                result.message || "Your employee account is awaiting administrator approval.",
                "success"
            );
            return;
        }

        if (!response.ok) {
            showMessage(result.error || "Google sign-in failed. Please try again.");
            return;
        }

        redirectAuthenticatedUser(result.user);

    } catch (error) {
        console.error("CivicTrack Google sign-in error:", error);
        showMessage(error.message || "Google sign-in could not reach CivicTrack.");
    } finally {
        googleButton.removeAttribute("aria-busy");
        setSubmitting(false);
    }
}

function loadGoogleIdentityServices() {

    fetch("/api/auth/google-config", {
        credentials: "same-origin",
        cache: "no-store"
    })
    .then(readAPIResponse)
    .then(config => {
        if (!config.client_id || !config.nonce) {
            throw new Error("Google Sign-In is not configured. Ask the administrator to set GOOGLE_CLIENT_ID.");
        }

        const initialize = () => {
            if (!window.google || !window.google.accounts || !window.google.accounts.id) {
                showMessage("Google Sign-In could not load. Check your connection or content blocker.");
                return;
            }

            window.google.accounts.id.initialize({
                client_id: config.client_id,
                nonce: config.nonce,
                callback: handleGoogleCredential,
                auto_select: false,
                cancel_on_tap_outside: true
            });

            googleButton.replaceChildren();
            window.google.accounts.id.renderButton(googleButton, {
                type: "standard",
                theme: "outline",
                size: "large",
                shape: "rectangular",
                text: "continue_with",
                width: Math.min(360, googleButton.clientWidth || 360),
                logo_alignment: "left"
            });
        };

        if (window.google && window.google.accounts && window.google.accounts.id) {
            initialize();
            return;
        }

        const script = document.createElement("script");
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.defer = true;
        script.onload = initialize;
        script.onerror = () => showMessage("Google Sign-In could not load. Check your connection.");
        document.head.appendChild(script);
    })
    .catch(error => {
        console.error("CivicTrack Google configuration error:", error);
        showMessage(error.message || "Google Sign-In is unavailable. Check server configuration.", "info");
    });
}


/* =====================================================
   RESEND EMAIL VERIFICATION
   ===================================================== */

const resendButton = document.querySelector("#resend-verification-button");
const resendEmailInput = document.querySelector("#resend-email");
const resendMessage = document.querySelector("#resend-message");

resendButton.addEventListener("click", async () => {
    const email = resendEmailInput.value.trim();
    resendMessage.textContent = "";

    if (!email || !resendEmailInput.checkValidity()) {
        resendEmailInput.reportValidity();
        return;
    }

    resendButton.disabled = true;
    resendButton.textContent = "Sending...";

    try {
        const response = await fetch("/api/auth/resend-verification", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ email })
        });
        const result = await readAPIResponse(response);
        if (!response.ok) throw new Error(result.error || "Could not request a new link.");
        resendMessage.textContent = result.message || "Check your inbox shortly.";
    } catch (error) {
        resendMessage.textContent = error.message || "Could not contact CivicTrack.";
    } finally {
        resendButton.disabled = false;
        resendButton.textContent = "Resend verification email";
    }
});


/* =====================================================
   FORGOT PASSWORD — FUTURE FEATURE
   ===================================================== */

forgotPassword.addEventListener("click", () => {

    showMessage(
        "Password recovery is not available yet. Please contact the administrator if you cannot access your account.",
        "info"
    );

});


/* =====================================================
   INITIALIZE
   ===================================================== */

updateInterface();

loadGoogleIdentityServices();

