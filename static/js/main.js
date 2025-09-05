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
                session_id: sessionId
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

function analyzeCV(sessionId) {
        fetch('/analyze-cv', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert(data.message, 'success');
                document.getElementById('cv-analysis').innerHTML = 
                    `<div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-chart-line text-info"></i> Analiza CV</h5>
                        </div>
                        <div class="card-body">
                            <pre class="analysis-text">${data.cv_analysis}</pre>
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
            showAlert('Wystąpił błąd podczas analizy CV.', 'error');
        });
    }

// Placeholder for potential future button logic related to Stripe integration
document.addEventListener('DOMContentLoaded', function() {
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