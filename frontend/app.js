// Configuration
const API_URL = window.ENV?.API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

// State
let currentRoom = null;
let playerId = null;
let currentQuestion = null;
let gameState = null;
let pollingInterval = null;

// DOM Elements
const screens = {
    home: document.getElementById('home-screen'),
    create: document.getElementById('create-screen'),
    lobby: document.getElementById('lobby-screen'),
    game: document.getElementById('game-screen'),
    result: document.getElementById('result-screen')
};

const loading = document.getElementById('loading');
const toast = document.getElementById('toast');

// Utility Functions
function showScreen(screenName) {
    Object.values(screens).forEach(s => s.classList.add('hidden'));
    screens[screenName].classList.remove('hidden');
}

function showLoading(text = 'Chargement...') {
    document.getElementById('loading-text').textContent = text;
    loading.classList.remove('hidden');
}

function hideLoading() {
    loading.classList.add('hidden');
}

function showToast(message, type = 'info') {
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// API Functions
async function apiCall(endpoint, options = {}) {
    const response = await fetch(`${API_URL}/api${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Une erreur est survenue');
    }
    
    return response.json();
}

// Room Management
async function createRoom(playerName) {
    showLoading('Création de la partie...');
    
    try {
        const data = await apiCall('/rooms/create', {
            method: 'POST',
            body: JSON.stringify({ player_name: playerName })
        });
        
        currentRoom = data.room;
        playerId = data.player_id;
        
        showLobby();
        startPolling();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function joinRoom(code, playerName) {
    if (!code || !playerName) {
        showToast('Veuillez remplir tous les champs', 'error');
        return;
    }
    
    showLoading('Rejoindre la partie...');
    
    try {
        const data = await apiCall('/rooms/join', {
            method: 'POST',
            body: JSON.stringify({ 
                code: code.toUpperCase(),
                player_name: playerName 
            })
        });
        
        currentRoom = data.room;
        playerId = data.player_id;
        
        showLobby();
        startPolling();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function startGame() {
    showLoading('Préparation de la partie avec l\'IA...');
    
    try {
        const data = await apiCall(`/rooms/${currentRoom.code}/start?player_id=${playerId}`, {
            method: 'POST'
        });
        
        currentRoom = data;
        showGame();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function submitGuess(guess) {
    if (!guess.trim()) return;
    
    try {
        const data = await apiCall(`/rooms/${currentRoom.code}/guess`, {
            method: 'POST',
            body: JSON.stringify({
                player_id: playerId,
                guess: guess
            })
        });
        
        const feedback = document.getElementById('feedback');
        feedback.className = `feedback ${data.correct ? 'success' : 'error'}`;
        feedback.textContent = data.feedback;
        feedback.classList.remove('hidden');
        
        if (data.correct) {
            document.getElementById('current-score').textContent = data.player.score;
            document.getElementById('answer-input').disabled = true;
            document.getElementById('btn-submit-answer').disabled = true;
            
            setTimeout(() => {
                showResults();
            }, 2000);
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function leaveRoom() {
    if (!currentRoom || !playerId) return;
    
    try {
        await apiCall(`/rooms/${currentRoom.code}/leave?player_id=${playerId}`, {
            method: 'POST'
        });
    } catch (error) {
        console.error('Error leaving room:', error);
    }
    
    stopPolling();
    currentRoom = null;
    playerId = null;
    showScreen('home');
}

async function refreshRoom() {
    if (!currentRoom) return;
    
    try {
        const data = await apiCall(`/rooms/${currentRoom.code}`);
        currentRoom = data;
        
        if (data.status === 'playing' && screens.lobby.classList.contains('hidden') === false) {
            showGame();
        }
        
        if (data.status === 'finished') {
            showResults();
        }
        
        updateUI();
    } catch (error) {
        console.error('Error refreshing room:', error);
        showToast('Erreur de connexion', 'error');
    }
}

// UI Updates
function showLobby() {
    showScreen('lobby');
    document.getElementById('lobby-code').textContent = currentRoom.code;
    
    const isHost = currentRoom.host_id === playerId;
    const startBtn = document.getElementById('btn-start-game');
    
    if (isHost) {
        startBtn.classList.remove('hidden');
    } else {
        startBtn.classList.add('hidden');
    }
    
    updatePlayersList();
}

function showGame() {
    showScreen('game');
    
    if (currentRoom.current_question) {
        document.getElementById('question-text').textContent = currentRoom.current_question.text;
        document.getElementById('round-display').textContent = `Question ${currentRoom.current_round}/${currentRoom.max_rounds}`;
        
        // Show hints gradually
        const hintsContainer = document.getElementById('hints-container');
        hintsContainer.innerHTML = '';
        
        if (currentRoom.current_question.hints) {
            showHintsGradually(currentRoom.current_question.hints);
        }
    }
    
    updateLeaderboard();
}

function showHintsGradually(hints) {
    const container = document.getElementById('hints-container');
    let index = 0;
    
    function showNextHint() {
        if (index < hints.length) {
            const hint = document.createElement('div');
            hint.className = 'hint';
            hint.textContent = `💡 ${hints[index]}`;
            container.appendChild(hint);
            index++;
            
            if (index < hints.length) {
                setTimeout(showNextHint, 20000); // Show next hint after 20 seconds
            }
        }
    }
    
    showNextHint();
}

async function showResults() {
    showScreen('result');
    stopPolling();
    
    // Show article
    const articleReveal = document.getElementById('article-reveal');
    if (currentRoom.article) {
        articleReveal.innerHTML = `
            <h4>${currentRoom.article.title}</h4>
            <p>Source : ${currentRoom.article.source}</p>
            <a href="${currentRoom.article.url}" target="_blank">Lire l'article complet →</a>
        `;
    }
    
    // Show final leaderboard
    try {
        const data = await apiCall(`/rooms/${currentRoom.code}/leaderboard`);
        const leaderboard = document.getElementById('final-leaderboard');
        leaderboard.innerHTML = '';
        
        data.leaderboard.forEach((player, index) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <div class="player-info">
                    <span class="rank">${index + 1}</span>
                    <span>${player.name}</span>
                    ${player.is_host ? '<span class="host-badge">HOST</span>' : ''}
                </div>
                <span class="score">${player.score} pts</span>
            `;
            leaderboard.appendChild(li);
        });
    } catch (error) {
        console.error('Error loading leaderboard:', error);
    }
}

