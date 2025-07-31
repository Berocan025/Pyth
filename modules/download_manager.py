import os
import subprocess
import logging
import yt_dlp
from typing import Dict, Optional, List
import time
import shutil
from pathlib import Path
import re
from config import Config
from modules.database import DatabaseManager

logger = logging.getLogger(__name__)

class DownloadManager:
    """Video indirme yönetim sınıfı"""
    
    def __init__(self):
        self.download_path = Config.DOWNLOAD_PATH
        self.preferred_quality = Config.PREFERRED_QUALITY
        self.db_manager = DatabaseManager()
        
        # Downloads klasörünü oluştur
        os.makedirs(self.download_path, exist_ok=True)
        
    def download_movie(self, movie_data: Dict) -> Dict:
        """Film indirir"""
        try:
            movie_title = movie_data.get('title', 'Unknown Movie')
            movie_url = movie_data.get('source_url')
            
            if not movie_url:
                return {'success': False, 'error': 'Film URL\'si bulunamadı'}
            
            logger.info(f"Film indiriliyor: {movie_title}")
            
            # Film zaten var mı kontrol et
            if self.db_manager.movie_exists(movie_title, movie_data.get('year')):
                logger.info(f"Film zaten mevcut: {movie_title}")
                return {'success': False, 'error': 'Film zaten mevcut'}
            
            # Film detaylarını al (indirme linkleri için)
            from modules.movie_scraper import MovieScraper
            scraper = MovieScraper(Config.TARGET_MOVIE_SITE)
            movie_details = scraper.get_movie_details(movie_url)
            
            download_links = movie_details.get('download_links', [])
            
            if not download_links:
                logger.warning(f"İndirme linki bulunamadı: {movie_title}")
                # Alternatif yöntem: doğrudan URL'yi dene
                return self._download_with_yt_dlp(movie_url, movie_data)
            
            # En uygun linki seç (Türkçe ve yüksek kalite)
            best_link = self._select_best_download_link(download_links)
            
            if best_link:
                return self._download_with_yt_dlp(best_link['url'], movie_data)
            else:
                return self._download_with_yt_dlp(movie_url, movie_data)
                
        except Exception as e:
            logger.error(f"Film indirme hatası: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _select_best_download_link(self, download_links: List[Dict]) -> Optional[Dict]:
        """En uygun indirme linkini seçer"""
        # Türkçe dublajlı linkler
        turkish_links = [link for link in download_links if link.get('language') == 'Turkish']
        
        if turkish_links:
            # Türkçe linkler içinden en yüksek kaliteyi seç
            turkish_links.sort(key=lambda x: self._quality_score(x.get('quality', '')), reverse=True)
            return turkish_links[0]
        
        # İngilizce linkler
        english_links = [link for link in download_links if link.get('language') == 'English']
        
        if english_links:
            # İngilizce linkler içinden en yüksek kaliteyi seç
            english_links.sort(key=lambda x: self._quality_score(x.get('quality', '')), reverse=True)
            return english_links[0]
        
        # Diğer linkler
        if download_links:
            download_links.sort(key=lambda x: self._quality_score(x.get('quality', '')), reverse=True)
            return download_links[0]
        
        return None
    
    def _quality_score(self, quality: str) -> int:
        """Kalite skoru hesaplar"""
        quality_scores = {
            '4K': 4,
            '1080p': 3,
            '720p': 2,
            '480p': 1
        }
        return quality_scores.get(quality, 0)
    
    def _download_with_yt_dlp(self, url: str, movie_data: Dict) -> Dict:
        """yt-dlp ile video indirir"""
        try:
            movie_title = movie_data.get('title', 'Unknown Movie')
            safe_title = self._sanitize_filename(movie_title)
            
            # Çıkış dosya formatı
            output_template = os.path.join(self.download_path, f"{safe_title}.%(ext)s")
            
            # yt-dlp konfigürasyonu
            ydl_opts = {
                'outtmpl': output_template,
                'format': self._get_format_selector(),
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['tr', 'en'],  # Türkçe ve İngilizce altyazı
                'ignoreerrors': True,
                'no_warnings': False,
                'extractaudio': False,
                'audioformat': 'mp3',
                'embed_thumbnail': True,
                'addmetadata': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                },
                'socket_timeout': 30,
                'retries': 3,
                'fragment_retries': 3,
                'http_chunk_size': 10485760,  # 10MB chunks
                'concurrent_fragment_downloads': 4
            }
            
            # Hook'ları ekle
            ydl_opts['progress_hooks'] = [self._progress_hook]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Video bilgilerini al
                try:
                    info = ydl.extract_info(url, download=False)
                    logger.info(f"Video bilgileri alındı: {info.get('title', movie_title)}")
                except Exception as e:
                    logger.warning(f"Video bilgi alma hatası: {str(e)}")
                    # Bilgi alamasak bile indirmeyi dene
                    info = None
                
                # İndir
                logger.info(f"İndirme başlıyor: {movie_title}")
                ydl.download([url])
                
                # İndirilen dosyayı bul
                downloaded_file = self._find_downloaded_file(safe_title)
                
                if downloaded_file and os.path.exists(downloaded_file):
                    # Dosyayı MP4'e dönüştür
                    mp4_file = self._convert_to_mp4(downloaded_file, safe_title)
                    
                    if mp4_file:
                        file_size = os.path.getsize(mp4_file)
                        logger.info(f"İndirme başarılı: {movie_title} ({file_size / (1024*1024):.1f} MB)")
                        
                        return {
                            'success': True,
                            'file_path': mp4_file,
                            'file_size': file_size,
                            'title': movie_title,
                            'format': 'MP4'
                        }
                    else:
                        return {'success': False, 'error': 'MP4 dönüştürme başarısız'}
                else:
                    return {'success': False, 'error': 'İndirilen dosya bulunamadı'}
                    
        except Exception as e:
            logger.error(f"yt-dlp indirme hatası: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _get_format_selector(self) -> str:
        """Format seçici oluşturur"""
        # Kalite tercihi
        if self.preferred_quality == '1080p':
            return 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
        elif self.preferred_quality == '720p':
            return 'bestvideo[height<=720]+bestaudio/best[height<=720]/best'
        elif self.preferred_quality == '480p':
            return 'bestvideo[height<=480]+bestaudio/best[height<=480]/best'
        else:
            return 'best/best[ext=mp4]/best'
    
    def _progress_hook(self, d):
        """İndirme ilerleme hook'u"""
        if d['status'] == 'downloading':
            percent = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            logger.info(f"İndirme ilerlemesi: {percent} - Hız: {speed}")
        elif d['status'] == 'finished':
            logger.info(f"İndirme tamamlandı: {d['filename']}")
    
    def _sanitize_filename(self, filename: str) -> str:
        """Dosya adını temizler"""
        # Türkçe karakterleri değiştir
        replacements = {
            'ş': 's', 'ğ': 'g', 'ü': 'u', 'ç': 'c', 'ı': 'i', 'ö': 'o',
            'Ş': 'S', 'Ğ': 'G', 'Ü': 'U', 'Ç': 'C', 'İ': 'I', 'Ö': 'O'
        }
        
        for old, new in replacements.items():
            filename = filename.replace(old, new)
        
        # Geçersiz karakterleri kaldır
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        # Maksimum 100 karakter
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename
    
    def _find_downloaded_file(self, safe_title: str) -> Optional[str]:
        """İndirilen dosyayı bulur"""
        try:
            # Olası dosya uzantıları
            extensions = ['.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv']
            
            for ext in extensions:
                file_path = os.path.join(self.download_path, f"{safe_title}{ext}")
                if os.path.exists(file_path):
                    return file_path
            
            # Dosya adında değişiklik olmuş olabilir, klasörde ara
            for file in os.listdir(self.download_path):
                if safe_title.lower() in file.lower():
                    file_path = os.path.join(self.download_path, file)
                    if os.path.isfile(file_path):
                        return file_path
            
            return None
            
        except Exception as e:
            logger.error(f"Dosya bulma hatası: {str(e)}")
            return None
    
    def _convert_to_mp4(self, input_file: str, safe_title: str) -> Optional[str]:
        """Videoyu MP4 formatına dönüştürür"""
        try:
            # Zaten MP4 ise dönüştürme
            if input_file.lower().endswith('.mp4'):
                return input_file
            
            output_file = os.path.join(self.download_path, f"{safe_title}_converted.mp4")
            
            # FFmpeg var mı kontrol et
            if not self._check_ffmpeg():
                logger.warning("FFmpeg bulunamadı, dosya dönüştürme yapılamıyor")
                return input_file  # Orijinal dosyayı döndür
            
            logger.info(f"MP4'e dönüştürülüyor: {input_file}")
            
            # FFmpeg komutu
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-c:v', 'libx264',  # H.264 codec
                '-c:a', 'aac',      # AAC audio
                '-preset', 'fast',   # Hızlı encoding
                '-crf', '23',       # Kalite (18-28 arası)
                '-movflags', '+faststart',  # Web uyumlu
                '-y',               # Dosyayı üzerine yaz
                output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 saat timeout
            
            if result.returncode == 0 and os.path.exists(output_file):
                # Orijinal dosyayı sil
                try:
                    os.remove(input_file)
                    logger.info(f"Orijinal dosya silindi: {input_file}")
                except Exception:
                    pass
                
                # Yeni dosyayı yeniden adlandır
                final_output = os.path.join(self.download_path, f"{safe_title}.mp4")
                try:
                    os.rename(output_file, final_output)
                    return final_output
                except Exception:
                    return output_file
            else:
                logger.error(f"FFmpeg dönüştürme hatası: {result.stderr}")
                return input_file
                
        except Exception as e:
            logger.error(f"MP4 dönüştürme hatası: {str(e)}")
            return input_file
    
    def _check_ffmpeg(self) -> bool:
        """FFmpeg kurulu mu kontrol eder"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False
    
    def install_ffmpeg(self) -> bool:
        """FFmpeg kurulumunu yapar"""
        try:
            logger.info("FFmpeg kuruluyor...")
            
            # Ubuntu/Debian için kurulum
            result = subprocess.run(['sudo', 'apt', 'update'], capture_output=True, timeout=300)
            if result.returncode != 0:
                logger.error("apt update başarısız")
                return False
            
            result = subprocess.run(['sudo', 'apt', 'install', '-y', 'ffmpeg'], 
                                  capture_output=True, timeout=600)
            
            if result.returncode == 0:
                logger.info("FFmpeg başarıyla kuruldu")
                return True
            else:
                logger.error(f"FFmpeg kurulum hatası: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"FFmpeg kurulum hatası: {str(e)}")
            return False
    
    def get_download_info(self, url: str) -> Dict:
        """Video hakkında bilgi alır"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'description': info.get('description', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': [
                        {
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'height': f.get('height'),
                            'filesize': f.get('filesize')
                        }
                        for f in info.get('formats', [])
                        if f.get('height')
                    ]
                }
                
        except Exception as e:
            logger.error(f"Video bilgi alma hatası: {str(e)}")
            return {}
    
    def cleanup_failed_downloads(self):
        """Başarısız indirmeleri temizler"""
        try:
            for file in os.listdir(self.download_path):
                file_path = os.path.join(self.download_path, file)
                
                # Temp dosyalar
                if file.endswith(('.part', '.tmp', '.temp')):
                    try:
                        os.remove(file_path)
                        logger.info(f"Temp dosya silindi: {file}")
                    except Exception:
                        pass
                
                # Çok küçük dosyalar (1MB altı)
                elif os.path.isfile(file_path) and os.path.getsize(file_path) < 1024 * 1024:
                    try:
                        os.remove(file_path)
                        logger.info(f"Küçük dosya silindi: {file}")
                    except Exception:
                        pass
                        
        except Exception as e:
            logger.error(f"Temizleme hatası: {str(e)}")
    
    def get_download_queue_status(self) -> Dict:
        """İndirme kuyruğu durumunu döndürür"""
        try:
            total_size = 0
            file_count = 0
            
            for file in os.listdir(self.download_path):
                file_path = os.path.join(self.download_path, file)
                if os.path.isfile(file_path):
                    file_count += 1
                    total_size += os.path.getsize(file_path)
            
            return {
                'file_count': file_count,
                'total_size': total_size,
                'total_size_gb': round(total_size / (1024**3), 2),
                'download_path': self.download_path
            }
            
        except Exception as e:
            logger.error(f"Durum alma hatası: {str(e)}")
            return {
                'file_count': 0,
                'total_size': 0,
                'total_size_gb': 0,
                'download_path': self.download_path
            }