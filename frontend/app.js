// Configuration
const API_URL = window.ENV?.API_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

// State
let currentRoom = null;
let playerId = null;
let currentQuestion = null;
let gameState = null;
let pollingInterval = null;
let isSubmitting = false;

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

function showGlobalLoading(message = 'Chargement...') {
    // Afficher un overlay de chargement global
    let globalLoader = document.getElementById('global-loader');
    if (!globalLoader) {
        globalLoader = document.createElement('div');
        globalLoader.id = 'global-loader';
        globalLoader.className = 'global-loader';
        globalLoader.innerHTML = `
            <div class="loader-content">
                <div class="spinner-large"></div>
                <p class="loader-message">${message}</p>
            </div>
        `;
        document.body.appendChild(globalLoader);
    } else {
        globalLoader.querySelector('.loader-message').textContent = message;
        globalLoader.classList.remove('hidden');
    }
}

function hideGlobalLoading() {
    const globalLoader = document.getElementById('global-loader');
    if (globalLoader) {
        globalLoader.classList.add('hidden');
    }
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
        hideLoading();
        showGame();
    } catch (error) {
        showToast(error.message, 'error');
        hideLoading();
    }
}

async function submitGuess(guess) {
    if (!guess.trim() || isSubmitting) return;
    
    isSubmitting = true;
    const submitBtn = document.getElementById('btn-submit-answer');
    const answerInput = document.getElementById('answer-input');
    
    // Afficher le chargement sur le bouton
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-small"></span> Vérification...';
    
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
        
        // Mettre à jour le score
        document.getElementById('current-score').textContent = data.score;
        
        if (data.correct) {
            answerInput.value = '';
            
            if (data.finished) {
                // Le joueur a terminé toutes les questions
                showToast('Félicitations ! Tu as terminé toutes les questions !', 'success');
                submitBtn.innerHTML = '✓ Terminé';
                answerInput.disabled = true;
                
                // Vérifier si tous les joueurs ont fini
                await checkAllPlayersFinished();
            } else {
                // Passer à la question suivante
                submitBtn.innerHTML = 'Question suivante →';
                submitBtn.onclick = () => nextQuestion(data.current_round);
                answerInput.disabled = true;
                
                showToast(`Bonne réponse ! Question ${data.current_round}/${currentRoom.max_rounds}`, 'success');
            }
        } else {
            // Réponse incorrecte - permettre de réessayer
            submitBtn.disabled = false;
            submitBtn.textContent = 'Valider';
            answerInput.focus();
        }
    } catch (error) {
        showToast(error.message, 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Valider';
    } finally {
        isSubmitting = false;
    }
}

async function nextQuestion(roundNum) {
    // Passer à la question suivante
    const submitBtn = document.getElementById('btn-submit-answer');
    const answerInput = document.getElementById('answer-input');
    const feedback = document.getElementById('feedback');
    
    showLoading('Chargement de la question suivante...');
    
    try {
        // Rafraîchir la room pour obtenir la nouvelle question
        await refreshRoom();
        
        // Réinitialiser l'interface
        feedback.classList.add('hidden');
        answerInput.disabled = false;
        answerInput.value = '';
        answerInput.focus();
        
        submitBtn.innerHTML = 'Valider';
        submitBtn.onclick = () => {
            const input = document.getElementById('answer-input');
            submitGuess(input.value);
        };
        
        // Mettre à jour l'affichage
        updateGameDisplay();
        
    } catch (error) {
        showToast('Erreur lors du chargement de la question', 'error');
    } finally {
        hideLoading();
    }
}

