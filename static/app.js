const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("chat-messages");
const sendButton = document.getElementById("send-button");
const statusText = document.getElementById("status");

const base = document.body.dataset.base || "";

function addMessage(role, content) {
    const message = document.createElement("div");

    message.classList.add("message", role);
    message.textContent = content;

    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
}

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
