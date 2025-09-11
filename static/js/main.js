// Simple CV Optimizer Pro JavaScript

// Toast notifications
function showToast(type, message, duration = 5000) {
    const toastContainer = document.querySelector('.toast-container') || document.body;

    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    toastContainer.appendChild(toast);

    // Auto remove
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, duration);
}

// Simple form validation
function validateForm(formElement) {
    const requiredFields = formElement.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// File upload handler
function handleFileUpload(inputElement) {
    inputElement.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            if (file.size > 16 * 1024 * 1024) { // 16MB
                showToast('danger', 'Plik jest za duży. Maksymalny rozmiar to 16MB.');
                this.value = '';
                return;
            }

            if (file.type !== 'application/pdf') {
                showToast('danger', 'Dozwolone są tylko pliki PDF.');
                this.value = '';
                return;
            }
        }
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 CV Optimizer Pro initialized');

    // Initialize file upload validation
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(handleFileUpload);

    // Initialize form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                showToast('danger', 'Proszę wypełnić wszystkie wymagane pola.');
            }
        });
    });
});

// Global CVOptimizer object for compatibility
window.CVOptimizer = {
    showToast: showToast,
    validateForm: validateForm
};

// Funkcja obsługi przekierowań do cennika
function handlePaymentRedirect(response) {
    if (response.redirect_to_pricing) {
        if (confirm(response.message + '\n\nCzy chcesz przejść do cennika?')) {
            window.location.href = '/pricing';
        }
        return true;
    }
    return false;
}

function optimizeCV(sessionId) {
        fetch('/optimize-cv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                selected_model: getSelectedModel()
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert(data.message, 'success');
                document.getElementById('optimized-cv').innerHTML = 
                    `<div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-magic text-primary"></i> Zoptymalizowane CV</h5>
                        </div>
                        <div class="card-body">
                            <pre class="cv-text">${data.optimized_cv}</pre>
                        </div>
                    </div>`;
            } else {
                if (!handlePaymentRedirect(data)) {
                    showAlert(data.message, 'error');
                }
            }
        })
        .catch(error => {
            console.error('Błąd:', error);
            showAlert('Wystąpił błąd podczas optymalizacji CV.', 'error');
        });
    }

function analyzeCV(sessionId, buttonElement = null) {
    try {
        // Disable button to prevent double clicks
        if (buttonElement) {
            buttonElement.disabled = true;
            const originalText = buttonElement.innerHTML;
            buttonElement.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Analizowanie...';
            
            // Re-enable button after timeout as fallback
            setTimeout(() => {
                if (buttonElement.disabled) {
                    buttonElement.disabled = false;
                    buttonElement.innerHTML = originalText;
                }
            }, 30000);
        }

        fetch('/analyze-cv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                selected_model: getSelectedModel()
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showAlert(data.message, 'success');
                // Reload page to show the analysis results
                window.location.reload();
            } else {
                if (!handlePaymentRedirect(data)) {
                    showAlert(data.message, 'error');
                }
            }
        })
        .catch(error => {
            console.error('Błąd:', error);
            showAlert('Wystąpił błąd podczas analizy CV. Spróbuj ponownie.', 'error');
        })
        .finally(() => {
            // Re-enable button
            if (buttonElement) {
                buttonElement.disabled = false;
                buttonElement.innerHTML = buttonElement.getAttribute('data-original-text') || 'Analizuj CV';
            }
        });
    } catch (error) {
        console.error('Błąd w analyzeCV:', error);
        showAlert('Wystąpił nieoczekiwany błąd.', 'error');
        if (buttonElement) {
            buttonElement.disabled = false;
        }
    }
}

// Placeholder for potential future button logic related to Stripe integration
// AI Model Selection functionality
let selectedModel = localStorage.getItem('selectedAIModel') || 'qwen';

