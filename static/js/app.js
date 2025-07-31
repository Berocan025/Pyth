// Film Yönetim Sistemi - Ana JavaScript Dosyası

// Global değişkenler
let app = {
    statusUpdateInterval: null,
    isProcessing: false,
    config: {
        updateInterval: 2000,
        maxRetries: 3,
        retryDelay: 1000
    }
};

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', function() {
    app.init();
});

// Ana başlatma fonksiyonu
app.init = function() {
    console.log('Film Yönetim Sistemi başlatılıyor...');
    
    // Event listener'ları ekle
    app.attachEventListeners();
    
    // Otomatik durum güncellemesini başlat
    app.startStatusUpdates();
    
    // Sayfa gizlenme/görünme olaylarını dinle
    document.addEventListener('visibilitychange', app.handleVisibilityChange);
    
    // Klavye kısayollarını ekle
    app.setupKeyboardShortcuts();
    
    console.log('Sistem başarıyla başlatıldı');
};

// Event listener'ları ekle
app.attachEventListeners = function() {
    // Form submit olayları
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', app.handleFormSubmit);
    });
    
    // Button click olayları
    document.querySelectorAll('[data-action]').forEach(button => {
        button.addEventListener('click', app.handleActionClick);
    });
    
    // Modal olayları
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('shown.bs.modal', app.handleModalShown);
        modal.addEventListener('hidden.bs.modal', app.handleModalHidden);
    });
};

// Form submit işleme
app.handleFormSubmit = function(event) {
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    
    if (submitButton) {
        app.setButtonLoading(submitButton, true);
        
        // Form submit işlemi tamamlandıktan sonra loading durumunu kaldır
        setTimeout(() => {
            app.setButtonLoading(submitButton, false);
        }, 2000);
    }
};

// Action button click işleme
app.handleActionClick = function(event) {
    const button = event.target.closest('[data-action]');
    const action = button.getAttribute('data-action');
    
    switch(action) {
        case 'start-processing':
            app.startProcessing();
            break;
        case 'stop-processing':
            app.stopProcessing();
            break;
        case 'test-vpn':
            app.testVPN();
            break;
        case 'test-cdn':
            app.testCDN();
            break;
        case 'refresh-status':
            app.refreshStatus();
            break;
        case 'cleanup-files':
            app.cleanupFiles();
            break;
        default:
            console.warn('Bilinmeyen action:', action);
    }
};

// Modal gösterildiğinde
app.handleModalShown = function(event) {
    const modal = event.target;
    const focusElement = modal.querySelector('[autofocus]');
    if (focusElement) {
        focusElement.focus();
    }
};

// Modal gizlendiğinde
app.handleModalHidden = function(event) {
    // Modal kapatıldığında form verilerini temizle
    const forms = event.target.querySelectorAll('form');
    forms.forEach(form => form.reset());
};

// Sayfa görünürlük değişikliği
app.handleVisibilityChange = function() {
    if (document.hidden) {
        app.stopStatusUpdates();
    } else {
        app.startStatusUpdates();
    }
};

// Klavye kısayolları
app.setupKeyboardShortcuts = function() {
    document.addEventListener('keydown', function(event) {
        // Ctrl+Enter: İşlemi başlat
        if (event.ctrlKey && event.key === 'Enter') {
            if (!app.isProcessing) {
                app.startProcessing();
            }
            event.preventDefault();
        }
        
        // Escape: İşlemi durdur
        if (event.key === 'Escape' && app.isProcessing) {
            app.stopProcessing();
            event.preventDefault();
        }
        
        // F5: Durumu yenile (varsayılan F5'i engelle)
        if (event.key === 'F5') {
            app.refreshStatus();
            event.preventDefault();
        }
    });
};

// API çağrıları
app.api = {
    // Generic API çağrısı
    call: function(endpoint, options = {}) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        const finalOptions = { ...defaultOptions, ...options };
        
        return fetch(endpoint, finalOptions)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('API Hatası:', error);
                app.showAlert('Bağlantı hatası: ' + error.message, 'error');
                throw error;
            });
    },
    
    // İşlemi başlat
    startProcessing: function() {
        return this.call('/api/start_processing', { method: 'POST' });
    },
    
    // İşlemi durdur
    stopProcessing: function() {
        return this.call('/api/stop_processing', { method: 'POST' });
    },
    
    // Durum al
    getStatus: function() {
        return this.call('/api/status');
    },
    
    // Ayarları güncelle
    updateSettings: function(settings) {
        return this.call('/api/update_settings', {
            method: 'POST',
            body: JSON.stringify(settings)
        });
    }
};

