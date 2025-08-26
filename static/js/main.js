// Main JavaScript functionality for CV Optimizer Pro

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupFormValidation();
    setupFileUpload();
    setupToastSystem();
    setupAnimations();
});

/**
 * Initialize the application
 */
function initializeApp() {
    console.log('🚀 CV Optimizer Pro initialized');

    // Check for session storage cleanup
    cleanupOldSessions();

    // Setup event listeners
    setupGlobalEventListeners();

    // Initialize tooltips
    initializeTooltips();
}

/**
 * Setup global event listeners
 */
function setupGlobalEventListeners() {
    // Handle navigation
    document.addEventListener('click', function(e) {
        if (e.target.matches('[data-action]')) {
            handleAction(e.target.dataset.action, e.target);
        }
    });

    // Handle keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Enter to submit form
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const activeForm = document.querySelector('form:focus-within');
            if (activeForm) {
                activeForm.dispatchEvent(new Event('submit', {
                    cancelable: true
                }));
            }
        }
    });
}

/**
 * Setup form validation
 */
function setupFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');

    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form)) {
                e.preventDefault();
                showToast('error', 'Proszę wypełnić wszystkie wymagane pola poprawnie.');
            }
        });

        // Real-time validation
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', () => validateField(input));
            input.addEventListener('input', () => clearFieldError(input));
        });
    });
}

/**
 * Validate entire form
 */
function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');

    inputs.forEach(input => {
        if (!validateField(input)) {
            isValid = false;
        }
    });

    return isValid;
}

/**
 * Validate individual field
 */
function validateField(input) {
    const value = input.value.trim();
    let isValid = true;
    let errorMessage = '';

    // Check if required field is empty
    if (input.hasAttribute('required') && !value) {
        isValid = false;
        errorMessage = 'To pole jest wymagane.';
    }

    // Check specific field types
    if (value && input.type) {
        switch (input.type) {
            case 'email':
                if (!isValidEmail(value)) {
                    isValid = false;
                    errorMessage = 'Nieprawidłowy format adresu email.';
                }
                break;

            case 'file':
                if (input.files.length > 0) {
                    const file = input.files[0];
                    if (!isValidFile(file, input.accept)) {
                        isValid = false;
                        errorMessage = 'Nieprawidłowy format pliku.';
                    }
                }
                break;
        }
    }

    // Show/hide error
    if (isValid) {
        clearFieldError(input);
    } else {
        showFieldError(input, errorMessage);
    }

    return isValid;
}

/**
 * Show field error
 */
function showFieldError(input, message) {
    clearFieldError(input);

    input.classList.add('is-invalid');

    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;

    input.parentNode.appendChild(errorDiv);
}

/**
 * Clear field error
 */
function clearFieldError(input) {
    input.classList.remove('is-invalid');
    const errorDiv = input.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

/**
 * Setup enhanced file upload
 */
function setupFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]');

    fileInputs.forEach(input => {
        setupDragAndDrop(input);
        setupFilePreview(input);
        setupFileValidation(input);
    });
}

/**
 * Setup drag and drop for file input
 */
function setupDragAndDrop(input) {
    const container = input.closest('.file-upload-container') || input.parentNode;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        container.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        container.addEventListener(eventName, () => {
            container.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        container.addEventListener(eventName, () => {
            container.classList.remove('dragover');
        }, false);
    });

    container.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            input.files = files;
            input.dispatchEvent(new Event('change', {
                bubbles: true
            }));
        }
    }, false);
}

/**
 * Prevent default drag behaviors
 */
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

/**
 * Setup file preview
 */
function setupFilePreview(input) {
    input.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            showFilePreview(file, input);
        }
    });
}

/**
 * Show file preview
 */
function showFilePreview(file, input) {
    const previewContainer = input.parentNode.querySelector('.file-preview') ||
        createFilePreviewContainer(input);

    if (previewContainer) {
        previewContainer.innerHTML = ' \
            <div class="file-info d-flex align-items-center"> \
                <i class="bi bi-file-pdf text-danger fs-3 me-3"></i> \
                <div> \
                    <div class="fw-bold">' + file.name + '</div> \
                    <div class="text-muted small">' + formatFileSize(file.size) + '</div> \
                </div> \
                <button type="button" class="btn btn-sm btn-outline-danger ms-auto" onclick="clearFile(this)"> \
                    <i class="bi bi-x"></i> \
                </button> \
            </div> \
        ';

        previewContainer.style.display = 'block';
    }
}

/**
 * Create file preview container
 */
function createFilePreviewContainer(input) {
    const container = document.createElement('div');
    container.className = 'file-preview mt-2 p-3 border rounded';
    container.style.display = 'none';

    input.parentNode.appendChild(container);
    return container;
}

