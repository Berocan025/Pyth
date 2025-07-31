import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Uygulama konfigürasyon ayarları"""
    
    # Flask ayarları
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # BunnyCDN ayarları
    BUNNYCDN_STORAGE_ZONE_NAME = os.getenv('BUNNYCDN_STORAGE_ZONE_NAME', '')
    BUNNYCDN_ACCESS_KEY = os.getenv('BUNNYCDN_ACCESS_KEY', '')
    BUNNYCDN_REGION = os.getenv('BUNNYCDN_REGION', 'ny')  # ny, la, sg, etc.
    BUNNYCDN_BASE_URL = f"https://storage.bunnycdn.com/{BUNNYCDN_STORAGE_ZONE_NAME}"
    
    # ProtonVPN ayarları
    PROTONVPN_USERNAME = os.getenv('PROTONVPN_USERNAME', '')
    PROTONVPN_PASSWORD = os.getenv('PROTONVPN_PASSWORD', '')
    PROTONVPN_SERVER = os.getenv('PROTONVPN_SERVER', 'TR#1')  # Türkiye sunucusu
    
    # Film sitesi ayarları
    TARGET_MOVIE_SITE = os.getenv('TARGET_MOVIE_SITE', '')
    
    # İndirme ayarları
    DOWNLOAD_PATH = os.getenv('DOWNLOAD_PATH', './downloads')
    MAX_DOWNLOADS_PER_SESSION = int(os.getenv('MAX_DOWNLOADS_PER_SESSION', '20'))
    PREFERRED_QUALITY = os.getenv('PREFERRED_QUALITY', '1080p')
    
    # Database ayarları
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'movie_manager.db')
    
    # Log ayarları
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'movie_manager.log')
    
    @classmethod
    def validate_config(cls):
        """Konfigürasyon doğrulaması"""
        required_fields = [
            'BUNNYCDN_STORAGE_ZONE_NAME',
            'BUNNYCDN_ACCESS_KEY',
            'TARGET_MOVIE_SITE'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not getattr(cls, field):
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Eksik konfigürasyon alanları: {', '.join(missing_fields)}")
        
        return True