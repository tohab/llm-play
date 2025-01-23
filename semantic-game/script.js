let conversationHistory = [];
let currentSeedWord = '';
let currentDifficulty = 'medium';

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('start-game-button').addEventListener('click', startGame);
    document.getElementById('guess-button').addEventListener('click', handleGuess);
    document.getElementById('give-up-button').addEventListener('click', handleGiveUp);
    document.getElementById('guess-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') handleGuess();
    });
});

async function startGame() {
    const seedInput = document.getElementById('seed-input').value.trim();
    const difficultySelect = document.getElementById('difficulty-select').value;
    
    if (!seedInput) {
        alert('Please enter a seed word to start the game');
        return;
    }

    const startButton = document.getElementById('start-game-button');
    startButton.disabled = true;
    startButton.textContent = 'Starting...';

    try {
        const response = await fetch('http://localhost:5000/start-game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                seed_word: seedInput,
                difficulty: difficultySelect
            })
        });

        if (!response.ok) throw new Error('Failed to start game');

        currentSeedWord = seedInput;
        currentDifficulty = difficultySelect;
        document.querySelector('.setup-controls').style.display = 'none';
        document.querySelector('.game-controls').style.display = 'flex';
        
        clearChat();
        appendMessage('bot', `Game started! Seed word: ${seedInput}, Difficulty: ${difficultySelect}`);
        appendMessage('bot', "Try to guess the word related to the seed!");

    } catch (error) {
        console.error('Error:', error);
        appendMessage('bot', "Error starting game. Please try again.");
    } finally {
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
        
        appendMessage('bot', botContent);
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
    
    requestAnimationFrame(() => {
        messagesDiv.scrollTo({
            top: messagesDiv.scrollHeight,
            behavior: 'smooth'
        });
    });
}