/**
 * Clear selected file
 */
function clearFile(button) {
    const previewContainer = button.closest('.file-preview');
    const input = previewContainer ? previewContainer.parentNode.querySelector('input[type="file"]') : null;

    if (input) {
        input.value = '';
    }
    if (previewContainer) {
        previewContainer.style.display = 'none';
    }
}

/**
 * Setup file validation
 */
function setupFileValidation(input) {
    input.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            validateFileUpload(file, input);
        }
    });
}

/**
 * Validate file upload
 */
function validateFileUpload(file, input) {
    const maxSize = 16 * 1024 * 1024; // 16MB
    const allowedTypes = ['application/pdf'];

    if (file.size > maxSize) {
        showToast('error', 'Plik jest za duży. Maksymalny rozmiar to 16MB.');
        input.value = '';
        return false;
    }

    if (!allowedTypes.includes(file.type)) {
        showToast('error', 'Dozwolone są tylko pliki PDF.');
        input.value = '';
        return false;
    }

    return true;
}

/**
 * Setup toast notification system
 */
function setupToastSystem() {
    // Create toast container if it doesn't exist
    if (!document.querySelector('.toast-container')) {
        createToastContainer();
    }
}

/**
 * Create toast container
 */
function createToastContainer() {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '9999';

    document.body.appendChild(container);
}

/**
 * Show toast notification
 */
function showToast(type, message, duration = 5000) {
    const container = document.querySelector('.toast-container');
    const toastId = 'toast-' + Date.now();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    const bgClass = type === 'success' ? 'bg-success' :
        type === 'error' ? 'bg-danger' :
        type === 'warning' ? 'bg-warning' : 'bg-info';

    const icon = type === 'success' ? 'check-circle-fill' :
        type === 'error' ? 'exclamation-triangle-fill' :
        type === 'warning' ? 'exclamation-triangle-fill' : 'info-circle-fill';

    toast.innerHTML = ' \
        <div class="' + bgClass + ' text-white toast-header">\n            <i class="bi bi-' + icon + ' me-2"></i>\n            <strong class="me-auto">' + (type === 'success' ? 'Sukces' :
        type === 'error' ? 'Błąd' :
        type === 'warning' ? 'Ostrzeżenie' : 'Informacja') + '</strong>\n            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>\n        </div>\n        <div class="toast-body">\n            ' + message + '\n        </div>\n    ';

    container.appendChild(toast);

    const bsToast = new bootstrap.Toast(toast, {
        delay: duration
    });

    bsToast.show();

    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });

    return bsToast;
}

/**
 * Setup animations
 */
function setupAnimations() {
    // Intersection Observer for fade-in animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // Observe elements with animation classes
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

/**
 * Initialize tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Handle custom actions
 */
function handleAction(action, element) {
    switch (action) {
        case 'copy-text':
            copyTextToClipboard(element.dataset.text);
            break;
        case 'download-text':
            downloadText(element.dataset.text, element.dataset.filename);
            break;
        case 'scroll-to':
            scrollToElement(element.dataset.target);
            break;
        default:
            console.log('Unknown action:', action);
    }
}

/**
 * Copy text to clipboard
 */
async function copyTextToClipboard(text) {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            textArea.remove();
        }
        showToast('success', 'Tekst został skopiowany do schowka!');
    } catch (err) {
        showToast('error', 'Nie udało się skopiować tekstu.');
        console.error('Copy failed:', err);
    }
}

/**
 * Download text as file
 */
function downloadText(text, filename = 'download.txt') {
    const blob = new Blob([text], {
        type: 'text/plain;charset=utf-8'
    });
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.style.display = 'none';

    document.body.appendChild(a);
    a.click();

    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    showToast('success', 'Plik został pobrany!');
}

/**
 * Scroll to element
 */
function scrollToElement(selector) {
    const target = document.querySelector(selector);
    if (target) {
        target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }
}

/**
 * Cleanup old sessions from localStorage
 */
function cleanupOldSessions() {
    const now = Date.now();
    const oneDay = 24 * 60 * 60 * 1000; // 24 hours in milliseconds

    for (let key in localStorage) {
        if (key.startsWith('cv-session-')) {
            try {
                const data = JSON.parse(localStorage[key]);
                if (data.timestamp && (now - data.timestamp) > oneDay) {
                    localStorage.removeItem(key);
                }
            } catch (e) {
                // Remove invalid entries
                localStorage.removeItem(key);
            }
        }
    }
}

