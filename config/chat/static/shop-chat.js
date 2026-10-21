(() => {
    const guestOrderPrompt = document.getElementById("guest-order-prompt");
    if (guestOrderPrompt) {
        const promptKey = `guest-order-prompt-${guestOrderPrompt.dataset.orderReference}`;
        if (!sessionStorage.getItem(promptKey)) {
            guestOrderPrompt.showModal();
            sessionStorage.setItem(promptKey, "shown");
        }
        guestOrderPrompt
            .querySelectorAll("[data-close-guest-prompt]")
            .forEach((button) => {
                button.addEventListener("click", () => guestOrderPrompt.close());
            });
    }

    const widget = document.querySelector(".shop-chat-widget");
    if (!widget) return;

    const launcher = document.getElementById("shop-chat-launcher");
    const panel = document.getElementById("shop-chat-panel");
    const closeButton = widget.querySelector(".shop-chat-close");
    const messages = document.getElementById("shop-chat-messages");
    const chatForm = document.getElementById("shop-chat-form");
    const input = document.getElementById("shop-chat-input");
    const sendButton = chatForm?.querySelector('button[type="submit"]');
    const csrfToken = document.querySelector(
        '#shop-chat-csrf input[name="csrfmiddlewaretoken"]'
    )?.value;
    let isSending = false;

    function setOpen(isOpen) {
        widget.classList.toggle("is-open", isOpen);
        launcher.setAttribute("aria-expanded", String(isOpen));
        launcher.setAttribute(
            "aria-label",
            isOpen ? "Close shopping assistant" : "Open shopping assistant"
        );
        panel.setAttribute("aria-hidden", String(!isOpen));
        panel.inert = !isOpen;

        if (isOpen && input) {
            input.focus();
        } else {
            launcher.focus();
        }
    }

    function addMessage(text, sender, isError = false) {
        const message = document.createElement("div");
        message.className = `shop-chat-message ${sender}`;
        if (isError) message.classList.add("is-error");
        const productOrOrdersPath = /\/products\/[a-z0-9-]+\/|\/orders\//g;
        let lastIndex = 0;
        for (const match of text.matchAll(productOrOrdersPath)) {
            message.appendChild(
                document.createTextNode(text.slice(lastIndex, match.index))
            );
            const link = document.createElement("a");
            link.href = match[0];
            link.textContent = match[0].startsWith("/products/")
                ? "View product and add to bag"
                : "View all orders";
            message.appendChild(link);
            lastIndex = match.index + match[0].length;
        }
        message.appendChild(document.createTextNode(text.slice(lastIndex)));
        messages.appendChild(message);
        messages.scrollTop = messages.scrollHeight;
        return message;
    }

    launcher.addEventListener("click", () => {
        setOpen(!widget.classList.contains("is-open"));
    });

    closeButton.addEventListener("click", () => setOpen(false));

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && widget.classList.contains("is-open")) {
            setOpen(false);
        }
    });

    if (!chatForm) return;

    chatForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const question = input.value.trim();
        if (!question || isSending) return;

        if (!csrfToken) {
            addMessage(
                "Could not verify this request. Refresh the page and try again.",
                "assistant",
                true
            );
            return;
        }

        isSending = true;
        input.disabled = true;
        sendButton.disabled = true;
        addMessage(question, "user");
        const loadingMessage = addMessage("Thinking…", "assistant");
        input.value = "";

        try {
            const response = await fetch(widget.dataset.chatUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken
                },
                credentials: "same-origin",
                body: JSON.stringify({ question })
            });
            let data;
            try {
                data = await response.json();
            } catch {
                throw new Error(
                    `The server returned an unexpected response (${response.status}).`
                );
            }

            loadingMessage.remove();
            if (!response.ok) {
                throw new Error(data.error || `Request failed (${response.status}).`);
            }
            if (typeof data.answer !== "string" || !data.answer.trim()) {
                throw new Error("The assistant returned an empty response.");
            }
            addMessage(data.answer, "assistant");
        } catch (error) {
            loadingMessage.remove();
            addMessage(
                error.message === "Failed to fetch"
                    ? "Could not connect to the shop assistant. Please try again."
                    : error.message,
                "assistant",
                true
            );
        } finally {
            isSending = false;
            input.disabled = false;
            sendButton.disabled = false;
            input.focus();
        }
    });
})();