async function checkAllPlayersFinished() {
    try {
        const data = await apiCall(`/rooms/${currentRoom.code}`);
        
        // Vérifier si tous les joueurs ont terminé
        const allFinished = data.players.every(p => p.has_finished);
        
        if (allFinished || data.status === 'finished') {
            setTimeout(() => {
                showResults();
            }, 3000);
        } else {
            showToast('En attente des autres joueurs...', 'info');
            // Continuer le polling pour voir quand la partie finit
        }
    } catch (error) {
        console.error('Error checking players:', error);
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
        
        // Vérifier si l'état de chargement a changé
        if (data.is_loading && !currentRoom.is_loading) {
            showGlobalLoading(data.loading_message || 'Chargement...');
        } else if (!data.is_loading && currentRoom.is_loading) {
            hideGlobalLoading();
        }
        
        currentRoom = data;
        
        if (data.status === 'playing' && screens.lobby.classList.contains('hidden') === false) {
            hideGlobalLoading();
            showGame();
        }
        
        if (data.status === 'finished') {
            hideGlobalLoading();
            showResults();
        }
        
        updateUI();
    } catch (error) {
        console.error('Error refreshing room:', error);
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
        // Afficher un message pour les non-hosts
        const waitingMsg = document.getElementById('waiting-message') || document.createElement('div');
        waitingMsg.id = 'waiting-message';
        waitingMsg.className = 'waiting-message';
        waitingMsg.innerHTML = '<p>⏳ En attente que l\'hôte lance la partie...</p>';
        if (!document.getElementById('waiting-message')) {
            document.querySelector('.lobby-actions').prepend(waitingMsg);
        }
    }
    
    updatePlayersList();
}

function showGame() {
    showScreen('game');
    updateGameDisplay();
}

function updateGameDisplay() {
    if (!currentRoom) return;
    
    const currentPlayer = currentRoom.players.find(p => p.id === playerId);
    if (!currentPlayer) return;
    
    // Afficher la progression du joueur actuel
    const playerRound = currentPlayer.current_round || 1;
    document.getElementById('round-display').textContent = `Question ${Math.min(playerRound, currentRoom.max_rounds)}/${currentRoom.max_rounds}`;
    document.getElementById('current-score').textContent = currentPlayer.score || 0;
    
    if (currentRoom.current_question) {
        document.getElementById('question-text').textContent = currentRoom.current_question.text;
        
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
                setTimeout(showNextHint, 15000); // Show next hint after 15 seconds
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
    
    // Show final leaderboard with progress
    try {
        const data = await apiCall(`/rooms/${currentRoom.code}/leaderboard`);
        const leaderboard = document.getElementById('final-leaderboard');
        leaderboard.innerHTML = '';
        
        data.leaderboard.forEach((player, index) => {
            const li = document.createElement('li');
            
            // Déterminer le statut du joueur
            let statusBadge = '';
            if (player.has_finished) {
                statusBadge = '<span class="status-badge finished">✓ Terminé</span>';
            } else if (player.current_round > 1) {
                statusBadge = `<span class="status-badge in-progress">⏳ Q${player.current_round}/${player.max_rounds}</span>`;
            } else {
                statusBadge = '<span class="status-badge not-started">Pas commencé</span>';
            }
            
            // Barre de progression
            const progressBar = `
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${player.progress_percent}%"></div>
                </div>
            `;
            
            li.innerHTML = `
                <div class="player-info">
                    <span class="rank">${index + 1}</span>
                    <div class="player-details">
                        <span class="player-name">${player.name}</span>
                        ${player.is_host ? '<span class="host-badge">HOST</span>' : ''}
                        ${statusBadge}
                    </div>
                </div>
                <div class="score-info">
                    <span class="score">${player.score} pts</span>
                    ${progressBar}
                </div>
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
    if (!leaderboard) return;
    
    leaderboard.innerHTML = '';
    
    const sortedPlayers = [...currentRoom.players].sort((a, b) => b.score - a.score);
    
    sortedPlayers.forEach((player, index) => {
        const li = document.createElement('li');
        const progress = player.current_round || 1;
        const maxRounds = currentRoom.max_rounds;
        
        li.innerHTML = `
            <span>${index + 1}. ${player.name} ${player.id === playerId ? '(Toi)' : ''}</span>
            <span>${player.score || 0} pts (Q${Math.min(progress, maxRounds)}/${maxRounds})</span>
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