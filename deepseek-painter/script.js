let conversationHistory = [];

function appendMessage(role, content) {
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;
    messageDiv.textContent = content;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();
    
    if (!message) return;
    
    // Add user message (unchanged)
    appendMessage('user', message);
    conversationHistory.push({ role: 'user', content: message });
    userInput.value = '';
    
    // Create a PLACEHOLDER bot message div for streaming
    const messagesDiv = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messagesDiv.appendChild(messageDiv);
    let botContent = '';
    
    try {
        const response = await fetch('http://localhost:5000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ messages: conversationHistory })
        });

        if (!response.ok) throw new Error('Network error');

        // Stream processing logic (new code)
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const decodedChunk = decoder.decode(value);
            try {
                const data = JSON.parse(decodedChunk);
                botContent += data.content;
                messageDiv.textContent = botContent; // Update UI incrementally
                messagesDiv.scrollTop = messagesDiv.scrollHeight; // Auto-scroll
            } catch (e) {
                console.error('Error parsing chunk:', e);
            }
        }

        // Finalize conversation history (unchanged)
        conversationHistory.push({ role: 'assistant', content: botContent });
    } catch (error) {
        console.error('Error:', error);
        messageDiv.textContent = 'Sorry, there was an error processing your request.';
    }
}

function clearChat() {
    conversationHistory = [];
    document.getElementById('chat-messages').innerHTML = '';
}

// Handle Enter key for sending message
document.getElementById('user-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});