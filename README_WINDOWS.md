# Film Yönetim Sistemi - Windows Server 2022 Kurulum

Bu döküman Windows Server 2022 için özel kurulum talimatlarını içerir.

## 🖥️ Windows Server 2022 Gereksinimleri

- **Windows Server 2022** (veya Windows 10/11)
- **Python 3.8+** 
- **Administrator yetkileri**
- **İnternet bağlantısı**
- **Minimum 4GB RAM**
- **50GB+ boş disk alanı**

## 🚀 Hızlı Kurulum

### 1. Python Kurulumu

```powershell
# Python resmi sitesinden indirin:
# https://www.python.org/downloads/windows/
# "Add Python to PATH" seçeneğini işaretleyin!
```

### 2. Projeyi İndirin

```powershell
# Git ile (önerilen)
git clone https://github.com/username/film-yonetim-sistemi.git
cd film-yonetim-sistemi

# Veya ZIP olarak indirip açın
```

### 3. Otomatik Kurulum

```batch
# Administrator olarak Command Prompt açın
# Proje klasörüne gidin ve çalıştırın:
install_windows.bat
```

### 4. Konfigürasyon

`.env` dosyasını düzenleyin:

```env
# BunnyCDN ayarları (ZORUNLU)
BUNNYCDN_STORAGE_ZONE_NAME=your-storage-zone-name
BUNNYCDN_ACCESS_KEY=your-bunnycdn-access-key
BUNNYCDN_REGION=ny

# Film sitesi
TARGET_MOVIE_SITE=https://example-movie-site.com

# ProtonVPN (opsiyonel)
PROTONVPN_USERNAME=your-username
PROTONVPN_PASSWORD=your-password
```

### 5. Sistemi Başlatın

```batch
run_windows.bat
```

Web arayüzü: **http://localhost:5000**

## 🔧 Manuel Kurulum

### Python ve Pip Kurulumu

1. **Python İndirin:**
   - https://www.python.org/downloads/windows/
   - "Add Python to PATH" seçeneğini işaretleyin
   - Python 3.8+ sürümünü kurun

2. **Kurulumu Doğrulayın:**
```powershell
python --version
pip --version
```

### Proje Kurulumu

1. **Virtual Environment:**
```powershell
python -m venv venv
venv\Scripts\activate
```

2. **Paketleri Kurun:**
```powershell
pip install -r requirements.txt
```

### Sistem Bağımlılıkları

#### FFmpeg (Video Dönüştürme)

1. **FFmpeg İndirin:**
   - https://www.gyan.dev/ffmpeg/builds/
   - "ffmpeg-master-latest-win64-gpl.zip" indirin

2. **Kurulum:**
   - Zip'i açın
   - `bin\ffmpeg.exe` dosyasını proje klasörüne kopyalayın
   - Veya sistem PATH'ine ekleyin

3. **Test:**
```powershell
ffmpeg -version
```

#### Chrome/Edge WebDriver

Sistem otomatik olarak arayacaktır:
- Google Chrome
- Microsoft Edge

En az birinin kurulu olması gerekir.

## 🛡️ ProtonVPN Kurulumu (Opsiyonel)

### 1. ProtonVPN Windows Uygulaması

1. **İndirin:**
   - https://protonvpn.com/download
   - Windows uygulamasını kurun

2. **Konfigürasyon:**
   - Hesabınızla giriş yapın
   - Türkiye sunucularını aktif edin

3. **Manuel Bağlantı:**
   - Film indirme sırasında manuel olarak Türkiye'ye bağlanın
   - Sistem VPN durumunu otomatik algılayacaktır

## 🔥 Firewall Ayarları

### Windows Defender Firewall

Kurulum scripti otomatik olarak ekler, manuel için:

```powershell
# PowerShell (Administrator)
New-NetFirewallRule -DisplayName "Film Yonetim Sistemi" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

### Port 5000 Açık Olmalı

- **Gelen Bağlantılar:** Port 5000 TCP
- **Web Arayüzü:** http://localhost:5000

## 📁 Dizin Yapısı

```
C:\film-yonetim-sistemi\
├── install_windows.bat    # Kurulum scripti
├── run_windows.bat        # Çalıştırma scripti
├── app.py                 # Ana uygulama
├── .env                   # Konfigürasyon
├── venv\                  # Virtual environment
├── downloads\             # İndirilen filmler
├── logs\                  # Log dosyaları
├── ffmpeg.exe            # FFmpeg (opsiyonel)
└── modules\              # Python modülleri
```

## 🚨 Yaygın Sorunlar

### 1. Python Bulunamadı

```bash
# Hata: 'python' is not recognized
```

**Çözüm:**
- Python'u yeniden kurun
- "Add Python to PATH" seçeneğini işaretleyin
- Bilgisayarı yeniden başlatın

### 2. Pip Install Hatası

```bash
# Hata: Microsoft Visual C++ 14.0 is required
```

**Çözüm:**
- https://visualstudio.microsoft.com/visual-cpp-build-tools/
- "C++ build tools" kurun

### 3. FFmpeg Bulunamadı

```bash
# Hata: ffmpeg.exe bulunamadı
```

**Çözüm:**
- FFmpeg'i indirin: https://www.gyan.dev/ffmpeg/builds/
- `ffmpeg.exe`'yi proje klasörüne koyun
- Veya sistem PATH'ine ekleyin

### 4. Chrome/Edge Bulunamadı

**Çözüm:**
- Google Chrome veya Microsoft Edge kurun
- En az birinin kurulu olması yeterli

### 5. BunnyCDN Bağlantı Hatası

**Çözüm:**
- `.env` dosyasındaki bilgileri kontrol edin
- Storage Zone adını doğrulayın
- Access Key'in doğru olduğundan emin olun

### 6. Port 5000 Kullanımda

```bash
# Hata: [Errno 10048] Only one usage of each socket address
```

**Çözüm:**
```powershell
# Portu kullanan uygulamayı bulun
netstat -ano | findstr :5000

