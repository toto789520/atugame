import aiohttp
import json
from typing import Optional, Dict, List, Tuple
import os

class OllamaClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv('OLLAMA_URL', 'http://ollama:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'llama3')

    async def generate_questions(self, article_title: str, article_content: str) -> Optional[Dict]:
        """Génère des questions avec un prompt strict pour forcer le JSON"""
        
        # Définition du schéma JSON attendu pour guider l'IA
        json_schema = {
            "title": "Titre court du sujet",
            "questions": [
                {"id": 1, "text": "Indice vague (domaine général)", "difficulty": 1},
                {"id": 2, "text": "Indice moyen (contexte)", "difficulty": 2},
                {"id": 3, "text": "Indice précis (détail clé sans nommer)", "difficulty": 3}
            ],
            "hints": ["Indice 1", "Indice 2", "Indice 3"],
            "answer_keywords": ["mot1", "mot2", "mot3"],
            "full_answer": "La réponse exacte"
        }

        prompt = f"""[INST] <<SYS>>
Tu es un moteur de génération de quiz de haute précision. Tu dois extraire l'essence d'un article pour en faire un jeu de devinettes.
Tu ne parles QUE le JSON. Ne salue pas, ne fais pas de commentaires.
<</SYS>>

ARTICLE À ANALYSER :
Titre : {article_title}
Contenu : {article_content[:800]}

CONSIGNES STRICTES :
1. Génère 3 questions progressives (Facile -> Moyen -> Difficile).
2. Interdiction formelle de citer le titre ou la réponse exacte dans les questions.
3. La difficulté 1 doit être très évasive (le secteur).
4. La difficulté 3 doit être très spécifique.
5. La réponse doit être un JSON valide respectant SCRUPULEUSEMENT cette structure :
{json.dumps(json_schema, indent=2)}

RÉPONSE JSON : [/INST]"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json", # Option Ollama pour forcer le mode JSON
                        "options": {
                            "temperature": 0.2, # Réduit pour plus de stabilité
                            "num_predict": 800,
                            "top_p": 0.9
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._safe_parse_json(data.get('response', ''), article_title)
                    return self._fallback_questions(article_title)
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return self._fallback_questions(article_title)

    async def check_answer(self, user_guess: str, keywords: List[str], full_answer: str) -> Tuple[bool, str]:
        """Vérifie la réponse avec un prompt binaire strict"""
        
        prompt = f"""[INST] <<SYS>>
Tu es un arbitre de jeu de société. Ta mission est de comparer la réponse d'un joueur avec la solution.
Réponds EXCLUSIVEMENT sous forme de JSON.
<</SYS>>

SOLUTION ATTENDUE : {full_answer}
MOTS-CLÉS : {', '.join(keywords)}
RÉPONSE DU JOUEUR : {user_guess}

RÈGLES D'ARBITRAGE :
1. Si le joueur a compris l'idée principale, "correct" est true.
2. Sois indulgent sur l'orthographe et les synonymes.
3. Si le joueur est totalement à côté, "correct" est false.
4. Donne un feedback court et encourageant (maximum 15 mots).

STRUCTURE JSON :
{{
  "correct": boolean,
  "feedback": "string"
}}

RÉPONSE JSON : [/INST]"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.1} # Très bas pour la précision
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = json.loads(data.get('response', '{}'))
                        return result.get('correct', False), result.get('feedback', 'Réponse enregistrée.')
        except Exception:
            pass
        
        # Fallback simplifié
        return (full_answer.lower() in user_guess.lower()), "Vérification manuelle effectuée."

    def _safe_parse_json(self, text: str, title: str) -> Dict:
        """Nettoie et parse le JSON retourné par l'IA"""
        try:
            # Nettoyage des balises markdown si présentes
            text = text.replace('```json', '').replace('```', '').strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return self._fallback_questions(title)

    def _fallback_questions(self, article_title: str) -> Dict:
        """Fallback robuste en cas d'erreur de l'IA"""
        return {
            "title": "Article d'actualité",
            "questions": [
                {"id": 1, "text": "De quel domaine général parle cet article ?", "difficulty": 1},
                {"id": 2, "text": "Quel événement est décrit dans ce texte ?", "difficulty": 2},
                {"id": 3, "text": "Pouvez-vous identifier le sujet précis ?", "difficulty": 3}
            ],
            "hints": ["C'est une info récente", "Regardez les thèmes principaux", "Le sujet est lié à l'actualité"],
            "answer_keywords": article_title.lower().split(),
            "full_answer": article_title
        }
