// Main script file for Form Digitizer application

document.addEventListener('DOMContentLoaded', function() {
    // Add loading spinner for form submission
    setupLoadingSpinner();
    
    // Set up template selection cards
    setupTemplateSelection();
    
    // Set up form upload area
    setupFormUpload();
    
    // Set up tooltips
    setupTooltips();
});

// Function to show/hide loading spinner
function setupLoadingSpinner() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            // Check if the form has the 'no-spinner' class
            if (!form.classList.contains('no-spinner')) {
                showSpinner();
            }
        });
    });
}

function showSpinner() {
    // Create spinner overlay if it doesn't exist
    if (!document.querySelector('.spinner-overlay')) {
        const spinnerOverlay = document.createElement('div');
        spinnerOverlay.className = 'spinner-overlay';
        
        const spinnerContainer = document.createElement('div');
        spinnerContainer.className = 'spinner-container';
        
        const spinner = document.createElement('div');
        spinner.className = 'spinner-border text-primary';
        spinner.setAttribute('role', 'status');
        
        const spinnerText = document.createElement('span');
        spinnerText.className = 'sr-only';
        spinnerText.textContent = 'Loading...';
        
        spinner.appendChild(spinnerText);
        spinnerContainer.appendChild(spinner);
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'mt-3';
        messageDiv.textContent = 'Processing your request...';
        spinnerContainer.appendChild(messageDiv);
        
        spinnerOverlay.appendChild(spinnerContainer);
        document.body.appendChild(spinnerOverlay);
    }
}

function hideSpinner() {
    const spinnerOverlay = document.querySelector('.spinner-overlay');
    if (spinnerOverlay) {
        document.body.removeChild(spinnerOverlay);
    }
}

// Function to set up template selection cards
function setupTemplateSelection() {
    const templateCards = document.querySelectorAll('.template-card');
    const templateInput = document.getElementById('template');
    
    if (templateCards.length > 0 && templateInput) {
        templateCards.forEach(card => {
            card.addEventListener('click', function() {
                // Remove selected class from all cards
                templateCards.forEach(c => c.classList.remove('selected'));
                
                // Add selected class to clicked card
                this.classList.add('selected');
                
                // Set the value of the hidden input
                templateInput.value = this.dataset.template;
            });
        });
    }
}

// Function to set up form upload area
function setupFormUpload() {
    const uploadArea = document.querySelector('.upload-area');
    const fileInput = document.getElementById('form_file');
    
    if (uploadArea && fileInput) {
        // Handle drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('border-primary');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('border-primary');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('border-primary');
            
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                updateFileNameDisplay(fileInput);
            }
        });
        
        // Handle file input change
        fileInput.addEventListener('change', function() {
            updateFileNameDisplay(this);
        });
        
        // Click on upload area to trigger file input
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });
    }
}

// Function to update file name display
function updateFileNameDisplay(fileInput) {
    const fileNameDisplay = document.querySelector('.file-name-display');
    
    if (fileNameDisplay) {
        if (fileInput.files && fileInput.files.length > 0) {
            fileNameDisplay.textContent = fileInput.files[0].name;
        } else {
            fileNameDisplay.textContent = 'No file selected';
        }
    }
}

// Function to set up tooltips
function setupTooltips() {
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        new bootstrap.Tooltip(tooltip);
    });
}

// Function to confirm delete
function confirmDelete(formId) {
    if (confirm('Are you sure you want to delete this form? This action cannot be undone.')) {
        document.getElementById(`delete-form-${formId}`).submit();
    }
}
