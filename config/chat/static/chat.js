
const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const messages = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const sendButton = document.getElementById("send-button");
const newChatButton = document.getElementById("new-chat");
const sidebar = document.getElementById("sidebar");
const menuButton = document.getElementById("menu-button");

const csrfInput = document.querySelector(
    '#csrf-form input[name="csrfmiddlewaretoken"]'
);

let isSending = false;

function scrollToBottom() {
    const chatArea = document.getElementById("chat-area");
    chatArea.scrollTop = chatArea.scrollHeight;
}

function addMessage(text, sender) {
    const row = document.createElement("div");
    row.className = `message ${sender}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = sender === "user" ? "You" : "✦";

    const content = document.createElement("div");
    content.className = "message-content";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    const productOrOrdersPath = /\/products\/[a-z0-9-]+\/|\/orders\//g;
    let lastIndex = 0;
    for (const match of text.matchAll(productOrOrdersPath)) {
        bubble.appendChild(
            document.createTextNode(text.slice(lastIndex, match.index))
        );
        const link = document.createElement("a");
        link.href = match[0];
        link.textContent = match[0].startsWith("/products/")
            ? "View product and add to bag"
            : "View all orders";
        bubble.appendChild(link);
        lastIndex = match.index + match[0].length;
    }
    bubble.appendChild(document.createTextNode(text.slice(lastIndex)));

    content.appendChild(bubble);

    if (sender === "assistant") {
        row.appendChild(avatar);
        row.appendChild(content);
    } else {
        row.appendChild(content);
        row.appendChild(avatar);
    }

    messages.appendChild(row);
    scrollToBottom();

    return row;
}

function showTyping() {
    const row = document.createElement("div");
    row.className = "message assistant";
    row.id = "typing-indicator";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "✦";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    const dots = document.createElement("div");
    dots.className = "typing";
    dots.setAttribute("aria-label", "AI is responding");

    for (let i = 0; i < 3; i++) {
        dots.appendChild(document.createElement("span"));
    }

    bubble.appendChild(dots);
    row.append(avatar, bubble);
    messages.appendChild(row);

    scrollToBottom();
}

function removeTyping() {
    document.getElementById("typing-indicator")?.remove();
}

async function sendMessage(question) {
    question = question.trim();

    if (!question || isSending) return;

    if (!csrfInput) {
        addMessage(
            "Security token missing. Refresh the page and try again.",
            "assistant"
        );
        return;
    }

    isSending = true;
    sendButton.disabled = true;
    messageInput.disabled = true;
    welcome.hidden = true;

    addMessage(question, "user");
    showTyping();

    try {
        const response = await fetch(chatForm.dataset.chatUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfInput.value
            },
            credentials: "same-origin",
            body: JSON.stringify({ question: question })
        });

        let data;
        try {
            data = await response.json();
        } catch {
            throw new Error(
                `The server returned an unexpected response (${response.status}).`
            );
        }
        removeTyping();

        if (!response.ok) {
            throw new Error(
                data.error || `Request failed (${response.status})`
            );
        }

        if (typeof data.answer !== "string" || !data.answer.trim()) {
            throw new Error("The server returned an invalid response.");
        }

        addMessage(data.answer, "assistant");

    } catch (error) {
        removeTyping();

        addMessage(
            error.message === "Failed to fetch"
                ? "Could not connect to Django. Check that the server is running."
                : `Sorry, something went wrong: ${error.message}`,
            "assistant"
        );
    } finally {
        isSending = false;
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.focus();
    }
}

chatForm.addEventListener("submit", function (event) {
    event.preventDefault();

    const question = messageInput.value;
    if (!question.trim() || isSending) return;

    messageInput.value = "";
    messageInput.style.height = "auto";

    sendMessage(question);
});

messageInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = `${Math.min(this.scrollHeight, 150)}px`;
});

messageInput.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        chatForm.requestSubmit();
    }
});

document.querySelectorAll(".suggestion").forEach((button) => {
    button.addEventListener("click", () => {
        sendMessage(button.dataset.question || "");
    });
});

newChatButton.addEventListener("click", () => {
    if (isSending) return;

    messages.replaceChildren();
    welcome.hidden = false;
    messageInput.value = "";
    messageInput.style.height = "auto";
    sidebar.classList.remove("open");
    messageInput.focus();
});

menuButton.addEventListener("click", () => {
    sidebar.classList.toggle("open");
});
