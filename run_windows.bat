@echo off
title Film Yonetim Sistemi - Windows Server 2022

echo ================================================
echo Film Yonetim Sistemi Baslatiliyor...
echo ================================================

:: Virtual environment kontrolü
if not exist venv (
    echo HATA: Virtual environment bulunamadi!
    echo Once install_windows.bat dosyasini calistirin.
    pause
    exit /b
)

:: Virtual environment aktivasyonu
echo Virtual environment aktive ediliyor...
call venv\Scripts\activate.bat

:: Python ve modülleri kontrol et
echo Sistem kontrolleri yapiliyor...
python -c "import flask; print('Flask:', flask.__version__)" 2>nul
if %errorLevel% neq 0 (
    echo HATA: Flask modulu bulunamadi!
    echo install_windows.bat dosyasini tekrar calistirin.
    pause
    exit /b
)

:: .env dosyası kontrolü
if not exist .env (
    echo UYARI: .env dosyasi bulunamadi!
    echo .env.example dosyasini .env olarak kopyalayin ve duzenleyin.
    pause
    exit /b
)

:: Downloads klasörü kontrolü
if not exist downloads mkdir downloads

:: Log dosyası başlatma
echo %date% %time% - Sistem baslatiliyor >> logs\system.log

:: Ana uygulama başlatma
echo.
echo ================================================
echo Web arayuzu baslatiliyor...
echo ================================================
echo.
echo URL: http://localhost:5000
echo Durdurmak icin: Ctrl+C
echo.

:: Flask uygulamasını başlat
python app.py

echo.
echo Uygulama sonlandirildi.
echo Log dosyasi: logs\system.log
pause