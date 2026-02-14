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
    
    # Set loading state for all players
    room_manager.set_loading(code, True, "Génération des questions avec l'IA...")
    
    try:
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
        room.quiz_data = quiz_data
        
        # Set first question
        await update_question_for_round(code, 1)
        
    finally:
        # Remove loading state
        room_manager.set_loading(code, False)
    
    return room

async def update_question_for_round(code: str, round_num: int):
    """Update the current question for a specific round"""
    room = room_manager.get_room(code)
    if not room or not room.quiz_data:
        return
    
    questions = room.quiz_data.get('questions', [])
    hints = room.quiz_data.get('hints', [])
    
    if round_num <= len(questions):
        question_data = questions[round_num - 1]
        
        # Get hints for this round (distribute hints across rounds)
        round_hints = []
        hints_per_round = max(1, len(hints) // room.max_rounds)
        start_idx = (round_num - 1) * hints_per_round
        end_idx = min(start_idx + hints_per_round, len(hints))
        round_hints = hints[start_idx:end_idx]
        
        room.current_question = {
            "id": round_num,
            "text": question_data['text'],
            "article_title": room.quiz_data.get('title', 'Article'),
            "article_url": room.article['url'],
            "hints": round_hints,
            "answer_keywords": room.quiz_data.get('answer_keywords', []),
            "difficulty": round_num
        }
        room.current_round = round_num

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
        room.quiz_data.get('answer_keywords', []),
        room.quiz_data.get('full_answer', '')
    )
    
    # Update player progress
    result = room_manager.submit_guess(code, request.player_id, request.guess, is_correct)
    
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    # If correct and not finished, update question for this player's round
    if is_correct and not result.get("finished"):
        player = next((p for p in room.players if p.id == request.player_id), None)
        if player:
            # Update global question to match player's round (for simplicity)
            await update_question_for_round(code, player.current_round)
    
    # Check if all players finished
    if room_manager.check_all_finished(code):
        room.status = "finished"
    
    return {
        "correct": is_correct,
        "feedback": feedback,
        "score": result.get("score", 0),
        "current_round": result.get("current_round", 1),
        "finished": result.get("finished", False),
        "player": next((p for p in room.players if p.id == request.player_id), None)
    }

@app.post("/api/rooms/{code}/next-round")
async def next_round(code: str, player_id: str):
    """Move to next round (for a specific player)"""
    room = room_manager.get_room(code)
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    player = next((p for p in room.players if p.id == player_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Update question for this player's next round
    await update_question_for_round(code, player.current_round)
    
    return room

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