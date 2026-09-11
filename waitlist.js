const API_URL = (() => {
    if (window.RATED_API_URL) {
        return window.RATED_API_URL;
    }
    const { hostname, port } = window.location;
    if (hostname === "127.0.0.1" || hostname === "localhost") {
        return port === "8000" ? "" : "http://127.0.0.1:8000";
    }
    return "";
})();

const form = document.getElementById("waitlistForm");
const errorNode = document.getElementById("formError");
const submitButton = document.getElementById("submitButton");
const signupCard = document.getElementById("signupCard");
const thanksCard = document.getElementById("thanksCard");
const proof = document.getElementById("socialProof");

function showError(message) {
    errorNode.hidden = false;
    errorNode.textContent = message;
}

function hideError() {
    errorNode.hidden = true;
    errorNode.textContent = "";
}

function thankYou(username, email, emailSent) {
    const title = document.getElementById("thanksTitle");
    const body = document.getElementById("thanksBody");

    title.textContent = `You're locked in, ${username}.`;
    body.textContent = emailSent
        ? `We sent the receipt to ${email}. When RATED drops, that inbox gets the keys. Log in with this account and you'll have a gold star next to your name.`
        : `You're on the list as ${username}. When RATED drops, we'll hit ${email}. Keep your password — that's your seat, and your gold star.`;

    signupCard.hidden = true;
    thanksCard.hidden = false;
}

function readJson(key) {
    try {
        return JSON.parse(localStorage.getItem(key) || "[]");
    } catch (error) {
        return [];
    }
}

async function hashSecret(value) {
    const buffer = await crypto.subtle.digest(
        "SHA-256",
        new TextEncoder().encode(value)
    );
    return Array.from(new Uint8Array(buffer))
        .map(byte => byte.toString(16).padStart(2, "0"))
        .join("");
}

async function saveLocalWaitlist(username, email, password, updates) {
    email = email.toLowerCase();
    const waitlist = readJson("ratedWaitlistUsers");
    const locals = readJson("ratedLocalUsers");

    const taken = [...waitlist, ...locals].some(
        user =>
            user.email === email ||
            (user.username || "").toLowerCase() === username.toLowerCase()
    );

    if (taken) {
        throw new Error("You're already on the list.");
    }

    const salt = crypto.randomUUID();
    waitlist.push({
        id: Date.now(),
        username,
        email,
        salt,
        password_hash: await hashSecret(salt + password),
        is_founder: true,
        lists: {
            launch: true,
            updates
        },
        created_at: Date.now()
    });
    localStorage.setItem("ratedWaitlistUsers", JSON.stringify(waitlist));
}

async function loadCount() {
    try {
        const response = await fetch(`${API_URL}/waitlist/count`);
        if (!response.ok) {
            return showLocalCount();
        }
        const data = await response.json();
        if (data.launched) {
            localStorage.setItem("ratedLaunched", "1");
        }
        if (data.count > 0) {
            proof.hidden = false;
            proof.textContent =
                data.count === 1
                    ? "1 name already on the wall."
                    : `${data.count} names already on the wall.`;
        }
    } catch (error) {
        showLocalCount();
    }
}

function showLocalCount() {
    const count = readJson("ratedWaitlistUsers").length;
    if (count > 0) {
        proof.hidden = false;
        proof.textContent =
            count === 1
                ? "1 name already on the wall."
                : `${count} names already on the wall.`;
    }
}

form.addEventListener("submit", async event => {
    event.preventDefault();
    hideError();

    const username = document.getElementById("username").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const updates = document.getElementById("updatesList").checked;

    if (username.length < 3) {
        showError("Username must be at least 3 characters.");
        return;
    }

    if (!email.includes("@")) {
        showError("Enter a real email.");
        return;
    }

    if (password.length < 8) {
        showError("Password must be at least 8 characters.");
        return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Locking it in…";

    let localSaved = false;
    try {
        await saveLocalWaitlist(username, email, password, updates);
        localSaved = true;
    } catch (error) {
        showError(error.message || "Could not save your seat.");
        submitButton.disabled = false;
        submitButton.textContent = "Get on the list";
        return;
    }

    try {
        const response = await fetch(`${API_URL}/waitlist`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username,
                email,
                password,
                updates
            })
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const detail = data.detail;
            const message =
                typeof detail === "string"
                    ? detail
                    : Array.isArray(detail) && detail[0] && detail[0].msg
                    ? detail[0].msg
                    : null;
            if (message && !localSaved) {
                showError(message);
                submitButton.disabled = false;
                submitButton.textContent = "Get on the list";
                return;
            }
            thankYou(username, email, false);
            return;
        }

        thankYou(data.username, data.email, data.emailSent);
    } catch (error) {
        thankYou(username, email, false);
    }
});

loadCount();
