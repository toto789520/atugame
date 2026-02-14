import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import random
import time


class NewsScraper:
    def __init__(self):
        self.articles = []
        self.last_update = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_lemonde(self) -> List[Dict]:
        """Scrape Le Monde actualités"""
        articles = []
        try:
            url = "https://www.lemonde.fr/actualites/"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find article links
            for article in soup.find_all('article', limit=10):
                link = article.find('a')
                title_elem = article.find(['h2', 'h3', 'p', 'span'], class_=lambda x: x and 'title' in x.lower() if x else True)
                
                if link and title_elem:
                    title = title_elem.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if href and title and len(title) > 20:
                        if not href.startswith('http'):
                            href = f"https://www.lemonde.fr{href}"
                        
                        articles.append({
                            'title': title,
                            'url': href,
                            'source': 'Le Monde'
                        })
        except Exception as e:
            print(f"Error scraping Le Monde: {e}")
        
        return articles
    
    def scrape_franceinfo(self) -> List[Dict]:
        """Scrape France Info"""
        articles = []
        try:
            url = "https://www.francetvinfo.fr/"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for item in soup.find_all('article', limit=10):
                link = item.find('a')
                title_elem = item.find(['h2', 'h3', 'h1', 'span'])
                
                if link and title_elem:
                    title = title_elem.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if href and title and len(title) > 20:
                        if not href.startswith('http'):
                            href = f"https://www.francetvinfo.fr{href}"
                        
                        articles.append({
                            'title': title,
                            'url': href,
                            'source': 'France Info'
                        })
        except Exception as e:
            print(f"Error scraping France Info: {e}")
        
        return articles
    
    def scrape_bbc(self) -> List[Dict]:
        """Scrape BBC News"""
        articles = []
        try:
            url = "https://www.bbc.com/news"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for item in soup.find_all(['article', 'div'], class_=lambda x: x and 'promo' in str(x).lower() if x else False, limit=10):
                link = item.find('a', href=lambda x: x and '/news/' in x if x else False)
                title_elem = item.find(['h2', 'h3', 'h1'])
                
                if link and title_elem:
                    title = title_elem.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if href and title and len(title) > 20:
                        if not href.startswith('http'):
                            href = f"https://www.bbc.com{href}"
                        
                        articles.append({
                            'title': title,
                            'url': href,
                            'source': 'BBC'
                        })
        except Exception as e:
            print(f"Error scraping BBC: {e}")
        
        return articles
    
    def scrape_guardian(self) -> List[Dict]:
        """Scrape The Guardian"""
        articles = []
        try:
            url = "https://www.theguardian.com/international"
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for item in soup.find_all('a', class_=lambda x: x and 'link' in str(x).lower() if x else False, limit=15):
                href = item.get('href', '')
                title = item.get_text(strip=True)
                
                if href and title and len(title) > 30 and '/news/' in href:
                    if not href.startswith('http'):
                        href = f"https://www.theguardian.com{href}"
                    
                    articles.append({
                        'title': title,
                        'url': href,
                        'source': 'The Guardian'
                    })
        except Exception as e:
            print(f"Error scraping Guardian: {e}")
        
        return articles
    
    def update_articles(self):
        """Update all articles from sources"""
        print("Updating news articles...")
        all_articles = []
        
        all_articles.extend(self.scrape_lemonde())
        time.sleep(0.5)
        
        all_articles.extend(self.scrape_franceinfo())
        time.sleep(0.5)
        
        all_articles.extend(self.scrape_bbc())
        time.sleep(0.5)
        
        all_articles.extend(self.scrape_guardian())
        
        # Remove duplicates by title similarity
        unique_articles = []
        seen_titles = set()
        
        for article in all_articles:
            # Simple deduplication
            title_lower = article['title'].lower()[:50]
            if title_lower not in seen_titles and len(article['title']) > 30:
                seen_titles.add(title_lower)
                unique_articles.append(article)
        
        self.articles = unique_articles[:20]  # Keep top 20
        self.last_update = time.time()
        print(f"Updated {len(self.articles)} articles")
    
    def get_random_article(self) -> Optional[Dict]:
        """Get a random article for the game"""
        if not self.articles:
            self.update_articles()
        
        if self.articles:
            return random.choice(self.articles)
        
        return None
    
    def get_article_content(self, url: str) -> str:
        """Try to get article content"""
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find main content
            for selector in ['article', 'main', '[role="main"]', '.article-body', '.content']:
                content = soup.select_one(selector)
                if content:
                    return content.get_text(separator=' ', strip=True)[:2000]
            
            # Fallback to body
            body = soup.find('body')
            if body:
                return body.get_text(separator=' ', strip=True)[:2000]
        except Exception as e:
            print(f"Error getting article content: {e}")
        
        return ""


# Singleton instance
scraper = NewsScraper()