import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime

from models import CreateRoomRequest, JoinRoomRequest, GuessRequest, GameState
from room_manager import RoomManager
from scraper import scraper
from ollama_client import ollama_client

# Initialize room manager
room_manager = RoomManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("Starting up...")
    
    # Update articles on startup
    scraper.update_articles()
    
    # Start periodic update task
    async def periodic_update():
        while True:
            await asyncio.sleep(int(os.getenv('SCRAPE_INTERVAL', 3600)))
            scraper.update_articles()
    
    asyncio.create_task(periodic_update())
    
    # Wait for Ollama to be ready
    print("Waiting for Ollama...")
    for _ in range(30):  # Try for 30 seconds
        if await ollama_client.is_ready():
            print("Ollama is ready!")
            break
        await asyncio.sleep(1)
    
    yield
    
    # Shutdown
    print("Shutting down...")

app = FastAPI(
    title="News Quiz Game API",
    description="API pour jeu de quiz sur l'actualité avec IA locale",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    ollama_status = await ollama_client.is_ready()
    return {
        "status": "healthy",
        "ollama": "ready" if ollama_status else "not_ready",
        "articles_count": len(scraper.articles),
        "rooms_count": len(room_manager.rooms)
    }

@app.get("/api/news")
async def get_news():
    """Get current news articles"""
    return {
        "articles": scraper.articles,
        "last_update": scraper.last_update
    }

@app.post("/api/rooms/create")
async def create_room(request: CreateRoomRequest):
    """Create a new game room"""
    room, player_id = room_manager.create_room(request.player_name)
    return {
        "room": room,
        "player_id": player_id
    }

@app.post("/api/rooms/join")
async def join_room(request: JoinRoomRequest):
    """Join an existing room"""
    result = room_manager.join_room(request.code, request.player_name)
    
    if not result:
        raise HTTPException(status_code=404, detail="Room not found or game already started")
    
    room, player_id = result
    return {
        "room": room,
        "player_id": player_id
    }

@app.get("/api/rooms/{code}")
async def get_room(code: str):
    """Get room state"""
    room = room_manager.get_room(code)
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return room

@app.post("/api/rooms/{code}/start")
async def start_game(code: str, player_id: str):
    """Start the game"""
    room = room_manager.get_room(code)
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.host_id != player_id:
        raise HTTPException(status_code=403, detail="Only host can start the game")
    
    # Get random article
    article = scraper.get_random_article()
    if not article:
        raise HTTPException(status_code=503, detail="No articles available")
    
    # Get article content
    content = scraper.get_article_content(article['url'])
    
    # Generate questions with Ollama
    quiz_data = await ollama_client.generate_questions(article['title'], content)
    
    if not quiz_data:
        raise HTTPException(status_code=503, detail="Failed to generate questions")
    
    # Update room with game data
    room = room_manager.start_game(code)
    room.article = {
        "title": article['title'],
        "url": article['url'],
        "source": article['source']
    }
    room.current_question = {
        "id": 1,
        "text": quiz_data['questions'][0]['text'],
        "article_title": quiz_data['title'],
        "article_url": article['url'],
        "hints": quiz_data['hints'],
        "answer_keywords": quiz_data['answer_keywords'],
        "difficulty": 1
    }
    room.quiz_data = quiz_data
    
    return room

@app.post("/api/rooms/{code}/guess")
async def submit_guess(code: str, request: GuessRequest):
    """Submit a guess"""
    room = room_manager.get_room(code)
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.status != "playing":
        raise HTTPException(status_code=400, detail="Game not in progress")
    
    # Check answer with Ollama
    is_correct, feedback = await ollama_client.check_answer(
        request.guess,
        room.quiz_data['answer_keywords'],
        room.quiz_data['full_answer']
    )
    
    # Update score if correct
    if is_correct:
        room_manager.submit_guess(code, request.player_id, request.guess, True)
    
    return {
        "correct": is_correct,
        "feedback": feedback,
        "player": next((p for p in room.players if p.id == request.player_id), None)
    }

@app.get("/api/rooms/{code}/leaderboard")
async def get_leaderboard(code: str):
    """Get game leaderboard"""
    leaderboard = room_manager.get_leaderboard(code)
    return {
        "leaderboard": leaderboard
    }

@app.post("/api/rooms/{code}/leave")
async def leave_room(code: str, player_id: str):
    """Leave a room"""
    room_manager.leave_room(code, player_id)
    return {"status": "success"}

# Static files (for serving frontend)
if os.path.exists("/app/static"):
    app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)