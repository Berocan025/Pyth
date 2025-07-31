#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Film Yönetim Sistemi - Ana Çalıştırma Script'i

Bu script sistemi başlatır ve gerekli kurulumları yapar.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Ana dizini sys.path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_python_version():
    """Python sürümünü kontrol eder"""
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 veya üzeri gerekli!")
        logger.error(f"Mevcut sürüm: {sys.version}")
        return False
    
    logger.info(f"Python sürümü uygun: {sys.version}")
    return True

def check_system_dependencies():
    """Sistem bağımlılıklarını kontrol eder"""
    dependencies = {
        'ffmpeg': 'FFmpeg video dönüştürme için gerekli',
        'curl': 'HTTP istekleri için gerekli',
        'wget': 'Dosya indirme için gerekli'
    }
    
    missing = []
    
    for dep, description in dependencies.items():
        try:
            result = subprocess.run(['which', dep], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"✓ {dep} bulundu: {result.stdout.strip()}")
            else:
                logger.warning(f"✗ {dep} bulunamadı - {description}")
                missing.append(dep)
        except Exception as e:
            logger.error(f"Bağımlılık kontrolü hatası {dep}: {str(e)}")
            missing.append(dep)
    
    return missing

def install_system_dependencies(missing_deps):
    """Eksik sistem bağımlılıklarını kurar"""
    if not missing_deps:
        return True
    
    logger.info("Eksik sistem bağımlılıkları kuruluyor...")
    
    try:
        # Paket listesini güncelle
        subprocess.run(['sudo', 'apt', 'update'], check=True)
        
        # Eksik paketleri kur
        cmd = ['sudo', 'apt', 'install', '-y'] + missing_deps
        subprocess.run(cmd, check=True)
        
        logger.info("Sistem bağımlılıkları başarıyla kuruldu")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Sistem bağımlılıkları kurulumunda hata: {e}")
        return False
    except Exception as e:
        logger.error(f"Beklenmeyen hata: {e}")
        return False

def check_python_packages():
    """Python paketlerini kontrol eder"""
    try:
        import flask
        import requests
        import yt_dlp
        import selenium
        logger.info("Ana Python paketleri mevcut")
        return True
    except ImportError as e:
        logger.warning(f"Python paketi eksik: {e}")
        return False

def install_python_packages():
    """Python paketlerini kurar"""
    logger.info("Python paketleri kuruluyor...")
    
    try:
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], check=True)
        
        logger.info("Python paketleri başarıyla kuruldu")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Python paketleri kurulumunda hata: {e}")
        return False

def setup_directories():
    """Gerekli klasörleri oluşturur"""
    directories = [
        Config.DOWNLOAD_PATH,
        'logs',
        'static/uploads',
        'instance'
    ]
    
    for directory in directories:
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.info(f"Klasör oluşturuldu/kontrol edildi: {directory}")
        except Exception as e:
            logger.error(f"Klasör oluşturma hatası {directory}: {e}")
            return False
    
    return True

def check_configuration():
    """Konfigürasyonu kontrol eder"""
    try:
        Config.validate_config()
        logger.info("Konfigürasyon geçerli")
        return True
    except ValueError as e:
        logger.error(f"Konfigürasyon hatası: {e}")
        logger.error("Lütfen .env dosyasını kontrol edin")
        return False

def test_database():
    """Veritabanını test eder"""
    try:
        from modules.database import DatabaseManager
        
        db = DatabaseManager()
        db.init_database()
        
        logger.info("Veritabanı başarıyla başlatıldı")
        return True
        
    except Exception as e:
        logger.error(f"Veritabanı test hatası: {e}")
        return False

def test_services():
    """Servisleri test eder"""
    logger.info("Servisler test ediliyor...")
    
    # BunnyCDN test
    try:
        from modules.bunnycdn_uploader import BunnyCDNUploader
        
        uploader = BunnyCDNUploader()
        if uploader.test_connection():
            logger.info("✓ BunnyCDN bağlantısı başarılı")
        else:
            logger.warning("✗ BunnyCDN bağlantısı başarısız")
    except Exception as e:
        logger.warning(f"BunnyCDN test hatası: {e}")
    
    # VPN test (opsiyonel)
    try:
        from modules.vpn_manager import VPNManager
        
        vpn = VPNManager()
        if vpn.check_protonvpn_cli():
            logger.info("✓ ProtonVPN CLI mevcut")
        else:
            logger.info("ℹ ProtonVPN CLI mevcut değil (opsiyonel)")
    except Exception as e:
        logger.warning(f"VPN test hatası: {e}")

def main():
    """Ana fonksiyon"""
    logger.info("=" * 50)
    logger.info("Film Yönetim Sistemi Başlatılıyor")
    logger.info("=" * 50)
    
    # Python sürümü kontrolü
    if not check_python_version():
        sys.exit(1)
    
    # Sistem bağımlılıkları
    missing_deps = check_system_dependencies()
    if missing_deps:
        logger.info(f"Eksik bağımlılıklar: {', '.join(missing_deps)}")
        
        response = input("Eksik bağımlılıkları kurmak ister misiniz? (y/N): ")
        if response.lower() in ['y', 'yes', 'evet']:
            if not install_system_dependencies(missing_deps):
                logger.error("Sistem bağımlılıkları kurulamadı")
                sys.exit(1)
        else:
            logger.warning("Bazı özellikler çalışmayabilir")
    
    # Python paketleri
    if not check_python_packages():
        logger.info("Python paketleri kuruluyor...")
        if not install_python_packages():
            logger.error("Python paketleri kurulamadı")
            sys.exit(1)
    
    # Klasör yapısı
    if not setup_directories():
        logger.error("Klasör yapısı oluşturulamadı")
        sys.exit(1)
    
    # Konfigürasyon
    if not check_configuration():
        logger.error("Konfigürasyon hatası - .env dosyasını kontrol edin")
        sys.exit(1)
    
    # Veritabanı
    if not test_database():
        logger.error("Veritabanı başlatılamadı")
        sys.exit(1)
    
    # Servis testleri
    test_services()
    
    logger.info("=" * 50)
    logger.info("Sistem başarıyla hazırlandı!")
    logger.info("=" * 50)
    
    # Flask uygulamasını başlat
    try:
        from app import app
        
        logger.info(f"Web arayüzü başlatılıyor: http://localhost:5000")
        logger.info("Durdurmak için Ctrl+C kullanın")
        
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=Config.DEBUG
        )
        
    except KeyboardInterrupt:
        logger.info("Uygulama kullanıcı tarafından durduruldu")
    except Exception as e:
        logger.error(f"Uygulama başlatma hatası: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()