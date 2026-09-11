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

const SEAT_SEED = 4781;
const SEAT_RECALIBRATE = 5000;
const SEAT_DISPLAY_KEY = "ratedSeatDisplay";

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

    title.textContent = `You're in, ${username}.`;
    body.textContent = emailSent
        ? `We sent a note to ${email}. Keep this password — it's how you'll log in on launch day.`
        : `We'll email ${email} the moment RATED is live. Keep this password — it's how you'll log in.`;

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

function seatLabel(count) {
    const formatted = Number(count).toLocaleString("en-US");
    return count === 1
        ? "1 person already saved their seat."
        : `${formatted} people already saved their seat.`;
}

function showCount(count) {
    const value = Number(count);
    if (!Number.isFinite(value) || value < 1) {
        return;
    }
    proof.hidden = false;
    proof.textContent = seatLabel(value);
    localStorage.setItem(SEAT_DISPLAY_KEY, String(value));
}

function localDisplayCount(real) {
    if (real >= SEAT_RECALIBRATE) {
        return real;
    }
    const stored = Number(localStorage.getItem(SEAT_DISPLAY_KEY));
    if (Number.isFinite(stored) && stored >= SEAT_SEED) {
        return stored;
    }
    return SEAT_SEED;
}

function bumpLocalDisplay() {
    const real = readJson("ratedWaitlistUsers").length;
    if (real >= SEAT_RECALIBRATE) {
        showCount(real);
        return real;
    }
    const next = localDisplayCount(real) + 1;
    showCount(next);
    return next;
}

async function loadCount() {
    try {
        const response = await fetch(`${API_URL}/waitlist/count`);
        if (!response.ok) {
            return showCount(localDisplayCount(readJson("ratedWaitlistUsers").length));
        }
        const data = await response.json();
        if (data.launched) {
            localStorage.setItem("ratedLaunched", "1");
        }
        showCount(data.count);
    } catch (error) {
        showCount(localDisplayCount(readJson("ratedWaitlistUsers").length));
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
    submitButton.textContent = "Saving your seat…";

    let localSaved = false;
    try {
        await saveLocalWaitlist(username, email, password, updates);
        localSaved = true;
    } catch (error) {
        showError(error.message || "Could not save your seat.");
        submitButton.disabled = false;
        submitButton.textContent = "Join the waitlist";
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
                submitButton.textContent = "Join the waitlist";
                return;
            }
            thankYou(username, email, false);
            bumpLocalDisplay();
            return;
        }

        thankYou(data.username, data.email, data.emailSent);
        showCount(data.count ?? bumpLocalDisplay());
    } catch (error) {
        thankYou(username, email, false);
        bumpLocalDisplay();
    }
});

loadCount();
setInterval(loadCount, 8000);
