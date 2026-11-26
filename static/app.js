const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("chat-messages");
const sendButton = document.getElementById("send-button");
const statusText = document.getElementById("status");

const base = document.body.dataset.base || "";
const SESSION_KEY = "viikko5.chat.session_id";


// Generate or retrieve the browser's session ID
function getSessionId() {
    let id = localStorage.getItem(SESSION_KEY);

    if (!id) {
        const bytes = new Uint8Array(16);
        crypto.getRandomValues(bytes);

        id = Array.from(bytes, byte =>
            byte.toString(16).padStart(2, "0")
        ).join("");

        localStorage.setItem(SESSION_KEY, id);
    }

    return id;
}

const sessionId = getSessionId();


// Display a message in the chat window
function addMessage(role, content) {
    const message = document.createElement("div");

    message.classList.add("message", role);
    message.textContent = content;

    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
}


// Retrieve previous messages
async function loadHistory() {
    sendButton.disabled = true;
    statusText.textContent = "Loading conversation...";

    try {
        const response = await fetch(
            `${base}/api/history/${encodeURIComponent(sessionId)}`,
            { cache: "no-store" }
        );

        if (!response.ok) {
            throw new Error("Failed to load history");
        }

        const history = await response.json();

        if (history.length > 0) {
            messages.replaceChildren();

            for (const message of history) {
                addMessage(message.role, message.content);
            }
        }

        statusText.textContent = "";
        sendButton.disabled = false;

    } catch (error) {
        statusText.textContent =
            "Failed to load conversation. Refresh to retry.";
        console.error(error);
    }
}


// Send a new message
form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = input.value.trim();

    if (!message || sendButton.disabled) {
        return;
    }

    addMessage("user", message);

    input.value = "";
    sendButton.disabled = true;
    statusText.textContent = "Generating response...";

    try {
        const response = await fetch(`${base}/api/chat`, {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                session_id: sessionId,
                message: message
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Request failed");
        }

        addMessage("assistant", data.reply);

    } catch (error) {
        addMessage("error", error.message);

    } finally {
        sendButton.disabled = false;
        statusText.textContent = "";
        input.focus();
    }
});


// Load conversation when the page opens
loadHistory();
