/**
 * Search Strategy Form JavaScript
 * Handles real-time preview, validation, and interactive features
 */

class SearchStrategyForm {
    constructor() {
        this.form = document.getElementById('strategy-form');
        this.previewTimeout = null;
        this.debounceDelay = 1000;
        this.sessionId = this.getSessionId();
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.initAutoPreview();
        this.loadInitialPreview();
    }
    
    getSessionId() {
        // Extract session ID from URL or data attribute
        const path = window.location.pathname;
        const match = path.match(/session\/([a-f0-9-]+)\//);
        return match ? match[1] : null;
    }
    
    bindEvents() {
        // Preview button
        const previewBtn = document.querySelector('[onclick="previewChanges()"]');
        if (previewBtn) {
            previewBtn.onclick = () => this.previewChanges();
        }
        
        // Validate button
        const validateBtn = document.querySelector('[onclick="validateStrategy()"]');
        if (validateBtn) {
            validateBtn.onclick = () => this.validateStrategy();
        }
        
        // Form submission
        this.form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        // Auto-save functionality (optional)
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges()) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            }
        });
    }
    
    initAutoPreview() {
        // Add auto-preview to all relevant form fields
        const watchedFields = [
            'population_terms_text',
            'interest_terms_text', 
            'context_terms_text',
            'organization_domains',
            'include_general_search',
            'search_pdf',
            'search_doc',
            'use_google_search',
            'use_google_scholar'
        ];
        
        watchedFields.forEach(fieldName => {
            const field = document.getElementById(`id_${fieldName}`);
            if (field) {
                if (field.type === 'checkbox') {
                    field.addEventListener('change', () => this.debouncedPreview());
                } else {
                    field.addEventListener('input', () => this.debouncedPreview());
                }
            }
        });
    }
    
    debouncedPreview() {
        clearTimeout(this.previewTimeout);
        this.previewTimeout = setTimeout(() => this.previewChanges(), this.debounceDelay);
    }
    
    loadInitialPreview() {
        // Load initial preview if there's existing data
        const hasData = this.collectFormData().population_terms.length > 0 ||
                       this.collectFormData().interest_terms.length > 0 ||
                       this.collectFormData().context_terms.length > 0;
        
        if (hasData) {
            this.previewChanges();
        }
    }
    
    collectFormData() {
        const getFieldValue = (fieldName) => {
            const field = document.getElementById(`id_${fieldName}`);
            return field ? field.value : '';
        };
        
        const getCheckboxValue = (fieldName) => {
            const field = document.getElementById(`id_${fieldName}`);
            return field ? field.checked : false;
        };
        
        const parseTerms = (text) => {
            return text.split('\\n')
                      .map(t => t.trim())
                      .filter(t => t.length > 0);
        };
        
        return {
            population_terms: parseTerms(getFieldValue('population_terms_text')),
            interest_terms: parseTerms(getFieldValue('interest_terms_text')),
            context_terms: parseTerms(getFieldValue('context_terms_text')),
            search_config: {
                domains: parseTerms(getFieldValue('organization_domains')),
                include_general_search: getCheckboxValue('include_general_search'),
                file_types: [
                    ...(getCheckboxValue('search_pdf') ? ['pdf'] : []),
                    ...(getCheckboxValue('search_doc') ? ['doc'] : [])
                ],
                search_type: getCheckboxValue('use_google_scholar') ? 'scholar' : 'google',
                max_results: parseInt(getFieldValue('max_results_per_query')) || 50
            }
        };
    }
    
    async previewChanges() {
        if (!this.sessionId) {
            console.error('No session ID found');
            return;
        }
        
        const formData = this.collectFormData();
        const previewContainer = document.getElementById('query-preview');
        
        // Show loading state
        if (previewContainer) {
            previewContainer.classList.add('loading');
        }
        
        try {
            const response = await fetch(`/search_strategy/api/session/${this.sessionId}/update/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(formData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateQueryPreview(data.queries);
                this.updateProgressIndicators(data.stats);
                this.updateValidationStatus(data.is_complete, data.validation_errors);
            } else {
                console.error('Preview failed:', data.error);
                this.showError('Failed to update preview: ' + data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            this.showError('Network error occurred while updating preview');
        } finally {
            // Remove loading state
            if (previewContainer) {
                previewContainer.classList.remove('loading');
            }
        }
    }
    
    updateQueryPreview(queries) {
        const preview = document.getElementById('query-preview');
        if (!preview) return;
        
        if (queries && queries.length > 0) {
            let html = '<p class="text-muted small mb-3">Base preview - actual query may include additional filters</p>';
            queries.forEach(query => {
                const domain = query.domain || 'General Search';
                const typeColor = query.type === 'domain-specific' ? 'primary' : 'secondary';
                
                html += `
                    <div class="query-item">
                        <div class="d-flex justify-content-between mb-2">
                            <span class="font-weight-bold">${this.escapeHtml(domain)}</span>
                            <small class="badge badge-${typeColor}">${query.type}</small>
                        </div>
                        <code class="small">${this.escapeHtml(query.query)}</code>
                        <div class="mt-2 small text-muted">
                            Estimated results: ~${query.estimated_results}
                        </div>
                    </div>
                `;
            });
            preview.innerHTML = html;
        } else {
            preview.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="fas fa-search fa-2x mb-2"></i>
                    <p>Add PIC terms to see query preview</p>
                </div>
            `;
        }
    }
    
    updateProgressIndicators(stats) {
        // Update progress counters
        const counters = document.querySelectorAll('.badge-counter');
        const counts = [stats.population_count, stats.interest_count, stats.context_count];
        
        counters.forEach((counter, index) => {
            if (counts[index] !== undefined) {
                counter.textContent = counts[index];
            }
        });
        
        // Update progress item classes
        const items = document.querySelectorAll('.strategy-progress-item');
        items.forEach((item, index) => {
            if (counts[index] !== undefined) {
                item.className = 'strategy-progress-item ' + (counts[index] > 0 ? 'complete' : 'empty');
            }
        });
        
        // Update total terms counter
        const totalElement = document.querySelector('.card-body strong');
        if (totalElement && stats.total_terms !== undefined) {
            totalElement.textContent = `Total Terms: ${stats.total_terms}`;
        }
    }
    
    updateValidationStatus(isComplete, validationErrors) {
        // Update completion badge
        const statusBadges = document.querySelectorAll('.badge');
        statusBadges.forEach(badge => {
            if (badge.textContent.includes('Complete') || badge.textContent.includes('In Progress')) {
                badge.className = isComplete ? 'badge badge-success' : 'badge badge-warning';
                badge.textContent = isComplete ? 'Complete' : 'In Progress';
            }
        });
        
        // Show/hide continue button
        const continueBtn = document.querySelector('[name="save_and_continue"]');
        if (continueBtn) {
            continueBtn.style.display = isComplete ? 'inline-block' : 'none';
        }
        
        // Update validation errors (if any)
        this.displayValidationErrors(validationErrors);
    }
    
    displayValidationErrors(errors) {
        // Remove existing error alerts
        const existingAlerts = document.querySelectorAll('.alert-warning');
        existingAlerts.forEach(alert => {
            if (alert.textContent.includes('Please address these issues')) {
                alert.remove();
            }
        });
        
        if (errors && Object.keys(errors).length > 0) {
            const errorHtml = `
                <div class="alert alert-warning">
                    <h6>Please address these issues:</h6>
                    <ul>
                        ${Object.values(errors).map(error => `<li>${this.escapeHtml(error)}</li>`).join('')}
                    </ul>
                </div>
            `;
            
            const cardBody = document.querySelector('.card-body');
            if (cardBody) {
                cardBody.insertAdjacentHTML('afterbegin', errorHtml);
            }
        }
    }
    
    validateStrategy() {
        const formData = this.collectFormData();
        let errors = [];
        
        // Check PIC terms
        const totalTerms = formData.population_terms.length + 
                          formData.interest_terms.length + 
                          formData.context_terms.length;
        
        if (totalTerms === 0) {
            errors.push('At least one PIC category must have terms');
        }
        
        // Check domains or general search
        if (formData.search_config.domains.length === 0 && 
            !formData.search_config.include_general_search) {
            errors.push('Must specify domains or enable general search');
        }
        
        // Check file types
        if (formData.search_config.file_types.length === 0) {
            errors.push('Must select at least one file type');
        }
        
        // Display results
        if (errors.length > 0) {
            this.showError('Validation errors:\\n- ' + errors.join('\\n- '));
        } else {
            this.showSuccess('Strategy validation passed! Ready to save.');
        }
        
        return errors.length === 0;
    }
    
    handleFormSubmit(e) {
        // Basic client-side validation before submission
        if (!this.validateStrategy()) {
            e.preventDefault();
            return false;
        }
        
        // Show loading state
        const submitBtns = this.form.querySelectorAll('button[type="submit"]');
        submitBtns.forEach(btn => {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        });
        
        return true;
    }
    
    hasUnsavedChanges() {
        // Simple check for unsaved changes
        const formData = this.collectFormData();
        return formData.population_terms.length > 0 || 
               formData.interest_terms.length > 0 || 
               formData.context_terms.length > 0;
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showError(message) {
        // Simple alert for now - could be enhanced with toast notifications
        alert(message);
    }
    
    showSuccess(message) {
        // Simple alert for now - could be enhanced with toast notifications
        alert(message);
    }
}

// Initialize the form when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SearchStrategyForm();
});

// Legacy function support for inline onclick handlers
function previewChanges() {
    if (window.strategyForm) {
        window.strategyForm.previewChanges();
    }
}

function validateStrategy() {
    if (window.strategyForm) {
        window.strategyForm.validateStrategy();
    }
}

// Export for global access
window.strategyForm = null;
document.addEventListener('DOMContentLoaded', () => {
    window.strategyForm = new SearchStrategyForm();
});