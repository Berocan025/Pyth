@echo off
echo ================================================
echo Film Yonetim Sistemi - Windows Server 2022 Kurulumu
echo ================================================

:: Admin yetkisi kontrolü
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Bu scripti Administrator olarak calistirin!
    pause
    exit /b
)

:: Python kontrolü
echo Python kontrol ediliyor...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo Python bulunamadi! Python 3.8+ yuklemeniz gerekiyor.
    echo https://www.python.org/downloads/windows/ adresinden Python indirin
    pause
    exit /b
)

:: Python sürümü kontrolü
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set python_version=%%i
echo Python surum: %python_version%

:: Pip güncellemesi
echo Pip guncelleniyor...
python -m pip install --upgrade pip

:: Virtual environment oluşturma
echo Virtual environment olusturuluyor...
if exist venv rmdir /s /q venv
python -m venv venv

:: Virtual environment aktivasyonu
echo Virtual environment aktive ediliyor...
call venv\Scripts\activate.bat

:: Requirements kurulumu
echo Python paketleri kuruluyor...
pip install Flask==2.3.3
pip install requests==2.31.0
pip install beautifulsoup4==4.12.2
pip install yt-dlp==2023.12.30
pip install selenium==4.15.2
pip install webdriver-manager==4.0.1
pip install python-dotenv==1.0.0
pip install schedule==1.2.0
pip install psutil==5.9.6
pip install aiohttp==3.9.1
pip install lxml==4.9.3
pip install cloudscraper==1.2.71
pip install fake-useragent==1.4.0

:: FFmpeg kontrolü
echo FFmpeg kontrol ediliyor...
ffmpeg -version >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ===============================================
    echo UYARI: FFmpeg bulunamadi!
    echo ===============================================
    echo Video donusturme icin FFmpeg gerekli.
    echo 1. https://ffmpeg.org/download.html#build-windows
    echo 2. ffmpeg.exe dosyasini sistem PATH'ine ekleyin
    echo 3. Veya ffmpeg.exe'yi proje klasorune kopyalayin
    echo ===============================================
    echo.
)

:: Chrome/Edge WebDriver kontrolü
echo WebDriver kontrol ediliyor...
echo Chrome veya Edge browser'in yuklu oldugunu kontrol edin.

:: Klasor yapisi olusturma
echo Klasor yapisi olusturuluyor...
if not exist downloads mkdir downloads
if not exist logs mkdir logs
if not exist static\uploads mkdir static\uploads
if not exist instance mkdir instance

:: .env dosyasi kontrolu
if not exist .env (
    echo .env dosyasi olusturuluyor...
    copy .env.example .env
    echo.
    echo ===============================================
    echo ONEMLI: .env dosyasini duzenleyin!
    echo ===============================================
    echo 1. .env dosyasini not defteri ile acin
    echo 2. BunnyCDN bilgilerinizi girin
    echo 3. Film sitesi URL'sini belirleyin
    echo 4. Diger ayarlari yapin
    echo ===============================================
    echo.
)

:: Firewall kurali ekleme
echo Firewall kurali ekleniyor...
netsh advfirewall firewall add rule name="Film Yonetim Sistemi" dir=in action=allow protocol=TCP localport=5000 >nul 2>&1

echo.
echo ================================================
echo Kurulum tamamlandi!
echo ================================================
echo.
echo Sistem baslatmak icin: run_windows.bat
echo Web arayuzu: http://localhost:5000
echo.
echo ONEMLI ADIMLAR:
echo 1. .env dosyasini duzenleyin
echo 2. FFmpeg yukleyin (video donusturme icin)
echo 3. run_windows.bat ile sistemi baslatin
echo.
pause