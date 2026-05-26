const chatContainer = document.getElementById("chatContainer");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

let ws = null;
let isWaiting = false;

function connect() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${location.host}/ws/chat`;

    ws = new WebSocket(url);

    ws.onopen = () => {
        statusDot.classList.add("connected");
        statusText.textContent = "Connected";
        messageInput.disabled = false;
        sendBtn.disabled = false;
        messageInput.focus();
    };

    ws.onmessage = (event) => {
        removeTypingIndicator();
        isWaiting = false;
        messageInput.disabled = false;
        sendBtn.disabled = false;

        const data = JSON.parse(event.data);

        if (data.type === "error") {
            addMessage(data.content, "bot");
            return;
        }

        if (data.type === "triage_complete") {
            addMessage(data.content, "bot");
            renderTriageCard(data.triage, data.patient);
            messageInput.disabled = true;
            sendBtn.disabled = true;
            messageInput.placeholder = "Triage complete";
            return;
        }

        addMessage(data.content, "bot");
    };

    ws.onclose = () => {
        statusDot.classList.remove("connected");
        statusText.textContent = "Disconnected";
        messageInput.disabled = true;
        sendBtn.disabled = true;
        setTimeout(connect, 3000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

function addMessage(content, sender) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = sender === "bot" ? "🏥" : "👤";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = content;

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
    chatContainer.appendChild(msgDiv);
    scrollToBottom();
}

function showTypingIndicator() {
    const div = document.createElement("div");
    div.className = "typing-indicator";
    div.id = "typingIndicator";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "🏥";

    const dots = document.createElement("div");
    dots.className = "typing-dots";
    dots.innerHTML = "<span></span><span></span><span></span>";

    div.appendChild(avatar);
    div.appendChild(dots);
    chatContainer.appendChild(div);
    scrollToBottom();
}

function removeTypingIndicator() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
}

function renderTriageCard(triage, patient) {
    const card = document.createElement("div");
    card.className = "triage-card";

    const urgency = (triage.urgency || "unknown").toLowerCase();
    const urgencyLabel = urgency.charAt(0).toUpperCase() + urgency.slice(1);

    card.innerHTML = `
        <div class="triage-card-header">
            <h3>📋 Triage Summary</h3>
            <span class="urgency-badge ${urgency}">${urgencyLabel}</span>
        </div>
        <div class="triage-grid">
            <div class="triage-field">
                <label>Patient</label>
                <span>${patient.name || "Not provided"}</span>
            </div>
            <div class="triage-field">
                <label>Age</label>
                <span>${patient.age || "Not provided"}</span>
            </div>
            <div class="triage-field">
                <label>Department</label>
                <span>${triage.department || "General Practice"}</span>
            </div>
            <div class="triage-field">
                <label>Urgency</label>
                <span>${urgencyLabel}</span>
            </div>
            <div class="triage-field full-width">
                <label>Chief Complaint</label>
                <span>${triage.chief_complaint || "See summary"}</span>
            </div>
            <div class="triage-field full-width">
                <label>Summary</label>
                <span>${triage.summary || "No summary available"}</span>
            </div>
            ${triage.recommendations ? `
            <div class="triage-field full-width">
                <label>Recommendations</label>
                <span>${triage.recommendations}</span>
            </div>` : ""}
            ${triage.escalation_reason ? `
            <div class="triage-field full-width">
                <label>⚠️ Escalation Reason</label>
                <span>${triage.escalation_reason}</span>
            </div>` : ""}
            ${patient.allergies ? `
            <div class="triage-field">
                <label>Allergies</label>
                <span>${patient.allergies}</span>
            </div>` : ""}
            ${patient.current_medications ? `
            <div class="triage-field">
                <label>Medications</label>
                <span>${patient.current_medications}</span>
            </div>` : ""}
        </div>
    `;

    chatContainer.appendChild(card);
    scrollToBottom();
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    });
}

function sendMessage() {
    const msg = messageInput.value.trim();
    if (!msg || isWaiting || !ws || ws.readyState !== WebSocket.OPEN) return;

    addMessage(msg, "user");
    ws.send(JSON.stringify({ message: msg }));
    messageInput.value = "";
    isWaiting = true;
    messageInput.disabled = true;
    sendBtn.disabled = true;
    showTypingIndicator();
}

sendBtn.addEventListener("click", sendMessage);
messageInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

connect();
