// Configuration par défaut (développement local)
// Ce fichier sera remplacé par le serveur nginx au démarrage du conteneur
window.ENV = {
    BACKEND_PORT: '8000',
    API_URL: window.location.hostname === 'localhost' ? 'http://localhost:8000' : ''
};