function updateUI() {
    if (!currentRoom) return;
    
    if (screens.lobby.classList.contains('hidden') === false) {
        updatePlayersList();
    } else if (screens.game.classList.contains('hidden') === false) {
        updateLeaderboard();
    }
}

function updatePlayersList() {
    const container = document.getElementById('players-container');
    const count = document.getElementById('player-count');
    
    count.textContent = currentRoom.players.length;
    container.innerHTML = '';
    
    currentRoom.players.forEach(player => {
        const li = document.createElement('li');
        li.className = `player-item ${player.is_host ? 'host' : ''}`;
        li.innerHTML = `
            <div class="player-name">
                ${player.name}
                ${player.is_host ? '<span class="host-badge">HOST</span>' : ''}
            </div>
            ${player.id === playerId ? '<span>👤</span>' : ''}
        `;
        container.appendChild(li);
    });
}

function updateLeaderboard() {
    const leaderboard = document.getElementById('game-leaderboard');
    leaderboard.innerHTML = '';
    
    const sortedPlayers = [...currentRoom.players].sort((a, b) => b.score - a.score);
    
    sortedPlayers.forEach((player, index) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span>${index + 1}. ${player.name}</span>
            <span>${player.score} pts</span>
        `;
        leaderboard.appendChild(li);
    });
}

// Polling
function startPolling() {
    stopPolling();
    pollingInterval = setInterval(refreshRoom, 2000);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// Event Listeners
document.getElementById('btn-create').addEventListener('click', () => {
    showScreen('create');
});

document.getElementById('btn-back-home').addEventListener('click', () => {
    showScreen('home');
});

document.getElementById('btn-create-room').addEventListener('click', () => {
    const name = document.getElementById('player-name-create').value.trim();
    if (!name) {
        showToast('Veuillez entrer votre pseudo', 'error');
        return;
    }
    createRoom(name);
});

document.getElementById('btn-join').addEventListener('click', () => {
    const code = document.getElementById('room-code').value.trim();
    const name = document.getElementById('player-name-join').value.trim();
    joinRoom(code, name);
});

document.getElementById('btn-start-game').addEventListener('click', startGame);

document.getElementById('btn-leave-lobby').addEventListener('click', leaveRoom);

document.getElementById('btn-submit-answer').addEventListener('click', () => {
    const input = document.getElementById('answer-input');
    submitGuess(input.value);
});

document.getElementById('answer-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        submitGuess(e.target.value);
    }
});

document.getElementById('btn-copy-code').addEventListener('click', () => {
    navigator.clipboard.writeText(currentRoom.code);
    showToast('Code copié !', 'success');
});

document.getElementById('btn-new-game').addEventListener('click', () => {
    currentRoom = null;
    playerId = null;
    showScreen('home');
});

// Initialize
showScreen('home');

// Check API health on load
apiCall('/health')
    .then(data => {
        if (data.ollama !== 'ready') {
            showToast('L\'IA locale est en cours de démarrage...', 'info');
        }
    })
    .catch(() => {
        showToast('Impossible de contacter le serveur', 'error');
    });