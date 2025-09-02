
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
