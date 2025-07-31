import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Veritabanı yönetim sınıfı"""
    
    def __init__(self, db_path: str = "movie_manager.db"):
        self.db_path = db_path
    
    def init_database(self):
        """Veritabanını ve tabloları oluşturur"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Movies tablosu
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS movies (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        original_title TEXT,
                        year INTEGER,
                        genre TEXT,
                        description TEXT,
                        duration TEXT,
                        imdb_rating REAL,
                        language TEXT,
                        quality TEXT,
                        file_size INTEGER,
                        local_path TEXT,
                        cdn_url TEXT,
                        source_url TEXT,
                        download_date TEXT,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Download logs tablosu
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS download_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        movie_id INTEGER,
                        action TEXT,
                        status TEXT,
                        message TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (movie_id) REFERENCES movies (id)
                    )
                ''')
                
                # Settings tablosu
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        key TEXT UNIQUE,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Veritabanı başarıyla başlatıldı")
                
        except Exception as e:
            logger.error(f"Veritabanı başlatma hatası: {str(e)}")
            raise
    
    def add_movie(self, movie_data: Dict) -> int:
        """Yeni film ekler"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO movies (
                        title, original_title, year, genre, description, 
                        duration, imdb_rating, language, quality, file_size,
                        local_path, cdn_url, source_url, download_date, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    movie_data.get('title'),
                    movie_data.get('original_title'),
                    movie_data.get('year'),
                    movie_data.get('genre'),
                    movie_data.get('description'),
                    movie_data.get('duration'),
                    movie_data.get('imdb_rating'),
                    movie_data.get('language'),
                    movie_data.get('quality'),
                    movie_data.get('file_size'),
                    movie_data.get('local_path'),
                    movie_data.get('cdn_url'),
                    movie_data.get('source_url'),
                    movie_data.get('download_date'),
                    movie_data.get('status', 'completed')
                ))
                
                movie_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Film eklendi: {movie_data.get('title')} (ID: {movie_id})")
                return movie_id
                
        except Exception as e:
            logger.error(f"Film ekleme hatası: {str(e)}")
            raise
    
    def get_movie_by_title(self, title: str) -> Optional[Dict]:
        """Başlığa göre film arar"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM movies WHERE title = ? ORDER BY created_at DESC LIMIT 1",
                    (title,)
                )
                
                row = cursor.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Film arama hatası: {str(e)}")
            return None
    
    def get_movies_paginated(self, page: int = 1, per_page: int = 20) -> Dict:
        """Sayfalama ile film listesi"""
        try:
            offset = (page - 1) * per_page
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Toplam sayı
                cursor.execute("SELECT COUNT(*) as count FROM movies")
                total = cursor.fetchone()['count']
                
                # Filmler
                cursor.execute('''
                    SELECT * FROM movies 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (per_page, offset))
                
                movies = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'movies': movies,
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
                
        except Exception as e:
            logger.error(f"Film listesi hatası: {str(e)}")
            return {'movies': [], 'page': 1, 'per_page': per_page, 'total': 0, 'pages': 0}
    
    def search_movies(self, search_term: str, page: int = 1, per_page: int = 20) -> Dict:
        """Film arama"""
        try:
            offset = (page - 1) * per_page
            search_pattern = f"%{search_term}%"
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Toplam sayı
                cursor.execute('''
                    SELECT COUNT(*) as count FROM movies 
                    WHERE title LIKE ? OR original_title LIKE ? OR genre LIKE ?
                ''', (search_pattern, search_pattern, search_pattern))
                total = cursor.fetchone()['count']
                
                # Filmler
                cursor.execute('''
                    SELECT * FROM movies 
                    WHERE title LIKE ? OR original_title LIKE ? OR genre LIKE ?
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                ''', (search_pattern, search_pattern, search_pattern, per_page, offset))
                
                movies = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'movies': movies,
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page,
                    'search_term': search_term
                }
                
        except Exception as e:
            logger.error(f"Film arama hatası: {str(e)}")
            return {'movies': [], 'page': 1, 'per_page': per_page, 'total': 0, 'pages': 0}
    
    def get_recent_movies(self, limit: int = 10) -> List[Dict]:
        """Son eklenen filmler"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM movies 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Son filmler hatası: {str(e)}")
            return []
    
    def get_statistics(self) -> Dict:
        """İstatistik bilgileri"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Toplam film sayısı
                cursor.execute("SELECT COUNT(*) as count FROM movies")
                total_movies = cursor.fetchone()['count']
                
                # Bu ayki filmler
                cursor.execute('''
                    SELECT COUNT(*) as count FROM movies 
                    WHERE created_at >= date('now', 'start of month')
                ''')
                monthly_movies = cursor.fetchone()['count']
                
                # Toplam dosya boyutu
                cursor.execute("SELECT SUM(file_size) as total_size FROM movies WHERE file_size IS NOT NULL")
                total_size = cursor.fetchone()['total_size'] or 0
                
                # En popüler türler
                cursor.execute('''
                    SELECT genre, COUNT(*) as count 
                    FROM movies 
                    WHERE genre IS NOT NULL 
                    GROUP BY genre 
                    ORDER BY count DESC 
                    LIMIT 5
                ''')
                popular_genres = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'total_movies': total_movies,
                    'monthly_movies': monthly_movies,
                    'total_size': total_size,
                    'total_size_gb': round(total_size / (1024**3), 2) if total_size else 0,
                    'popular_genres': popular_genres
                }
                
        except Exception as e:
            logger.error(f"İstatistik hatası: {str(e)}")
            return {
                'total_movies': 0,
                'monthly_movies': 0,
                'total_size': 0,
                'total_size_gb': 0,
                'popular_genres': []
            }
    
    def add_log(self, movie_id: int, action: str, status: str, message: str = ""):
        """Log kaydı ekler"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO download_logs (movie_id, action, status, message)
                    VALUES (?, ?, ?, ?)
                ''', (movie_id, action, status, message))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Log ekleme hatası: {str(e)}")
    
    def update_movie_status(self, movie_id: int, status: str):
        """Film durumunu günceller"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE movies 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (status, movie_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Film durumu güncelleme hatası: {str(e)}")
    
    def movie_exists(self, title: str, year: int = None) -> bool:
        """Film var mı kontrol eder"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if year:
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM movies WHERE title = ? AND year = ?",
                        (title, year)
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) as count FROM movies WHERE title = ?",
                        (title,)
                    )
                
                result = cursor.fetchone()
                return result[0] > 0
                
        except Exception as e:
            logger.error(f"Film kontrol hatası: {str(e)}")
            return False