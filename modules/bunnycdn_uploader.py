import os
import requests
import logging
from typing import Dict, Optional
import hashlib
import time
from pathlib import Path
import mimetypes
from config import Config

logger = logging.getLogger(__name__)

class BunnyCDNUploader:
    """BunnyCDN yükleme yönetim sınıfı"""
    
    def __init__(self):
        self.storage_zone_name = Config.BUNNYCDN_STORAGE_ZONE_NAME
        self.access_key = Config.BUNNYCDN_ACCESS_KEY
        self.region = Config.BUNNYCDN_REGION
        
        # API endpoint'leri
        self.base_url = f"https://storage.bunnycdn.com/{self.storage_zone_name}"
        self.cdn_url = f"https://{self.storage_zone_name}.b-cdn.net"
        
        # Headers
        self.headers = {
            'AccessKey': self.access_key,
            'Content-Type': 'application/octet-stream'
        }
        
    def upload_file(self, file_path: str, movie_title: str) -> Dict:
        """Dosyayı BunnyCDN'e yükler"""
        try:
            if not os.path.exists(file_path):
                return {'success': False, 'error': 'Dosya bulunamadı'}
            
            if not self.storage_zone_name or not self.access_key:
                return {'success': False, 'error': 'BunnyCDN konfigürasyonu eksik'}
            
            logger.info(f"BunnyCDN'e yükleniyor: {movie_title}")
            
            # Dosya bilgilerini al
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            # Güvenli dosya adı oluştur
            safe_filename = self._sanitize_filename(f"{movie_title}.mp4")
            
            # Klasör yapısı oluştur (yıl/ay bazında)
            upload_path = self._generate_upload_path(safe_filename)
            
            logger.info(f"Yükleme yolu: {upload_path}")
            logger.info(f"Dosya boyutu: {file_size / (1024*1024):.1f} MB")
            
            # Büyük dosyalar için chunked upload
            if file_size > 100 * 1024 * 1024:  # 100MB üzeri
                return self._upload_large_file(file_path, upload_path)
            else:
                return self._upload_small_file(file_path, upload_path)
                
        except Exception as e:
            logger.error(f"BunnyCDN yükleme hatası: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _upload_small_file(self, file_path: str, upload_path: str) -> Dict:
        """Küçük dosyayı tek seferde yükler"""
        try:
            url = f"{self.base_url}/{upload_path}"
            
            with open(file_path, 'rb') as file:
                response = requests.put(
                    url,
                    data=file,
                    headers=self.headers,
                    timeout=3600  # 1 saat timeout
                )
            
            if response.status_code in [200, 201]:
                cdn_url = f"{self.cdn_url}/{upload_path}"
                logger.info(f"Dosya başarıyla yüklendi: {cdn_url}")
                
                return {
                    'success': True,
                    'cdn_url': cdn_url,
                    'upload_path': upload_path,
                    'file_size': os.path.getsize(file_path)
                }
            else:
                logger.error(f"BunnyCDN yükleme hatası: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Küçük dosya yükleme hatası: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _upload_large_file(self, file_path: str, upload_path: str) -> Dict:
        """Büyük dosyayı parçalar halinde yükler"""
        try:
            logger.info("Büyük dosya için chunked upload başlıyor...")
            
            chunk_size = 10 * 1024 * 1024  # 10MB chunks
            file_size = os.path.getsize(file_path)
            total_chunks = (file_size + chunk_size - 1) // chunk_size
            
            url = f"{self.base_url}/{upload_path}"
            
            with open(file_path, 'rb') as file:
                for chunk_num in range(total_chunks):
                    start_byte = chunk_num * chunk_size
                    end_byte = min(start_byte + chunk_size - 1, file_size - 1)
                    
                    file.seek(start_byte)
                    chunk_data = file.read(chunk_size)
                    
                    # Range header ekle
                    chunk_headers = self.headers.copy()
                    chunk_headers['Content-Range'] = f"bytes {start_byte}-{end_byte}/{file_size}"
                    chunk_headers['Content-Length'] = str(len(chunk_data))
                    
                    logger.info(f"Chunk {chunk_num + 1}/{total_chunks} yükleniyor...")
                    
                    response = requests.put(
                        url,
                        data=chunk_data,
                        headers=chunk_headers,
                        timeout=1800  # 30 dakika timeout
                    )
                    
                    if response.status_code not in [200, 201, 206]:
                        logger.error(f"Chunk yükleme hatası: {response.status_code}")
                        return {
                            'success': False,
                            'error': f"Chunk {chunk_num + 1} yüklenemedi: {response.status_code}"
                        }
                    
                    # İlerleme göster
                    progress = ((chunk_num + 1) / total_chunks) * 100
                    logger.info(f"İlerleme: {progress:.1f}%")
            
            cdn_url = f"{self.cdn_url}/{upload_path}"
            logger.info(f"Büyük dosya başarıyla yüklendi: {cdn_url}")
            
            return {
                'success': True,
                'cdn_url': cdn_url,
                'upload_path': upload_path,
                'file_size': file_size
            }
            
        except Exception as e:
            logger.error(f"Büyük dosya yükleme hatası: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _sanitize_filename(self, filename: str) -> str:
        """Dosya adını güvenli hale getirir"""
        # Türkçe karakterleri değiştir
        replacements = {
            'ş': 's', 'ğ': 'g', 'ü': 'u', 'ç': 'c', 'ı': 'i', 'ö': 'o',
            'Ş': 'S', 'Ğ': 'G', 'Ü': 'U', 'Ç': 'C', 'İ': 'I', 'Ö': 'O'
        }
        
        for old, new in replacements.items():
            filename = filename.replace(old, new)
        
        # Geçersiz karakterleri kaldır
        import re
        filename = re.sub(r'[<>:"/\\|?*\s]', '_', filename)
        filename = re.sub(r'_+', '_', filename)  # Çoklu alt çizgileri tek yap
        filename = filename.strip('_')
        
        return filename
    
    def _generate_upload_path(self, filename: str) -> str:
        """Yükleme yolu oluşturur"""
        from datetime import datetime
        
        now = datetime.now()
        year = now.strftime('%Y')
        month = now.strftime('%m')
        
        # movies/2024/01/filename.mp4 formatı
        return f"movies/{year}/{month}/{filename}"
    
    def delete_file(self, upload_path: str) -> bool:
        """Dosyayı BunnyCDN'den siler"""
        try:
            url = f"{self.base_url}/{upload_path}"
            
            response = requests.delete(url, headers={'AccessKey': self.access_key})
            
            if response.status_code in [200, 204]:
                logger.info(f"Dosya silindi: {upload_path}")
                return True
            else:
                logger.error(f"Dosya silme hatası: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Dosya silme hatası: {str(e)}")
            return False
    
    def list_files(self, path: str = "") -> Dict:
        """Dosyaları listeler"""
        try:
            url = f"{self.base_url}/{path}" if path else self.base_url
            
            response = requests.get(url, headers={'AccessKey': self.access_key})
            
            if response.status_code == 200:
                files = response.json()
                return {'success': True, 'files': files}
            else:
                logger.error(f"Dosya listeleme hatası: {response.status_code}")
                return {'success': False, 'error': f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Dosya listeleme hatası: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_file_info(self, upload_path: str) -> Dict:
        """Dosya bilgilerini alır"""
        try:
            url = f"{self.base_url}/{upload_path}"
            
            response = requests.head(url, headers={'AccessKey': self.access_key})
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'size': int(response.headers.get('Content-Length', 0)),
                    'last_modified': response.headers.get('Last-Modified'),
                    'content_type': response.headers.get('Content-Type'),
                    'cdn_url': f"{self.cdn_url}/{upload_path}"
                }
            else:
                return {'success': False, 'error': f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Dosya bilgi alma hatası: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def test_connection(self) -> bool:
        """BunnyCDN bağlantısını test eder"""
        try:
            # Test dosyası oluştur
            test_content = b"BunnyCDN connection test"
            test_filename = f"test_{int(time.time())}.txt"
            
            url = f"{self.base_url}/{test_filename}"
            
            # Test dosyasını yükle
            response = requests.put(
                url,
                data=test_content,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                # Test dosyasını sil
                self.delete_file(test_filename)
                logger.info("BunnyCDN bağlantı testi başarılı")
                return True
            else:
                logger.error(f"BunnyCDN bağlantı testi başarısız: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"BunnyCDN bağlantı test hatası: {str(e)}")
            return False
    
    def get_storage_info(self) -> Dict:
        """Storage zone bilgilerini alır"""
        try:
            # BunnyCDN API kullanarak storage zone bilgilerini al
            api_url = "https://api.bunny.net/storagezone"
            api_headers = {
                'AccessKey': self.access_key,
                'Content-Type': 'application/json'
            }
            
            response = requests.get(api_url, headers=api_headers, timeout=30)
            
            if response.status_code == 200:
                zones = response.json()
                
                # Mevcut zone'u bul
                current_zone = None
                for zone in zones:
                    if zone.get('Name') == self.storage_zone_name:
                        current_zone = zone
                        break
                
                if current_zone:
                    return {
                        'success': True,
                        'name': current_zone.get('Name'),
                        'used_storage': current_zone.get('StorageUsed', 0),
                        'files_count': current_zone.get('FilesCount', 0),
                        'region': current_zone.get('Region'),
                        'custom_404_file_path': current_zone.get('Custom404FilePath')
                    }
                else:
                    return {'success': False, 'error': 'Storage zone bulunamadı'}
            else:
                return {'success': False, 'error': f"API hatası: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Storage bilgi alma hatası: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_directory(self, path: str) -> bool:
        """Klasör oluşturur"""
        try:
            url = f"{self.base_url}/{path}/"
            
            response = requests.put(
                url,
                headers={'AccessKey': self.access_key},
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Klasör oluşturuldu: {path}")
                return True
            else:
                logger.error(f"Klasör oluşturma hatası: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Klasör oluşturma hatası: {str(e)}")
            return False
    
    def get_download_url(self, upload_path: str, expire_hours: int = 24) -> str:
        """İndirme URL'si oluşturur"""
        try:
            # Basit CDN URL (güvenlik token'ı olmadan)
            cdn_url = f"{self.cdn_url}/{upload_path}"
            
            # Eğer güvenlik token'ı gerekiyorsa, burada oluşturulabilir
            # Şimdilik basit URL döndürüyoruz
            
            return cdn_url
            
        except Exception as e:
            logger.error(f"Download URL oluşturma hatası: {str(e)}")
            return ""
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Dosyanın MD5 hash'ini hesaplar"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Hash hesaplama hatası: {str(e)}")
            return ""
    
    def verify_upload(self, file_path: str, upload_path: str) -> bool:
        """Yüklenen dosyanın doğruluğunu kontrol eder"""
        try:
            # Yerel dosya hash'i
            local_hash = self.calculate_file_hash(file_path)
            if not local_hash:
                return False
            
            # Remote dosya bilgilerini al
            file_info = self.get_file_info(upload_path)
            if not file_info['success']:
                return False
            
            # Dosya boyutlarını karşılaştır
            local_size = os.path.getsize(file_path)
            remote_size = file_info['size']
            
            if local_size == remote_size:
                logger.info("Dosya boyutları eşleşiyor, yükleme doğrulandı")
                return True
            else:
                logger.error(f"Dosya boyutları eşleşmiyor: {local_size} != {remote_size}")
                return False
                
        except Exception as e:
            logger.error(f"Upload doğrulama hatası: {str(e)}")
            return False
    
    def get_cdn_stats(self) -> Dict:
        """CDN istatistiklerini alır"""
        try:
            # Bu özellik BunnyCDN API'si ile geliştirilebilir
            # Şimdilik basit bilgiler döndürüyoruz
            return {
                'success': True,
                'storage_zone': self.storage_zone_name,
                'region': self.region,
                'cdn_url': self.cdn_url
            }
            
        except Exception as e:
            logger.error(f"CDN stats hatası: {str(e)}")
            return {'success': False, 'error': str(e)}