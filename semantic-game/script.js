let conversationHistory = [];
let currentSeedWord = '';
let currentDifficulty = 'medium';

// Initialize game setup controls
document.addEventListener('DOMContentLoaded', () => {
    // Setup event listeners
    document.getElementById('start-game-button').addEventListener('click', startGame);
    document.getElementById('guess-button').addEventListener('click', handleGuess);
    document.getElementById('give-up-button').addEventListener('click', handleGiveUp);
    document.getElementById('guess-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleGuess();
        }
    });
});

async function startGame() {
    const seedInput = document.getElementById('seed-input').value.trim();
    const difficultySelect = document.getElementById('difficulty-select').value;
    
    if (!seedInput) {
        alert('Please enter a seed word to start the game');
        return;
    }

    // Show loading state
    const startButton = document.getElementById('start-game-button');
    startButton.disabled = true;
    startButton.textContent = 'Starting...';

    try {
        // Initialize game with seed word and difficulty
        const response = await fetch('http://localhost:5000/start-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                seed_word: seedInput,
                difficulty: difficultySelect
            })
        });

        if (!response.ok) throw new Error('Failed to start game');

        // Update UI state
        currentSeedWord = seedInput;
        currentDifficulty = difficultySelect;
        document.querySelector('.setup-controls').style.display = 'none';
        document.querySelector('.game-controls').style.display = 'flex';
        
        // Clear chat and start new game
        clearChat();
        appendMessage('bot', `Game started! Seed word: ${seedInput}, Difficulty: ${difficultySelect}`);
        appendMessage('bot', "Try to guess the word related to the seed!");

    } catch (error) {
        console.error('Error:', error);
        appendMessage('bot', "Error starting game. Please try again.");
    } finally {
        // Reset button state
        startButton.disabled = false;
        startButton.textContent = 'Start Game';
    }
}

function handleGuess() {
    const guess = document.getElementById('guess-input').value.trim();
    if (guess) {
        sendGuess(guess);
        document.getElementById('guess-input').value = '';
    }
}

async function sendGuess(guess) {
    appendMessage('user', guess);
    conversationHistory.push({ role: 'user', content: guess });

    try {
        const response = await fetch('http://localhost:5000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                messages: conversationHistory,
                seed_word: currentSeedWord,
                difficulty: currentDifficulty
            })
        });

        const data = await response.json();
        const botContent = data.content;
        
        // Update with parsed game data
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        messageDiv.innerHTML = `
            <div class="game-response">
                <div class="percentage">Similarity: ${JSON.parse(botContent).percentage}%</div>
                <div class="hint">Hint: ${JSON.parse(botContent).hint}</div>
            </div>
        `;
        
        document.getElementById('chat-messages').appendChild(messageDiv);
        conversationHistory.push({ role: 'assistant', content: botContent });

    } catch (error) {
        console.error('Error:', error);
        appendMessage('bot', "Error processing your guess.");
    }
}

function clearChat() {
    conversationHistory = [];
    document.getElementById('chat-messages').innerHTML = '';
}

async function handleGiveUp() {
    if (!confirm("Are you sure you want to give up?")) return;
    
    try {
        const response = await fetch('http://localhost:5000/give-up', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();
        appendMessage('bot', data.message);
        appendMessage('bot', "A new word has been selected. Keep guessing!");
    } catch (error) {
        console.error('Error:', error);
        appendMessage('bot', "Error processing give up request.");
    }
}

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
                    ${data.success ? `<div class="success">${data.success}</div>` : ''}
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