/**
 * Utility functions
 */

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function isValidFile(file, accept) {
    if (!accept) return true;

    const acceptedTypes = accept.split(',').map(type => type.trim());
    return acceptedTypes.some(type => {
        if (type.startsWith('.')) {
            return file.name.toLowerCase().endsWith(type.toLowerCase());
        } else {
            return file.type === type;
        }
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func.apply(this, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(this, args);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Service Worker Registration (for offline support)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/service-worker.js')
            .then(registration => {
                console.log('SW registered: ', registration);
            })
            .catch(registrationError => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);

    // Hide loading states on error
    const loadingElements = document.querySelectorAll('.spinner-border, [id$="loadingState"]');
    loadingElements.forEach(el => {
        if (el && el.style) el.style.display = 'none';
    });
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    showToast('error', 'Wystąpił błąd podczas przetwarzania. Proszę spróbować ponownie.');
});

// Export functions for global use
window.CVOptimizer = {
    showToast,
    copyTextToClipboard,
    downloadText,
    validateForm,
    formatFileSize
};

// --- Enhanced Animations and Interactions ---

// Scroll reveal animations
function revealOnScroll() {
    const reveals = document.querySelectorAll('.scroll-reveal, .scroll-reveal-left, .scroll-reveal-right');

    reveals.forEach(element => {
        const windowHeight = window.innerHeight;
        const elementTop = element.getBoundingClientRect().top;
        const elementVisible = 150;

        if (elementTop < windowHeight - elementVisible) {
            element.classList.add('revealed');
        }
    });
}

// Counter animation
function animateCounters() {
    const counters = document.querySelectorAll('.stat-counter[data-target]');

    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        const increment = target / 100;
        let current = 0;

        const updateCounter = () => {
            if (current < target) {
                current += increment;
                counter.textContent = Math.floor(current) + (counter.textContent.includes('%') ? '%' : '+');
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target + (counter.textContent.includes('%') ? '%' : '+');
            }
        };

        // Start animation when element is visible
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    updateCounter();
                    observer.unobserve(entry.target);
                }
            });
        });

        observer.observe(counter);
    });
}

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Typewriter effect
function typeWriter(element, text, speed = 100) {
    let i = 0;
    element.innerHTML = '';

    function type() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }

    type();
}

// Enhanced button interactions
function initButtonEnhancements() {
    const buttons = document.querySelectorAll('.btn-advanced');

    buttons.forEach(button => {
        button.addEventListener('mouseenter', function(e) {
            const ripple = document.createElement('span');
            ripple.classList.add('ripple-effect');
            this.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

// Parallax effect
function initParallax() {
    const parallaxElements = document.querySelectorAll('.parallax-element');

    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const rate = scrolled * -0.5;

        parallaxElements.forEach(element => {
            if (element && element.style) {
                element.style.transform = `translateY(${rate}px)`;
            }
        });
    });
}

// Loading skeleton animation
function showLoadingSkeleton(container) {
    const skeleton = `
        <div class="skeleton-loader skeleton-title"></div>
        <div class="skeleton-loader skeleton-text"></div>
        <div class="skeleton-loader skeleton-text"></div>
        <div class="skeleton-loader skeleton-text" style="width: 60%;"></div>
    `;

    container.innerHTML = skeleton;
}

// Enhanced toast notifications
function showEnhancedToast(type, message, duration = 5000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} toast-enter`;
    toast.innerHTML = `
        <div class="toast-header">
            <i class="bi bi-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
            <strong class="me-auto">${type === 'success' ? 'Sukces' : type === 'error' ? 'Błąd' : 'Informacja'}</strong>
            <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
        <div class="toast-body">${message}</div>
    `;

    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => {
        toast.classList.add('toast-enter-active');
        toast.classList.remove('toast-enter');
    }, 10);

    // Auto remove
    setTimeout(() => {
        toast.classList.add('toast-exit');
        toast.classList.add('toast-exit-active');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Initialize all enhancements
document.addEventListener('DOMContentLoaded', function() {
    // Existing initialization code...

    // Add new enhancements
    revealOnScroll();
    animateCounters();
    initButtonEnhancements();
    initParallax();

    // Scroll event listener
    window.addEventListener('scroll', revealOnScroll);

    // Initialize typewriter effect for hero title
    const heroTitle = document.querySelector('.typewriter');
    if (heroTitle) {
        const originalText = heroTitle.textContent;
        typeWriter(heroTitle, originalText, 50);
    }
});

// Enhanced file upload with visual feedback
function enhanceFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]');

    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const container = this.closest('.file-upload-area');
                if (container) {
                    container.classList.add('success');
                    container.innerHTML = `
                        <i class="bi bi-check-circle fs-1 text-success mb-3"></i>
                        <h5>Plik załadowany pomyślnie</h5>
                        <p class="text-muted">${file.name}</p>
                    `;
                }
            }
        });
    });
}

// Call enhance file upload
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceFileUpload);
} else {
    enhanceFileUpload();
}