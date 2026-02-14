from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Player(BaseModel):
    id: str
    name: str
    score: int = 0
    is_host: bool = False
    connected: bool = True


class Question(BaseModel):
    id: int
    text: str
    article_title: str
    article_url: str
    hints: List[str]
    answer_keywords: List[str]
    difficulty: int = 1


class Room(BaseModel):
    code: str
    host_id: str
    players: List[Player] = []
    status: str = "waiting"  # waiting, playing, finished
    current_question: Optional[Question] = None
    current_round: int = 0
    max_rounds: int = 5
    created_at: datetime = None
    article: dict = None


class GuessRequest(BaseModel):
    player_id: str
    guess: str


class CreateRoomRequest(BaseModel):
    player_name: str


class JoinRoomRequest(BaseModel):
    code: str
    player_name: str


class GameState(BaseModel):
    room_code: str
    status: str
    players: List[Player]
    current_question: Optional[Question]
    current_round: int
    max_rounds: int
    time_remaining: Optional[int]