// İşlem yönetimi
app.startProcessing = function() {
    const button = document.getElementById('start-btn');
    if (button) app.setButtonLoading(button, true);
    
    app.api.startProcessing()
        .then(data => {
            if (data.success) {
                app.isProcessing = true;
                app.updateUIState();
                app.showAlert('İşlem başlatıldı!', 'success');
            } else {
                app.showAlert('Hata: ' + data.message, 'error');
            }
        })
        .catch(error => {
            app.showAlert('İşlem başlatılamadı: ' + error.message, 'error');
        })
        .finally(() => {
            if (button) app.setButtonLoading(button, false);
        });
};

app.stopProcessing = function() {
    const button = document.getElementById('stop-btn');
    if (button) app.setButtonLoading(button, true);
    
    app.api.stopProcessing()
        .then(data => {
            if (data.success) {
                app.isProcessing = false;
                app.updateUIState();
                app.showAlert('İşlem durduruldu!', 'warning');
            } else {
                app.showAlert('Hata: ' + data.message, 'error');
            }
        })
        .catch(error => {
            app.showAlert('İşlem durdurulamadı: ' + error.message, 'error');
        })
        .finally(() => {
            if (button) app.setButtonLoading(button, false);
        });
};

// UI durum güncellemesi
app.updateUIState = function() {
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const progressSection = document.getElementById('progress-section');
    const statusBadge = document.getElementById('status-badge');
    
    if (app.isProcessing) {
        if (startBtn) startBtn.disabled = true;
        if (stopBtn) stopBtn.disabled = false;
        if (progressSection) progressSection.style.display = 'block';
        if (statusBadge) {
            statusBadge.className = 'badge bg-warning';
            statusBadge.textContent = 'İşleniyor';
        }
    } else {
        if (startBtn) startBtn.disabled = false;
        if (stopBtn) stopBtn.disabled = true;
        if (progressSection) progressSection.style.display = 'none';
        if (statusBadge) {
            statusBadge.className = 'badge bg-success';
            statusBadge.textContent = 'Hazır';
        }
    }
};

// Durum güncellemeleri
app.startStatusUpdates = function() {
    if (app.statusUpdateInterval) {
        clearInterval(app.statusUpdateInterval);
    }
    
    app.statusUpdateInterval = setInterval(() => {
        app.updateStatus();
    }, app.config.updateInterval);
    
    // İlk güncellemeyi hemen yap
    app.updateStatus();
};

app.stopStatusUpdates = function() {
    if (app.statusUpdateInterval) {
        clearInterval(app.statusUpdateInterval);
        app.statusUpdateInterval = null;
    }
};

app.updateStatus = function() {
    app.api.getStatus()
        .then(data => {
            app.isProcessing = data.is_running;
            app.updateUIState();
            
            // İlerleme güncelle
            if (data.is_running && data.total_movies > 0) {
                const progress = Math.round((data.processed_movies / data.total_movies) * 100);
                app.updateProgress(progress);
            }
            
            // Adım güncelle
            app.updateCurrentStep(data.current_step || 'Beklemede...');
            
            // İstatistikleri güncelle
            app.updateStatistics({
                total: data.total_movies || 0,
                processed: data.processed_movies || 0,
                errors: data.errors ? data.errors.length : 0
            });
            
            // Son güncelleme zamanı
            if (data.last_update) {
                app.updateLastUpdateTime(data.last_update);
            }
            
            // Hataları güncelle
            if (data.errors && data.errors.length > 0) {
                app.updateErrorLog(data.errors);
            }
        })
        .catch(error => {
            console.error('Durum güncelleme hatası:', error);
        });
};

// UI güncelleme fonksiyonları
app.updateProgress = function(percentage) {
    const progressBar = document.getElementById('progress-bar');
    if (progressBar) {
        progressBar.style.width = percentage + '%';
        progressBar.textContent = percentage + '%';
        progressBar.setAttribute('aria-valuenow', percentage);
    }
};

