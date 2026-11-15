
"use strict";

/* =====================================================
   CIVICTRACK V3 — EMAIL VERIFICATION
   Connects the verification page to the backend API
   ===================================================== */

const heading = document.querySelector("#verification-heading");
const description = document.querySelector("#verification-description");
const status = document.querySelector("#verification-status");
const actions = document.querySelector("#verification-actions");


/* =====================================================
   UPDATE VERIFICATION INTERFACE
   ===================================================== */

function showResult(type, title, message) {

    heading.textContent = title;
    description.textContent = message;

    status.textContent = message;
    status.dataset.type = type;

    actions.hidden = false;

}


/* =====================================================
   READ TOKEN FROM URL FRAGMENT
   ===================================================== */

function getVerificationToken() {

    const fragment = window.location.hash;

    const parameters = new URLSearchParams(
        fragment.startsWith("#")
            ? fragment.slice(1)
            : fragment
    );

    return parameters.get("token");

}


/* =====================================================
   VERIFY EMAIL THROUGH BACKEND
   ===================================================== */

async function verifyEmail() {

    const token = getVerificationToken();

    if (!token) {

        showResult(
            "error",
            "Verification link missing.",
            "No verification token was found. Please open the link from your verification email."
        );

        return;

    }

    if (token.length < 20 || token.length > 128) {

        showResult(
            "error",
            "Invalid verification link.",
            "The verification token is not valid. Please request a new verification email."
        );

        return;

    }

    /* Remove the token from the visible browser URL. */

    window.history.replaceState(
        null,
        "",
        window.location.pathname + window.location.search
    );

    status.textContent = "Verifying your email address...";

    status.dataset.type = "loading";

    try {

        const response = await fetch("/api/auth/verify-email", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            credentials: "same-origin",

            body: JSON.stringify({
                token: token
            })

        });

        const result = await response.json();

        if (!response.ok) {

            showResult(
                "error",
                "Verification unsuccessful.",
                result.error || "Your verification link could not be accepted."
            );

            return;

        }

        showResult(
            "success",
            "Email verified!",
            result.message || "Your email has been verified. You can now sign in."
        );

    } catch (error) {

        console.error("Email verification error:", error);

        showResult(
            "error",
            "Connection problem.",
            "We could not contact CivicTrack. Please check your connection and try again."
        );

    }

}


/* =====================================================
   INITIALIZE
   ===================================================== */

verifyEmail();

