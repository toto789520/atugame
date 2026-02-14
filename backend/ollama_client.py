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
        prompt = f"""Tu es un animateur de jeu télévisé. Tu dois créer un jeu où les joueurs doivent deviner le sujet d'un article d'actualité.

ARTICLE À DEVINER :
Titre: {article_title}
Contenu: {article_content[:800]}

INSTRUCTIONS PRÉCISES :
1. Crée 3 questions qui donnent des indices sur le sujet
2. Les questions doivent être de difficulté PROGRESSIVE (facile → moyen → difficile)
3. NE mentionne JAMAIS le titre exact de l'article dans les questions
4. Les indices doivent faire réfléchir mais pas donner la réponse immédiatement
5. Le joueur doit deviner de QUOI parle l'article (personne, événement, découverte, décision politique, etc.)

Règles strictes :
- Les 3 questions doivent être logiquement liées au même sujet
- Indice 1 = vague (secteur/général), Indice 2 = plus précis, Indice 3 = très précis
- Réponds UNIQUEMENT avec le JSON valide, sans texte avant ou après
- Assure-toi que le JSON est complet et valide

Génère maintenant le JSON pour cet article :"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.8,
                            "num_predict": 600,
                            "num_ctx": 2048,
                            "top_p": 0.9
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data.get('response', '').strip()
                        
                        # Try to parse JSON directly first
                        try:
                            return json.loads(response_text)
                        except json.JSONDecodeError:
                            # Try to find JSON in response
                            start = response_text.find('{')
                            end = response_text.rfind('}') + 1
                            if start != -1 and end > start:
                                json_str = response_text[start:end]
                                return json.loads(json_str)
                            else:
                                print(f"No JSON found in response: {response_text[:200]}")
                                return self._fallback_questions(article_title)
                    else:
                        print(f"Ollama error: {response.status}")
                        return self._fallback_questions(article_title)
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return self._fallback_questions(article_title)
    
    def _fallback_questions(self, article_title: str) -> Dict:
        """Generate fallback questions if AI fails"""
        return {
            "title": "Article d'actualité",
            "questions": [
                {"id": 1, "text": "Quel est le domaine ou le sujet général abordé dans cet article ?", "difficulty": 1},
                {"id": 2, "text": "Quel événement spécifique ou quelle décision est mentionné(e) ?", "difficulty": 2},
                {"id": 3, "text": "De quelle personne, organisation ou pays parle-t-on principalement ?", "difficulty": 3}
            ],
            "hints": [
                "Cet article parle d'un sujet d'actualité récent",
                "Le sujet concerne un événement ou une décision importante",
                "Cela implique des acteurs politiques, économiques ou sociaux"
            ],
            "answer_keywords": article_title.lower().split()[:5],
            "full_answer": article_title
        }
    
    async def check_answer(self, user_guess: str, keywords: List[str], full_answer: str) -> tuple[bool, str]:
        """Check if answer is correct using AI"""
        prompt = f"""Tu es un vérificateur de réponses pour un jeu.

SUJET ATTENDU : {full_answer}
MOTS-CLÉS : {', '.join(keywords)}
RÉPONSE DU JOUEUR : {user_guess}

INSTRUCTIONS :
Évalue si la réponse du joueur correspond au sujet attendu. Sois tolérant avec :
- Les fautes d'orthographe
- Les synonymes
- Les formulations différentes mais correctes
- Les réponses partielles correctes

IMPORTANT : Si le joueur mentionne le bon sujet, même avec des détails manquants, c'est CORRECT.

Réponds EXACTEMENT avec ce JSON :
{{"correct": true/false, "feedback": "Message explicatif"}}

Ton évaluation :"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 100
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        response_text = data.get('response', '')
                        
                        try:
                            result = json.loads(response_text)
                            return result.get('correct', False), result.get('feedback', 'Merci pour ta réponse !')
                        except:
                            pass
        except Exception as e:
            print(f"Error checking answer: {e}")
        
        # Fallback: simple keyword matching with better logic
        guess_lower = user_guess.lower().strip()
        full_lower = full_answer.lower()
        
        # Direct match or very close
        if guess_lower in full_lower or full_lower in guess_lower:
            return True, "Excellent ! Tu as trouvé le sujet exact de l'article !"
        
        # Keyword matching
        matched_keywords = [k for k in keywords if k.lower() in guess_lower and len(k) > 3]
        if len(matched_keywords) >= 2:
            return True, f"Très bien ! Tu as identifié les éléments clés : {', '.join(matched_keywords)}"
        elif len(matched_keywords) == 1:
            return False, f"Tu es sur la bonne piste avec '{matched_keywords[0]}', mais il manque des éléments. Continue !"
        
        # Check for partial matches
        guess_words = set(guess_lower.split())
        title_words = set(full_lower.split())
        common = guess_words & title_words
        if len(common) >= 2:
            return True, "Bonne réponse ! Tu as trouvé l'essentiel du sujet."
        
        return False, "Ce n'est pas tout à fait ça. Relis les indices et essaie de nouveau !"
    
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