from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import os
import json
import sqlite3
import threading
from datetime import datetime
import logging
from config import Config
from modules.movie_scraper import MovieScraper
from modules.vpn_manager import VPNManager
from modules.download_manager import DownloadManager
from modules.bunnycdn_uploader import BunnyCDNUploader
from modules.database import DatabaseManager

# Logging ayarları
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Veritabanı başlatma
db_manager = DatabaseManager()

# Global işlem durumu
processing_status = {
    'is_running': False,
    'current_step': '',
    'progress': 0,
    'total_movies': 0,
    'processed_movies': 0,
    'errors': [],
    'last_update': datetime.now().isoformat()
}

@app.route('/')
def index():
    """Ana sayfa"""
    return render_template('index.html', status=processing_status)

@app.route('/dashboard')
def dashboard():
    """Dashboard sayfası"""
    stats = db_manager.get_statistics()
    recent_movies = db_manager.get_recent_movies(limit=10)
    return render_template('dashboard.html', stats=stats, recent_movies=recent_movies)

@app.route('/movies')
def movies():
    """Film listesi sayfası"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    movies = db_manager.get_movies_paginated(page, per_page)
    return render_template('movies.html', movies=movies)

@app.route('/settings')
def settings():
    """Ayarlar sayfası"""
    return render_template('settings.html', config=Config)

@app.route('/api/start_processing', methods=['POST'])
def start_processing():
    """Film işleme sürecini başlatır"""
    global processing_status
    
    if processing_status['is_running']:
        return jsonify({'success': False, 'message': 'İşlem zaten çalışıyor'})
    
    try:
        # Konfigürasyonu doğrula
        Config.validate_config()
        
        # Yeni thread'de işleme başlat
        thread = threading.Thread(target=process_movies)
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'İşlem başlatıldı'})
    
    except Exception as e:
        logger.error(f"İşlem başlatma hatası: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/stop_processing', methods=['POST'])
def stop_processing():
    """Film işleme sürecini durdurur"""
    global processing_status
    processing_status['is_running'] = False
    processing_status['current_step'] = 'Durduruluyor...'
    return jsonify({'success': True, 'message': 'İşlem durduruldu'})

@app.route('/api/status')
def get_status():
    """Anlık durum bilgisi"""
    return jsonify(processing_status)

@app.route('/api/movies')
def api_movies():
    """Film listesi API"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    movies = db_manager.search_movies(search, page)
    return jsonify(movies)

@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    """Ayarları günceller"""
    try:
        data = request.get_json()
        
        # .env dosyasını güncelle
        env_content = []
        
        for key, value in data.items():
            env_content.append(f"{key}={value}")
        
        with open('.env', 'w') as f:
            f.write('\n'.join(env_content))
        
        flash('Ayarlar başarıyla güncellendi. Uygulamayı yeniden başlatın.', 'success')
        return jsonify({'success': True, 'message': 'Ayarlar güncellendi'})
    
    except Exception as e:
        logger.error(f"Ayar güncelleme hatası: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

def update_status(step, progress=None, total=None, processed=None, error=None):
    """Durum güncelleme fonksiyonu"""
    global processing_status
    
    processing_status['current_step'] = step
    processing_status['last_update'] = datetime.now().isoformat()
    
    if progress is not None:
        processing_status['progress'] = progress
    if total is not None:
        processing_status['total_movies'] = total
    if processed is not None:
        processing_status['processed_movies'] = processed
    if error:
        processing_status['errors'].append({
            'time': datetime.now().isoformat(),
            'message': error
        })

def process_movies():
    """Ana film işleme fonksiyonu"""
    global processing_status
    
    processing_status['is_running'] = True
    processing_status['errors'] = []
    processing_status['progress'] = 0
    
    try:
        update_status("Başlatılıyor...")
        
        # Modülleri başlat
        scraper = MovieScraper(Config.TARGET_MOVIE_SITE)
        vpn_manager = VPNManager()
        download_manager = DownloadManager()
        uploader = BunnyCDNUploader()
        
        update_status("Film sitesi taranıyor...")
        
        # Yeni filmleri bul
        new_movies = scraper.get_latest_movies()
        
        if not new_movies:
            update_status("Yeni film bulunamadı", progress=100)
            processing_status['is_running'] = False
            return
        
        update_status(f"{len(new_movies)} yeni film bulundu", total=len(new_movies))
        
        # VPN'e bağlan
        update_status("ProtonVPN'e bağlanılıyor...")
        vpn_connected = vpn_manager.connect()
        
        if not vpn_connected:
            update_status("VPN bağlantısı başarısız", error="VPN bağlantı hatası")
        
        processed = 0
        
        for i, movie in enumerate(new_movies[:Config.MAX_DOWNLOADS_PER_SESSION]):
            if not processing_status['is_running']:
                break
            
            try:
                update_status(f"İndiriliyor: {movie['title']}", processed=processed)
                
                # Film indir
                download_result = download_manager.download_movie(movie)
                
                if download_result['success']:
                    update_status(f"BunnyCDN'e yükleniyor: {movie['title']}")
                    
                    # VPN'i kapat
                    if vpn_connected:
                        vpn_manager.disconnect()
                    
                    # BunnyCDN'e yükle
                    upload_result = uploader.upload_file(
                        download_result['file_path'],
                        movie['title']
                    )
                    
                    if upload_result['success']:
                        # Veritabanına kaydet
                        db_manager.add_movie({
                            **movie,
                            'local_path': download_result['file_path'],
                            'cdn_url': upload_result['cdn_url'],
                            'download_date': datetime.now().isoformat(),
                            'file_size': download_result['file_size']
                        })
                        
                        # Yerel dosyayı sil
                        os.remove(download_result['file_path'])
                        
                        processed += 1
                        update_status(f"Tamamlandı: {movie['title']}", processed=processed)
                    else:
                        update_status(f"Yükleme hatası: {movie['title']}", 
                                    error=f"BunnyCDN yükleme hatası: {upload_result['error']}")
                    
                    # VPN'i tekrar bağla
                    if processed < len(new_movies) - 1:
                        vpn_manager.connect()
                else:
                    update_status(f"İndirme hatası: {movie['title']}", 
                                error=f"İndirme hatası: {download_result['error']}")
                
                # İlerleme hesapla
                progress = int((i + 1) / len(new_movies) * 100)
                update_status(processing_status['current_step'], progress=progress)
                
            except Exception as e:
                logger.error(f"Film işleme hatası {movie['title']}: {str(e)}")
                update_status(f"Hata: {movie['title']}", error=str(e))
        
        # VPN'i kapat
        if vpn_connected:
            vpn_manager.disconnect()
        
        update_status(f"İşlem tamamlandı. {processed} film işlendi.", progress=100)
        
    except Exception as e:
        logger.error(f"Genel işlem hatası: {str(e)}")
        update_status("İşlem hatası", error=str(e))
    
    finally:
        processing_status['is_running'] = False

if __name__ == '__main__':
    # Downloads klasörünü oluştur
    os.makedirs(Config.DOWNLOAD_PATH, exist_ok=True)
    
    # Veritabanını başlat
    db_manager.init_database()
    
    # Uygulamayı başlat
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG
    )