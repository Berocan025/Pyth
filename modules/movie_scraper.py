import requests
import time
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse
import cloudscraper
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class MovieScraper:
    """Film sitesi scraper sınıfı"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = cloudscraper.create_scraper()
        self.ua = UserAgent()
        self.session.headers.update({
            'User-Agent': self.ua.random
        })
        
    def _get_page_content(self, url: str, use_selenium: bool = False) -> Optional[str]:
        """Sayfa içeriğini alır"""
        try:
            if use_selenium:
                return self._get_with_selenium(url)
            
            # Önce cloudscraper ile dene
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            return response.text
            
        except Exception as e:
            logger.warning(f"Cloudscraper başarısız, Selenium deneniyor: {str(e)}")
            try:
                return self._get_with_selenium(url)
            except Exception as selenium_error:
                logger.error(f"Selenium de başarısız: {str(selenium_error)}")
                return None
    
    def _get_with_selenium(self, url: str) -> str:
        """Selenium ile sayfa içeriğini alır"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={self.ua.random}')
        
        driver = webdriver.Chrome(
            options=chrome_options
        )
        
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)  # Sayfanın tam yüklenmesi için bekle
            
            return driver.page_source
            
        finally:
            driver.quit()
    
    def get_latest_movies(self, limit: int = 50) -> List[Dict]:
        """Son eklenen filmleri alır"""
        try:
            # Ana sayfayı al
            content = self._get_page_content(self.base_url)
            if not content:
                logger.error("Ana sayfa içeriği alınamadı")
                return []
            
            soup = BeautifulSoup(content, 'html.parser')
            movies = []
            
            # Genel film kartı seçicileri (çoğu sitede çalışır)
            movie_selectors = [
                '.movie-item',
                '.film-item',
                '.movie-card',
                '.film-card',
                '.post-item',
                '.content-item',
                'article',
                '.movie',
                '.film'
            ]
            
            movie_elements = []
            for selector in movie_selectors:
                elements = soup.select(selector)
                if elements:
                    movie_elements = elements[:limit]
                    logger.info(f"Film öğeleri bulundu: {selector} ({len(elements)} adet)")
                    break
            
            if not movie_elements:
                logger.warning("Film öğeleri bulunamadı, alternatif yöntem deneniyor")
                return self._fallback_scraping(soup, limit)
            
            for element in movie_elements:
                try:
                    movie_data = self._extract_movie_data(element)
                    if movie_data and movie_data.get('title'):
                        movies.append(movie_data)
                        
                except Exception as e:
                    logger.warning(f"Film verisi çıkarma hatası: {str(e)}")
                    continue
            
            logger.info(f"{len(movies)} film başarıyla çıkarıldı")
            return movies
            
        except Exception as e:
            logger.error(f"Film listesi alma hatası: {str(e)}")
            return []
    
    def _extract_movie_data(self, element) -> Dict:
        """Film verisini çıkarır"""
        movie_data = {}
        
        try:
            # Başlık
            title_selectors = [
                'h1', 'h2', 'h3', 'h4',
                '.title', '.movie-title', '.film-title',
                '.post-title', '.entry-title',
                'a[title]', '.name'
            ]
            
            title = self._find_text_by_selectors(element, title_selectors)
            if title:
                movie_data['title'] = self._clean_title(title)
            
            # URL
            url_element = element.find('a', href=True)
            if url_element:
                movie_data['source_url'] = urljoin(self.base_url, url_element['href'])
            
            # Görsel
            img_element = element.find('img')
            if img_element:
                img_src = img_element.get('src') or img_element.get('data-src')
                if img_src:
                    movie_data['poster_url'] = urljoin(self.base_url, img_src)
            
            # Yıl
            year_text = element.get_text()
            year_match = re.search(r'(19|20)\d{2}', year_text)
            if year_match:
                movie_data['year'] = int(year_match.group())
            
            # Kalite/Dil bilgisi
            text_content = element.get_text().lower()
            
            # Kalite tespiti
            quality_patterns = ['1080p', '720p', '480p', '4k', 'hd', 'full hd']
            for quality in quality_patterns:
                if quality in text_content:
                    movie_data['quality'] = quality.upper()
                    break
            
            # Dil tespiti
            if any(term in text_content for term in ['türkçe', 'turkish', 'tr dublaj']):
                movie_data['language'] = 'Turkish'
            elif any(term in text_content for term in ['english', 'eng', 'ingilizce']):
                movie_data['language'] = 'English'
            
            # Tür
            genre_element = element.find(class_=re.compile(r'genre|category|tag'))
            if genre_element:
                movie_data['genre'] = genre_element.get_text().strip()
            
            return movie_data
            
        except Exception as e:
            logger.warning(f"Film verisi çıkarma hatası: {str(e)}")
            return {}
    
    def _find_text_by_selectors(self, element, selectors: List[str]) -> Optional[str]:
        """Seçiciler ile text arar"""
        for selector in selectors:
            found = element.select_one(selector)
            if found:
                text = found.get_text().strip()
                if text:
                    return text
        return None
    
    def _clean_title(self, title: str) -> str:
        """Başlığı temizler"""
        # Gereksiz karakterleri temizle
        title = re.sub(r'\s+', ' ', title)  # Çoklu boşlukları tek yap
        title = re.sub(r'[\[\](){}]', '', title)  # Parantezleri kaldır
        title = title.replace('İzle', '').replace('izle', '')
        title = title.replace('HD', '').replace('hd', '')
        title = title.strip()
        
        return title
    
    def _fallback_scraping(self, soup, limit: int) -> List[Dict]:
        """Alternatif scraping yöntemi"""
        movies = []
        
        try:
            # Tüm linkleri al
            links = soup.find_all('a', href=True)
            
            for link in links[:limit * 2]:  # Daha fazla link kontrol et
                href = link.get('href', '')
                text = link.get_text().strip()
                
                # Film linki olma olasılığını kontrol et
                if self._is_likely_movie_link(href, text):
                    movie_data = {
                        'title': self._clean_title(text),
                        'source_url': urljoin(self.base_url, href)
                    }
                    
                    # Yıl bilgisini çıkar
                    year_match = re.search(r'(19|20)\d{2}', text)
                    if year_match:
                        movie_data['year'] = int(year_match.group())
                    
                    movies.append(movie_data)
                    
                    if len(movies) >= limit:
                        break
            
            logger.info(f"Alternatif yöntemle {len(movies)} film bulundu")
            return movies
            
        except Exception as e:
            logger.error(f"Alternatif scraping hatası: {str(e)}")
            return []
    
    def _is_likely_movie_link(self, href: str, text: str) -> bool:
        """Link film linkimi kontrol eder"""
        if not href or not text:
            return False
        
        # Çok kısa textleri atlaya
        if len(text.strip()) < 3:
            return False
        
        # Film olmayan linkler
        excluded_terms = [
            'contact', 'about', 'home', 'login', 'register',
            'category', 'tag', 'page', 'admin', 'user',
            'search', 'rss', 'feed', 'sitemap'
        ]
        
        href_lower = href.lower()
        text_lower = text.lower()
        
        for term in excluded_terms:
            if term in href_lower or term in text_lower:
                return False
        
        # Film olabilecek içerik
        movie_indicators = [
            'film', 'movie', 'sinema', 'cinema',
            'izle', 'watch', 'stream'
        ]
        
        for indicator in movie_indicators:
            if indicator in href_lower or indicator in text_lower:
                return True
        
        # Yıl içeriyorsa film olabilir
        if re.search(r'(19|20)\d{2}', text):
            return True
        
        return False
    
    def get_movie_details(self, movie_url: str) -> Dict:
        """Film detaylarını alır"""
        try:
            content = self._get_page_content(movie_url)
            if not content:
                return {}
            
            soup = BeautifulSoup(content, 'html.parser')
            details = {}
            
            # Açıklama
            desc_selectors = [
                '.description', '.content', '.summary',
                '.synopsis', '.plot', '.overview',
                '.movie-description', '.film-description'
            ]
            
            description = self._find_text_by_selectors(soup, desc_selectors)
            if description:
                details['description'] = description[:500]  # İlk 500 karakter
            
            # IMDB rating
            rating_text = soup.get_text()
            rating_match = re.search(r'imdb[:\s]*(\d+\.?\d*)', rating_text, re.IGNORECASE)
            if rating_match:
                try:
                    details['imdb_rating'] = float(rating_match.group(1))
                except ValueError:
                    pass
            
            # Süre
            duration_match = re.search(r'(\d+)\s*(?:dk|min|minute)', soup.get_text(), re.IGNORECASE)
            if duration_match:
                details['duration'] = f"{duration_match.group(1)} dk"
            
            # İndirme linklerini bul
            download_links = self._find_download_links(soup)
            if download_links:
                details['download_links'] = download_links
            
            return details
            
        except Exception as e:
            logger.error(f"Film detayları alma hatası: {str(e)}")
            return {}
    
    def _find_download_links(self, soup) -> List[Dict]:
        """İndirme linklerini bulur"""
        download_links = []
        
        try:
            # İndirme linki olabilecek öğeler
            link_selectors = [
                'a[href*="download"]',
                'a[href*="indir"]',
                'a[href*="stream"]',
                'a[href*="watch"]',
                'a[href*="izle"]',
                '.download-link',
                '.stream-link',
                '.watch-link'
            ]
            
            for selector in link_selectors:
                links = soup.select(selector)
                
                for link in links:
                    href = link.get('href')
                    text = link.get_text().strip()
                    
                    if href and text:
                        # Kalite ve dil bilgisini çıkar
                        quality = self._extract_quality_from_text(text)
                        language = self._extract_language_from_text(text)
                        
                        download_links.append({
                            'url': href,
                            'text': text,
                            'quality': quality,
                            'language': language
                        })
            
            # Türkçe ve yüksek kaliteyi öne çıkar
            download_links.sort(key=lambda x: (
                x['language'] == 'Turkish',  # Türkçe önce
                self._quality_score(x['quality'])  # Sonra kalite
            ), reverse=True)
            
            return download_links
            
        except Exception as e:
            logger.error(f"İndirme linki bulma hatası: {str(e)}")
            return []
    
    def _extract_quality_from_text(self, text: str) -> str:
        """Metinden kalite bilgisini çıkarır"""
        text_lower = text.lower()
        
        if '4k' in text_lower or '2160p' in text_lower:
            return '4K'
        elif '1080p' in text_lower or 'full hd' in text_lower:
            return '1080p'
        elif '720p' in text_lower or 'hd' in text_lower:
            return '720p'
        elif '480p' in text_lower:
            return '480p'
        else:
            return 'Unknown'
    
    def _extract_language_from_text(self, text: str) -> str:
        """Metinden dil bilgisini çıkarır"""
        text_lower = text.lower()
        
        if any(term in text_lower for term in ['türkçe', 'tr dublaj', 'turkish']):
            return 'Turkish'
        elif any(term in text_lower for term in ['english', 'eng', 'ingilizce']):
            return 'English'
        else:
            return 'Unknown'
    
    def _quality_score(self, quality: str) -> int:
        """Kalite skoru hesaplar"""
        quality_scores = {
            '4K': 4,
            '1080p': 3,
            '720p': 2,
            '480p': 1,
            'Unknown': 0
        }
        return quality_scores.get(quality, 0)