import aiohttp
import json
from typing import Optional, Dict, List
import os


class OllamaClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv('OLLAMA_URL', 'http://ollama:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3')
    
    async def generate_questions(self, article_title: str, article_content: str) -> Optional[Dict]:
        """Generate questions from article using Ollama"""
        prompt = f"""Tu es un générateur de quiz pour un jeu sur l'actualité.

Article : {article_title}

Contexte : {article_content[:1000]}

Génère un jeu de questions/réponses au format JSON suivant :
{{
  "title": "Titre de l'article sans révéler le sujet principal",
  "questions": [
    {{
      "id": 1,
      "text": "Question 1 progressive",
      "difficulty": 1
    }},
    {{
      "id": 2,
      "text": "Question 2 plus précise",
      "difficulty": 2
    }},
    {{
      "id": 3,
      "text": "Question 3 encore plus précise",
      "difficulty": 3
    }}
  ],
  "hints": [
    "Indice 1 vague",
    "Indice 2 plus précis",
    "Indice 3 très précis"
  ],
  "answer_keywords": ["mot-clé1", "mot-clé2", "mot-clé3"],
  "full_answer": "Description complète de la réponse"
}}

Règles :
- Les questions doivent devenir progressivement plus faciles
- Ne révèle pas immédiatement le sujet
- Les mots-clés doivent permettre de vérifier une réponse correcte
- Réponds UNIQUEMENT avec le JSON, pas de texte avant/après
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data.get('response', '')
                        
                        # Extract JSON from response
                        try:
                            # Try to find JSON in response
                            start = response_text.find('{')
                            end = response_text.rfind('}') + 1
                            if start != -1 and end > start:
                                json_str = response_text[start:end]
                                return json.loads(json_str)
                        except json.JSONDecodeError:
                            print(f"Failed to parse JSON: {response_text}")
                            return None
                    else:
                        print(f"Ollama error: {response.status}")
                        return None
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return None
    
    async def check_answer(self, user_guess: str, keywords: List[str], full_answer: str) -> tuple[bool, str]:
        """Check if answer is correct using AI"""
        prompt = f"""Tu es un vérificateur de réponses pour un jeu.

Réponse attendue (mots-clés) : {', '.join(keywords)}
Description complète : {full_answer}
Réponse de l'utilisateur : {user_guess}

Détermine si la réponse de l'utilisateur est correcte ou proche de la réponse attendue.
Sois tolérant avec les fautes d'orthographe et les formulations différentes mais correctes.

Réponds UNIQUEMENT avec ce format JSON :
{{
  "correct": true/false,
  "feedback": "Message de feedback pour l'utilisateur"
}}
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data.get('response', '')
                        
                        try:
                            start = response_text.find('{')
                            end = response_text.rfind('}') + 1
                            if start != -1 and end > start:
                                json_str = response_text[start:end]
                                result = json.loads(json_str)
                                return result.get('correct', False), result.get('feedback', '')
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"Error checking answer: {e}")
        
        # Fallback: simple keyword matching
        guess_lower = user_guess.lower()
        for keyword in keywords:
            if keyword.lower() in guess_lower:
                return True, "Bonne réponse !"
        
        return False, "Ce n'est pas la bonne réponse, essayez encore !"
    
    async def is_ready(self) -> bool:
        """Check if Ollama is ready"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except:
            return False


# Singleton instance
ollama_client = OllamaClient()