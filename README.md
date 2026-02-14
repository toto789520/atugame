# News Quiz Game - Devinez l'actualité !

Un jeu multijoueur où les participants doivent deviner le sujet d'actualité récent à travers des questions générées par IA locale.

## 🚀 Déploiement Coolify (Recommandé)

### Étape 1 : Créer le projet
1. Connectez-vous à votre instance Coolify
2. Cliquez sur "Create New Project"
3. Nommez-le : `news-quiz-game`
4. Sélectionnez "Docker Compose"

### Étape 2 : Configurer le Docker Compose
Copiez le contenu du fichier `docker-compose.yml` dans Coolify.

### Étape 3 : Variables d'environnement
Dans l'onglet "Environment Variables", ajoutez :

```
# Ports (changez si vous avez des conflits)
FRONTEND_PORT=80
BACKEND_PORT=8000
OLLAMA_PORT=11434

# Configuration
OLLAMA_MODEL=llama3
SCRAPE_INTERVAL=3600
```

### Étape 4 : Déployer
Cliquez sur "Deploy" et attendez que tout soit prêt (environ 5-10 minutes pour télécharger le modèle LLM).

### Étape 5 : Accéder au jeu
- 🎮 **Jeu** : `https://votre-domaine-coolify.com`
- 📚 **API Docs** : `https://votre-domaine-coolify.com:8000/docs`

## 💻 Développement Local

### Prérequis
- Docker & Docker Compose
- 4GB RAM minimum (pour Ollama)
- 10GB espace disque

### Lancer le projet

```bash
# Cloner le repo
git clone <votre-repo>
cd news-quiz-game

# Lancer tous les services
docker-compose up -d

# Attendre le téléchargement du modèle (5-10 min)
docker-compose logs -f ollama

# Accéder au jeu
open http://localhost
```

### Commandes utiles

```bash
# Voir les logs
docker-compose logs -f

# Arrêter
docker-compose down

# Redémarrer uniquement le backend
docker-compose restart backend

# Entrer dans le conteneur Ollama
docker exec -it news-quiz-ollama bash

# Changer de modèle
docker exec news-quiz-ollama ollama pull mistral
```

## 🎮 Comment jouer

1. **Créer une partie** : Cliquez sur "Créer une partie" et entrez votre pseudo
2. **Partager le code** : Un code de 6 caractères est généré (ex: ABC123)
3. **Inviter des amis** : Partagez le code pour qu'ils rejoignent
4. **Lancer** : L'hôte clique sur "Démarrer la partie"
5. **Deviner** : L'IA pose des questions sur un article d'actualité, devinez le sujet !

### Règles
- L'IA génère 3 questions progressives
- Des indices apparaissent toutes les 20 secondes
- Plus vous répondez vite, plus vous gagnez de points
- L'article réel est révélé à la fin

## 🏗️ Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Frontend  │─────▶│   Backend   │─────▶│   Ollama    │
│   (Nginx)   │      │  (FastAPI)  │      │    (IA)     │
└─────────────┘      └─────────────┘      └─────────────┘
                            │
                            ▼
                    ┌─────────────┐
                    │  Scraping   │
                    │  (News API) │
                    └─────────────┘
```

## 📚 Sources d'actualités

- **France** : Le Monde, France Info
- **International** : BBC News, The Guardian

Les articles sont scrapés automatiquement toutes les heures.

## 🔧 Configuration

### Modifier le modèle IA

Dans `.env` ou variables Coolify :
```
OLLAMA_MODEL=mistral  # ou llama2, codellama
```

### Changer la fréquence de scraping
```
SCRAPE_INTERVAL=1800  # 30 minutes (en secondes)
```

### Changer les ports (si conflits)
Créez un fichier `.env` à la racine :
```
# Ports externes (ceux exposés sur votre machine)
FRONTEND_PORT=8080      # Par défaut: 80
BACKEND_PORT=8001       # Par défaut: 8000
OLLAMA_PORT=11435       # Par défaut: 11434
```

Puis relancez :
```bash
docker-compose down
docker-compose up -d
```

💡 **Note** : Les ports internes des conteneurs restent inchangés, seuls les ports exposés changent.

## 🐛 Dépannage

### Ollama ne répond pas
```bash
# Vérifier si Ollama est prêt
curl http://localhost:11434/api/tags

# Redémarrer Ollama
docker-compose restart ollama
```

### Pas d'actualités
```bash
# Forcer le scraping
curl http://localhost:8000/api/news
```

### Le modèle ne charge pas
Attendez 5-10 minutes au premier démarrage. Le modèle fait ~4GB.

## 📝 API Endpoints

- `GET /api/health` - Vérifier l'état du serveur
- `POST /api/rooms/create` - Créer une room
- `POST /api/rooms/join` - Rejoindre une room
- `GET /api/rooms/{code}` - Infos room
- `POST /api/rooms/{code}/start` - Démarrer partie
- `POST /api/rooms/{code}/guess` - Soumettre réponse

Voir la documentation complète : `/docs` (Swagger UI)

## 📄 License

MIT - Fait avec ❤️ pour les amateurs de news