# Process'i sonlandırın
taskkill /PID <PID_NUMBER> /F
```

## 🔧 İleri Seviye Ayarlar

### IIS ile Production

```xml
<!-- web.config -->
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <system.webServer>
    <handlers>
      <add name="Python FastCGI" path="*" verb="*" 
           modules="FastCgiModule" 
           scriptProcessor="C:\film-yonetim-sistemi\venv\Scripts\python.exe|C:\film-yonetim-sistemi\app.py" 
           resourceType="Unspecified" />
    </handlers>
  </system.webServer>
</configuration>
```

### Windows Service Olarak Çalıştırma

```python
# service.py
import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import os

class FilmYonetimService(win32serviceutil.ServiceFramework):
    _svc_name_ = "FilmYonetimSistemi"
    _svc_display_name_ = "Film Yönetim Sistemi"
    _svc_description_ = "Otomatik film indirme ve CDN yükleme servisi"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        
        # Film yönetim sistemini başlat
        os.chdir(r"C:\film-yonetim-sistemi")
        subprocess.call([r"venv\Scripts\python.exe", "app.py"])

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(FilmYonetimService)
```

### Görev Zamanlayıcısı

```xml
<!-- task.xml -->
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2">
  <RegistrationInfo>
    <Description>Film Yönetim Sistemi Otomatik Başlatma</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
    </BootTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>C:\film-yonetim-sistemi\run_windows.bat</Command>
      <WorkingDirectory>C:\film-yonetim-sistemi</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

## 📊 Performans Optimizasyonu

### Windows Server Ayarları

```powershell
# Disk performansı
fsutil behavior set DisableLastAccess 1

# Network optimizasyonu
netsh int tcp set global autotuninglevel=normal

# Memory ayarları
bcdedit /set increaseuserva 3072
```

### Güvenlik Ayarları

```powershell
# Windows Update devre dışı (opsiyonel)
sc config wuauserv start= disabled

# Unnecessary services durdur
sc config "Fax" start= disabled
sc config "Windows Search" start= disabled
```

## 📝 Log ve Monitoring

### Log Dosyaları

- **Sistem Log:** `logs\system.log`
- **Flask Log:** `movie_manager.log`
- **Windows Event Log:** Event Viewer

### Monitoring Script

```powershell
# monitor.ps1
while ($true) {
    $process = Get-Process python -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-Host "Sistem durdu, yeniden başlatılıyor..."
        Start-Process -FilePath "run_windows.bat" -WorkingDirectory "C:\film-yonetim-sistemi"
    }
    Start-Sleep -Seconds 30
}
```

## 🆘 Destek

### Log Toplama

```batch
# logs_topla.bat
@echo off
mkdir support_logs
copy logs\*.log support_logs\
copy *.log support_logs\
systeminfo > support_logs\system_info.txt
python --version > support_logs\python_version.txt
pip list > support_logs\installed_packages.txt
echo Loglar support_logs\ klasorunde toplandi
```

### Sistem Bilgileri

```powershell
# Sistem durumu kontrolü
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, TotalPhysicalMemory
Get-Process python
netstat -an | findstr 5000
```

## 🔄 Güncelleme

```batch
# update.bat
git pull
venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

---

## 📞 Windows Özel Destek

**Windows Server sorunları için:**
- Event Viewer loglarını kontrol edin
- PowerShell ISE kullanarak script'leri test edin
- Process Monitor ile dosya erişimlerini izleyin

**Faydalı Komutlar:**
```powershell
# Servis durumu
Get-Service | Where-Object {$_.Name -like "*python*"}

# Port kullanımı
Get-NetTCPConnection -LocalPort 5000

# Disk alanı
Get-PSDrive C

# Memory kullanımı
Get-Process python | Measure-Object WorkingSet -Sum
```