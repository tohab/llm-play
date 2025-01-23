let conversationHistory = [];

function appendMessage(role, content) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    
    // Game response formatting
    if (role === 'bot' && content.includes('{')) {
        try {
            const data = JSON.parse(content);
            messageDiv.innerHTML = `
                <div class="game-response">
                    <div class="percentage">Similarity: ${data.percentage}%</div>
                    <div class="hint">Hint: ${data.hint}</div>
                </div>
            `;
        } catch(e) {
            messageDiv.textContent = content;
        }
    } else {
        messageDiv.textContent = content;
    }
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();
    
    if (!message) return;
    
    // Add user message
    appendMessage('user', message);
    conversationHistory.push({ role: 'user', content: message });
    userInput.value = '';
    
    // Create bot message container
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messagesDiv.appendChild(messageDiv);

    try {
        const response = await fetch('http://localhost:5000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: conversationHistory })
        });

        const data = await response.json();
        const botContent = data.content;
        
        // Update with parsed game data
        messageDiv.innerHTML = `
            <div class="game-response">
                <div class="percentage">Similarity: ${JSON.parse(botContent).percentage}%</div>
                <div class="hint">Hint: ${JSON.parse(botContent).hint}</div>
            </div>
        `;
        
        conversationHistory.push({ role: 'assistant', content: botContent });

    } catch (error) {
        console.error('Error:', error);
        messageDiv.textContent = 'Error processing your guess.';
    }
}

function clearChat() {
    conversationHistory = [];
    document.getElementById('chat-messages').innerHTML = '';
    appendMessage('bot', "New game started! Guess the secret word!");
}

// Preserve original event listeners
document.addEventListener('DOMContentLoaded', () => {
    appendMessage('bot', "Welcome to the Word Guessing Game! Try to guess my secret word!");
});

document.getElementById('user-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});