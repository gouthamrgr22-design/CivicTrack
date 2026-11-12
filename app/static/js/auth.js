
// ==========================================
// CIVICTRACK LOGIN INTERFACE
// ==========================================

const loginForm = document.querySelector("#login-form");

const passwordInput = document.querySelector("#password");

const togglePassword = document.querySelector(
    "#toggle-password"
);

const loginMessage = document.querySelector(
    "#login-message"
);


// ==========================================
// SHOW / HIDE PASSWORD
// ==========================================

togglePassword.addEventListener("click", () => {

    const isHidden = passwordInput.type === "password";

    passwordInput.type = isHidden ? "text" : "password";

    togglePassword.textContent = isHidden ? "Hide" : "Show";

    togglePassword.setAttribute(
        "aria-label",
        isHidden ? "Hide password" : "Show password"
    );

    togglePassword.setAttribute(
        "aria-pressed",
        String(isHidden)
    );

});


// ==========================================
// LOGIN FORM SUBMISSION
// ==========================================

loginForm.addEventListener("submit", event => {

    // Prevent the browser's normal form submission.
    event.preventDefault();

    // This prototype does not authenticate accounts.
    // It does not read, transmit or store the password.

    loginMessage.textContent =
        "The login interface is ready. Real account authentication " +
        "will be connected when the backend is implemented. " +
        "No credentials were sent or saved.";

    // Clear the entered credentials after the demo action.
    loginForm.reset();

    // Restore the password visibility control.
    passwordInput.type = "password";

    togglePassword.textContent = "Show";

    togglePassword.setAttribute(
        "aria-label",
        "Show password"
    );

    togglePassword.setAttribute(
        "aria-pressed",
        "false"
    );

});

