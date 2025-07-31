import subprocess
import time
import logging
import psutil
import requests
from typing import Optional, Dict
import os
import signal
from config import Config

logger = logging.getLogger(__name__)

class VPNManager:
    """ProtonVPN yönetim sınıfı"""
    
    def __init__(self):
        self.username = Config.PROTONVPN_USERNAME
        self.password = Config.PROTONVPN_PASSWORD
        self.server = Config.PROTONVPN_SERVER
        self.is_connected = False
        self.connection_process = None
        
    def check_protonvpn_cli(self) -> bool:
        """ProtonVPN CLI kurulu mu kontrol eder"""
        try:
            result = subprocess.run(['protonvpn-cli', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("ProtonVPN CLI bulundu")
                return True
            else:
                logger.warning("ProtonVPN CLI bulunamadı")
                return False
        except Exception as e:
            logger.error(f"ProtonVPN CLI kontrol hatası: {str(e)}")
            return False
    
    def install_protonvpn_cli(self) -> bool:
        """ProtonVPN CLI kurulumunu yapar"""
        try:
            logger.info("ProtonVPN CLI kuruluyor...")
            
            # Ubuntu/Debian için kurulum
            commands = [
                "wget -q -O - https://repo.protonvpn.com/debian/public_key.asc | sudo apt-key add -",
                "echo 'deb https://repo.protonvpn.com/debian stable main' | sudo tee /etc/apt/sources.list.d/protonvpn.list",
                "sudo apt update",
                "sudo apt install -y protonvpn"
            ]
            
            for cmd in commands:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    logger.error(f"Kurulum komutu başarısız: {cmd}")
                    logger.error(f"Hata: {result.stderr}")
                    return False
            
            logger.info("ProtonVPN CLI başarıyla kuruldu")
            return True
            
        except Exception as e:
            logger.error(f"ProtonVPN CLI kurulum hatası: {str(e)}")
            return False
    
    def setup_protonvpn(self) -> bool:
        """ProtonVPN ilk kurulumunu yapar"""
        try:
            if not self.username or not self.password:
                logger.error("ProtonVPN kullanıcı adı ve şifre gerekli")
                return False
            
            logger.info("ProtonVPN yapılandırılıyor...")
            
            # Giriş yap
            login_cmd = f"echo '{self.password}' | protonvpn-cli login {self.username}"
            result = subprocess.run(login_cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"ProtonVPN giriş hatası: {result.stderr}")
                return False
            
            logger.info("ProtonVPN başarıyla yapılandırıldı")
            return True
            
        except Exception as e:
            logger.error(f"ProtonVPN kurulum hatası: {str(e)}")
            return False
    
    def connect(self, server: Optional[str] = None) -> bool:
        """ProtonVPN'e bağlanır"""
        try:
            # Önce mevcut bağlantıyı kontrol et
            if self.is_connected:
                logger.info("Zaten VPN'e bağlı")
                return True
            
            # ProtonVPN CLI var mı kontrol et
            if not self.check_protonvpn_cli():
                logger.info("ProtonVPN CLI kuruluyor...")
                if not self.install_protonvpn_cli():
                    logger.error("ProtonVPN CLI kurulumu başarısız")
                    return self._fallback_openvpn_connection()
                
                # İlk kurulum
                if not self.setup_protonvpn():
                    return self._fallback_openvpn_connection()
            
            target_server = server or self.server
            logger.info(f"ProtonVPN'e bağlanılıyor: {target_server}")
            
            # Bağlan
            connect_cmd = f"protonvpn-cli c {target_server}"
            result = subprocess.run(connect_cmd, shell=True, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.is_connected = True
                logger.info(f"ProtonVPN bağlantısı başarılı: {target_server}")
                
                # IP adresini kontrol et
                time.sleep(5)
                new_ip = self.get_current_ip()
                if new_ip:
                    logger.info(f"Yeni IP adresi: {new_ip}")
                
                return True
            else:
                logger.error(f"ProtonVPN bağlantı hatası: {result.stderr}")
                return self._fallback_openvpn_connection()
                
        except Exception as e:
            logger.error(f"VPN bağlantı hatası: {str(e)}")
            return self._fallback_openvpn_connection()
    
    def _fallback_openvpn_connection(self) -> bool:
        """Alternatif OpenVPN bağlantısı"""
        try:
            logger.info("Alternatif OpenVPN bağlantısı deneniyor...")
            
            # OpenVPN kurulu mu kontrol et
            result = subprocess.run(['which', 'openvpn'], capture_output=True)
            if result.returncode != 0:
                logger.info("OpenVPN kuruluyor...")
                install_result = subprocess.run(['sudo', 'apt', 'install', '-y', 'openvpn'], 
                                              capture_output=True, timeout=300)
                if install_result.returncode != 0:
                    logger.error("OpenVPN kurulumu başarısız")
                    return False
            
            # ProtonVPN OpenVPN config dosyalarını indir
            config_url = "https://account.protonvpn.com/api/vpn/config?category=country&protocol=udp&tier=0&country=TR"
            
            # Bu alternatif yöntem daha karmaşık olduğu için şimdilik False döndürüyoruz
            # Gerçek uygulamada ProtonVPN config dosyaları kullanılabilir
            logger.warning("OpenVPN alternatif yöntemi henüz uygulanmadı")
            return False
            
        except Exception as e:
            logger.error(f"Alternatif VPN bağlantı hatası: {str(e)}")
            return False
    
    def disconnect(self) -> bool:
        """ProtonVPN bağlantısını keser"""
        try:
            if not self.is_connected:
                logger.info("Zaten VPN bağlantısı yok")
                return True
            
            logger.info("ProtonVPN bağlantısı kesiliyor...")
            
            # ProtonVPN CLI ile bağlantıyı kes
            result = subprocess.run(['protonvpn-cli', 'disconnect'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.is_connected = False
                logger.info("ProtonVPN bağlantısı başarıyla kesildi")
                
                # IP adresini kontrol et
                time.sleep(3)
                new_ip = self.get_current_ip()
                if new_ip:
                    logger.info(f"Gerçek IP adresi: {new_ip}")
                
                return True
            else:
                logger.error(f"ProtonVPN bağlantı kesme hatası: {result.stderr}")
                return self._force_disconnect()
                
        except Exception as e:
            logger.error(f"VPN bağlantı kesme hatası: {str(e)}")
            return self._force_disconnect()
    
    def _force_disconnect(self) -> bool:
        """Zorla VPN bağlantısını keser"""
        try:
            logger.info("Zorla VPN bağlantısı kesiliyor...")
            
            # ProtonVPN process'lerini bul ve öldür
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'protonvpn' in proc.info['name'].lower():
                        proc.kill()
                        logger.info(f"ProtonVPN process sonlandırıldı: {proc.info['pid']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # OpenVPN process'lerini bul ve öldür
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'openvpn' in proc.info['name'].lower():
                        proc.kill()
                        logger.info(f"OpenVPN process sonlandırıldı: {proc.info['pid']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Network interface'leri sıfırla
            subprocess.run(['sudo', 'killall', '-9', 'openvpn'], capture_output=True)
            subprocess.run(['sudo', 'ip', 'link', 'delete', 'proton0'], capture_output=True)
            
            self.is_connected = False
            logger.info("VPN bağlantısı zorla kesildi")
            return True
            
        except Exception as e:
            logger.error(f"Zorla bağlantı kesme hatası: {str(e)}")
            return False
    
    def get_current_ip(self) -> Optional[str]:
        """Mevcut IP adresini alır"""
        try:
            # Birden fazla servis dene
            services = [
                'https://api.ipify.org',
                'https://httpbin.org/ip',
                'https://icanhazip.com',
                'https://api.myip.com'
            ]
            
            for service in services:
                try:
                    response = requests.get(service, timeout=10)
                    response.raise_for_status()
                    
                    if 'ipify' in service:
                        return response.text.strip()
                    elif 'httpbin' in service:
                        return response.json().get('origin', '').split(',')[0].strip()
                    elif 'icanhazip' in service:
                        return response.text.strip()
                    elif 'myip' in service:
                        return response.json().get('ip', '').strip()
                        
                except Exception:
                    continue
            
            logger.warning("IP adresi alınamadı")
            return None
            
        except Exception as e:
            logger.error(f"IP adresi alma hatası: {str(e)}")
            return None
    
    def check_connection_status(self) -> Dict:
        """VPN bağlantı durumunu kontrol eder"""
        try:
            # ProtonVPN CLI status
            result = subprocess.run(['protonvpn-cli', 'status'], 
                                  capture_output=True, text=True, timeout=15)
            
            status_info = {
                'connected': self.is_connected,
                'ip_address': self.get_current_ip(),
                'server': None,
                'protocol': None,
                'country': None
            }
            
            if result.returncode == 0 and result.stdout:
                output = result.stdout.lower()
                
                if 'connected' in output or 'status: connected' in output:
                    self.is_connected = True
                    status_info['connected'] = True
                    
                    # Server bilgisini çıkar
                    for line in result.stdout.split('\n'):
                        if 'server:' in line.lower():
                            status_info['server'] = line.split(':')[1].strip()
                        elif 'protocol:' in line.lower():
                            status_info['protocol'] = line.split(':')[1].strip()
                        elif 'country:' in line.lower():
                            status_info['country'] = line.split(':')[1].strip()
                else:
                    self.is_connected = False
                    status_info['connected'] = False
            
            return status_info
            
        except Exception as e:
            logger.error(f"VPN durum kontrol hatası: {str(e)}")
            return {
                'connected': False,
                'ip_address': self.get_current_ip(),
                'server': None,
                'protocol': None,
                'country': None,
                'error': str(e)
            }
    
    def test_connection(self) -> bool:
        """VPN bağlantısını test eder"""
        try:
            # IP değişikliğini kontrol et
            original_ip = self.get_current_ip()
            
            if not self.connect():
                return False
            
            time.sleep(5)
            new_ip = self.get_current_ip()
            
            # IP değişti mi kontrol et
            if original_ip and new_ip and original_ip != new_ip:
                logger.info(f"VPN test başarılı: {original_ip} -> {new_ip}")
                return True
            else:
                logger.warning("VPN test başarısız: IP değişmedi")
                return False
                
        except Exception as e:
            logger.error(f"VPN test hatası: {str(e)}")
            return False
    
    def get_available_servers(self) -> list:
        """Kullanılabilir sunucuları listeler"""
        try:
            result = subprocess.run(['protonvpn-cli', 'list'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                servers = []
                for line in result.stdout.split('\n'):
                    if '#' in line and 'TR' in line:  # Türkiye sunucuları
                        servers.append(line.strip())
                return servers
            else:
                logger.warning("Sunucu listesi alınamadı")
                return ['TR#1', 'TR#2', 'TR#3']  # Varsayılan Türkiye sunucuları
                
        except Exception as e:
            logger.error(f"Sunucu listesi alma hatası: {str(e)}")
            return ['TR#1', 'TR#2', 'TR#3']