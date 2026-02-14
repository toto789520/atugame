import random
import string
from typing import Dict, List, Optional
from datetime import datetime
from models import Room, Player, Question


class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, Room] = {}
    
    def generate_code(self, length: int = 6) -> str:
        """Generate a random room code"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    def create_room(self, host_name: str) -> tuple[Room, str]:
        """Create a new room with the given host"""
        code = self.generate_code()
        
        # Ensure unique code
        while code in self.rooms:
            code = self.generate_code()
        
        player_id = self.generate_code(8)
        host = Player(
            id=player_id,
            name=host_name,
            is_host=True
        )
        
        room = Room(
            code=code,
            host_id=player_id,
            players=[host],
            created_at=datetime.now()
        )
        
        self.rooms[code] = room
        return room, player_id
    
    def get_room(self, code: str) -> Optional[Room]:
        """Get a room by code"""
        return self.rooms.get(code.upper())
    
    def join_room(self, code: str, player_name: str) -> Optional[tuple[Room, str]]:
        """Add a player to a room"""
        room = self.get_room(code)
        if not room:
            return None
        
        if room.status != "waiting":
            return None
        
        if len(room.players) >= 10:
            return None
        
        player_id = self.generate_code(8)
        player = Player(
            id=player_id,
            name=player_name
        )
        
        room.players.append(player)
        return room, player_id
    
    def leave_room(self, code: str, player_id: str):
        """Remove a player from a room"""
        room = self.get_room(code)
        if not room:
            return
        
        room.players = [p for p in room.players if p.id != player_id]
        
        # If room is empty, remove it
        if not room.players:
            del self.rooms[code]
        # If host left, assign new host
        elif player_id == room.host_id and room.players:
            room.host_id = room.players[0].id
            room.players[0].is_host = True
    
    def start_game(self, code: str) -> Optional[Room]:
        """Start the game"""
        room = self.get_room(code)
        if not room or len(room.players) < 1:
            return None
        
        room.status = "playing"
        room.current_round = 1
        return room
    
    def submit_guess(self, code: str, player_id: str, guess: str, is_correct: bool):
        """Submit a guess and update scores"""
        room = self.get_room(code)
        if not room:
            return
        
        for player in room.players:
            if player.id == player_id and is_correct:
                # Points based on how fast they answered
                player.score += 100
    
    def next_round(self, code: str) -> Optional[Room]:
        """Move to next round"""
        room = self.get_room(code)
        if not room:
            return None
        
        room.current_round += 1
        
        if room.current_round > room.max_rounds:
            room.status = "finished"
        
        return room
    
    def get_leaderboard(self, code: str) -> List[Player]:
        """Get sorted leaderboard"""
        room = self.get_room(code)
        if not room:
            return []
        
        return sorted(room.players, key=lambda p: p.score, reverse=True)