function initializeModelSelection() {
    const modelCards = document.querySelectorAll('.model-card');
    const selectedModelInfo = document.getElementById('selected-model-info');
    const selectedModelText = document.getElementById('selected-model-text');
    
    // Set initial selection
    updateModelSelection(selectedModel);
    
    modelCards.forEach(card => {
        card.addEventListener('click', function() {
            const modelKey = this.dataset.model;
            if (modelKey !== selectedModel) {
                selectedModel = modelKey;
                localStorage.setItem('selectedAIModel', selectedModel);
                updateModelSelection(selectedModel);
                showToast('success', `Wybrano model AI: ${getModelName(selectedModel)}`);
            }
        });
    });

    function updateModelSelection(modelKey) {
        // Update visual selection
        modelCards.forEach(card => {
            if (card.dataset.model === modelKey) {
                card.style.border = '2px solid var(--primary)';
                card.style.background = 'rgba(99, 102, 241, 0.05)';
            } else {
                card.style.border = '2px solid var(--border-primary)';
                card.style.background = 'var(--bg-card)';
            }
        });
        
        // Update info text
        if (selectedModelInfo && selectedModelText) {
            selectedModelText.textContent = `Wybrano model: ${getModelName(modelKey)}`;
            selectedModelInfo.classList.remove('d-none');
        }
    }

    function getModelName(modelKey) {
        const modelNames = {
            'qwen': 'Qwen-2.5-72B',
            'deepseek': 'DeepSeek Chat v3.1'
        };
        return modelNames[modelKey] || 'Qwen-2.5-72B';
    }
}

// Get selected AI model for requests
function getSelectedModel() {
    return selectedModel;
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize model selection if on dashboard
    if (document.getElementById('ai-model-selection')) {
        initializeModelSelection();
    }
    
    const paymentButtons = document.querySelectorAll('[data-stripe-price-id]');
    paymentButtons.forEach(button => {
        button.addEventListener('click', function() {
            const priceId = this.getAttribute('data-stripe-price-id');
            // Here you would typically initiate a Stripe Checkout session
            // For now, we'll just log it and potentially redirect to pricing
            console.log(`Initiating payment for price ID: ${priceId}`);
            // Example: If you have a backend endpoint to create a checkout session
            // fetch('/create-checkout-session', {
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify({ priceId: priceId })
            // })
            // .then(response => response.json())
            // .then(session => {
            //     if (session.id) {
            //         stripe.redirectToCheckout({ sessionId: session.id });
            //     } else {
            //         showToast('danger', 'Nie można rozpocząć płatności. Spróbuj ponownie.');
            //     }
            // })
            // .catch(error => {
            //     console.error('Error creating checkout session:', error);
            //     showToast('danger', 'Wystąpił błąd podczas inicjowania płatności.');
            // });

            // Fallback or alternative: redirect to pricing page
            if (!handlePaymentRedirect({ redirect_to_pricing: true, message: "Aby dokonać płatności, przejdź do cennika." })) {
                 window.location.href = '/pricing';
            }
        });
    });
});

// CV Optimizer Pro - Main JavaScript

// Add missing downloadText function
function downloadText(content, filename) {
    const element = document.createElement('a');
    const file = new Blob([content], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = filename;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

console.log('🚀 CV Optimizer Pro initialized');

// Loading states
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Ładowanie...</span></div></div>';
    }
}

function hideLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '';
    }
}

// Download functions
function downloadText(content, filename) {
    if (!content) {
        alert('Brak treści do pobrania');
        return;
    }

    const element = document.createElement('a');
    const file = new Blob([content], { type: 'text/plain' });
    element.href = URL.createObjectURL(file);
    element.download = filename || 'document.txt';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

function downloadCV() {
    const cvContent = document.getElementById('cv-content');
    if (cvContent) {
        const content = cvContent.innerText || cvContent.textContent;
        downloadText(content, 'zoptymalizowane_cv.txt');
    } else {
        alert('Nie znaleziono treści CV do pobrania');
    }
}