app.updateCurrentStep = function(step) {
    const currentStep = document.getElementById('current-step');
    if (currentStep) {
        currentStep.textContent = step;
    }
};

app.updateStatistics = function(stats) {
    const totalMovies = document.getElementById('total-movies');
    const processedMovies = document.getElementById('processed-movies');
    const errorCount = document.getElementById('error-count');
    
    if (totalMovies) totalMovies.textContent = stats.total;
    if (processedMovies) processedMovies.textContent = stats.processed;
    if (errorCount) errorCount.textContent = stats.errors;
};

app.updateLastUpdateTime = function(timestamp) {
    const lastUpdate = document.getElementById('last-update');
    if (lastUpdate) {
        const date = new Date(timestamp);
        lastUpdate.textContent = date.toLocaleString('tr-TR');
    }
};

app.updateErrorLog = function(errors) {
    const errorLog = document.getElementById('error-log');
    const errorList = document.getElementById('error-list');
    
    if (errorLog && errorList) {
        if (errors.length > 0) {
            errorLog.style.display = 'block';
            errorList.innerHTML = '';
            
            errors.slice(-5).forEach(error => {
                const item = document.createElement('div');
                item.className = 'list-group-item';
                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong class="text-danger">${app.escapeHtml(error.message)}</strong>
                        </div>
                        <small class="text-muted">${new Date(error.time).toLocaleString('tr-TR')}</small>
                    </div>
                `;
                errorList.appendChild(item);
            });
        } else {
            errorLog.style.display = 'none';
        }
    }
};

// Test fonksiyonları
app.testVPN = function() {
    app.showAlert('VPN bağlantısı test ediliyor...', 'info');
    // VPN test implementasyonu burada olacak
};

app.testCDN = function() {
    app.showAlert('BunnyCDN bağlantısı test ediliyor...', 'info');
    // CDN test implementasyonu burada olacak
};

app.cleanupFiles = function() {
    if (confirm('Tüm geçici dosyalar silinecek. Emin misiniz?')) {
        app.showAlert('Dosyalar temizleniyor...', 'info');
        // Cleanup implementasyonu burada olacak
    }
};

app.refreshStatus = function() {
    app.updateStatus();
    app.showAlert('Durum yenilendi!', 'info');
};

// Utility fonksiyonlar
app.setButtonLoading = function(button, loading) {
    if (!button) return;
    
    if (loading) {
        button.disabled = true;
        const originalText = button.innerHTML;
        button.setAttribute('data-original-text', originalText);
        button.innerHTML = '<span class="loading-spinner me-2"></span>Yükleniyor...';
    } else {
        button.disabled = false;
        const originalText = button.getAttribute('data-original-text');
        if (originalText) {
            button.innerHTML = originalText;
            button.removeAttribute('data-original-text');
        }
    }
};

app.showAlert = function(message, type = 'info', duration = 5000) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${app.escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Container'ı bul ve alert'i ekle
    const container = document.querySelector('main .container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Otomatik gizle
        if (duration > 0) {
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, duration);
        }
    }
};

app.escapeHtml = function(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
};

app.formatFileSize = function(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

app.formatDuration = function(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    
    if (hours > 0) {
        return `${hours}s ${minutes}dk ${remainingSeconds}sn`;
    } else if (minutes > 0) {
        return `${minutes}dk ${remainingSeconds}sn`;
    } else {
        return `${remainingSeconds}sn`;
    }
};

// Local Storage yönetimi
app.storage = {
    set: function(key, value) {
        try {
            localStorage.setItem('movie_manager_' + key, JSON.stringify(value));
        } catch (error) {
            console.warn('Local storage yazma hatası:', error);
        }
    },
    
    get: function(key, defaultValue = null) {
        try {
            const item = localStorage.getItem('movie_manager_' + key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.warn('Local storage okuma hatası:', error);
            return defaultValue;
        }
    },
    
    remove: function(key) {
        try {
            localStorage.removeItem('movie_manager_' + key);
        } catch (error) {
            console.warn('Local storage silme hatası:', error);
        }
    }
};

// Sayfa ayrılmadan önce temizlik
window.addEventListener('beforeunload', function() {
    app.stopStatusUpdates();
});

// Global app nesnesini window'a ekle
window.MovieManagerApp = app;