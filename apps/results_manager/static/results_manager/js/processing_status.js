/**
 * Results Manager - Processing Status JavaScript
 * 
 * This module handles real-time updates for processing status,
 * including progress tracking, stage updates, and error handling.
 */

class ProcessingStatusManager {
    constructor(sessionId, initialStatus) {
        this.sessionId = sessionId;
        this.status = initialStatus;
        this.refreshInterval = null;
        this.refreshRate = 5000; // 5 seconds
        this.maxRetries = 3;
        this.retryCount = 0;
        
        this.init();
    }
    
    init() {
        // Initialize event listeners
        this.setupEventListeners();
        
        // Start auto-refresh if processing is in progress
        if (this.status === 'in_progress') {
            this.startAutoRefresh();
        }
        
        // Setup visibility change listener to pause/resume updates
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseAutoRefresh();
            } else if (this.status === 'in_progress') {
                this.resumeAutoRefresh();
            }
        });
    }
    
    setupEventListeners() {
        // Setup any button click handlers
        const pauseBtn = document.querySelector('[onclick="pauseProcessing()"]');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.pauseProcessing();
            });
        }
        
        const cancelBtn = document.querySelector('[onclick="cancelProcessing()"]');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.cancelProcessing();
            });
        }
        
        const viewErrorsBtn = document.querySelector('[onclick="viewAllErrors()"]');
        if (viewErrorsBtn) {
            viewErrorsBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.viewAllErrors();
            });
        }
    }
    
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        console.log('Starting auto-refresh for processing status');
        this.refreshInterval = setInterval(() => {
            this.fetchProcessingStatus();
        }, this.refreshRate);
        
        // Show auto-refresh indicator
        this.showAutoRefreshIndicator();
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('Stopped auto-refresh');
        }
        
        // Hide auto-refresh indicator
        this.hideAutoRefreshIndicator();
    }
    
    pauseAutoRefresh() {
        this.stopAutoRefresh();
    }
    
    resumeAutoRefresh() {
        if (this.status === 'in_progress') {
            this.startAutoRefresh();
        }
    }
    
    async fetchProcessingStatus() {
        try {
            const response = await fetch(`/results-manager/api/processing-status/${this.sessionId}/`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.updateProcessingUI(data);
            this.retryCount = 0; // Reset retry count on success
            
            // Update status and handle completion
            const oldStatus = this.status;
            this.status = data.status;
            
            if (oldStatus === 'in_progress' && this.status !== 'in_progress') {
                this.handleProcessingComplete(data);
            }
            
        } catch (error) {
            console.error('Error fetching processing status:', error);
            this.handleFetchError(error);
        }
    }
    
    updateProcessingUI(data) {
        // Update overall progress bar
        const overallProgress = document.querySelector('.progress-bar.bg-primary');
        if (overallProgress) {
            overallProgress.style.width = `${data.progress_percentage}%`;
            overallProgress.setAttribute('aria-valuenow', data.progress_percentage);
        }
        
        // Update stage progress bar
        const stageProgress = document.querySelector('.progress-bar.bg-info');
        if (stageProgress) {
            stageProgress.style.width = `${data.stage_progress}%`;
            stageProgress.textContent = `${data.stage_progress}% complete`;
            stageProgress.setAttribute('aria-valuenow', data.stage_progress);
        }
        
        // Update progress label
        const progressLabel = document.querySelector('.progress-label');
        if (progressLabel && data.total_raw_results > 0) {
            progressLabel.textContent = `${data.progress_percentage}% (${data.processed_count}/${data.total_raw_results} results)`;
        }
        
        // Update current stage
        const stageInfo = document.querySelector('.current-stage-info h6');
        if (stageInfo && data.current_stage) {
            const stageDisplay = this.formatStageName(data.current_stage);
            stageInfo.textContent = `Current Stage: ${stageDisplay}`;
        }
        
        // Update statistics
        this.updateStatistics(data);
        
        // Update stage icons and progress
        this.updateStageProgress(data);
        
        // Update estimated completion time
        if (data.estimated_completion) {
            const estimatedTime = new Date(data.estimated_completion);
            const timeElement = document.querySelector('.estimated-completion');
            if (timeElement) {
                timeElement.textContent = estimatedTime.toLocaleTimeString();
            }
        }
    }
    
    updateStatistics(data) {
        const stats = {
            'duplicate_count': data.duplicate_count || 0,
            'error_count': data.error_count || 0,
            'processed_count': data.processed_count || 0,
            'total_raw_results': data.total_raw_results || 0
        };
        
        Object.entries(stats).forEach(([key, value]) => {
            const element = document.querySelector(`.stat-card:has(.stat-label:contains("${this.getStatLabel(key)}")`) ||
                           document.querySelector(`[data-stat="${key}"] .stat-number`);
            if (element) {
                const numberElement = element.querySelector('.stat-number') || element;
                numberElement.textContent = value;
                
                // Add animation for value changes
                if (numberElement.textContent !== value.toString()) {
                    numberElement.classList.add('updating');
                    setTimeout(() => numberElement.classList.remove('updating'), 500);
                }
            }
        });
    }
    
    updateStageProgress(data) {
        const stages = [
            'initialization',
            'url_normalization', 
            'metadata_extraction',
            'deduplication',
            'quality_scoring',
            'finalization'
        ];
        
        const currentStageIndex = stages.indexOf(data.current_stage);
        
        stages.forEach((stage, index) => {
            const stageElement = document.querySelector(`[data-stage="${stage}"]`);
            if (!stageElement) return;
            
            const progressBar = stageElement.querySelector('.progress-bar');
            const icon = stageElement.querySelector('.stage-icon');
            const badge = stageElement.querySelector('.badge');
            
            if (index < currentStageIndex) {
                // Completed stages
                if (progressBar) {
                    progressBar.style.width = '100%';
                    progressBar.classList.remove('bg-primary', 'bg-light');
                    progressBar.classList.add('bg-success');
                }
                if (icon) icon.textContent = '✓';
                if (badge) {
                    badge.className = 'badge badge-success ml-2';
                    badge.textContent = 'Completed';
                }
            } else if (index === currentStageIndex) {
                // Current stage
                if (progressBar) {
                    progressBar.style.width = `${data.stage_progress}%`;
                    progressBar.classList.remove('bg-success', 'bg-light');
                    progressBar.classList.add('bg-primary');
                }
                if (icon) icon.textContent = '⟳';
                if (badge) {
                    badge.className = 'badge badge-primary ml-2';
                    badge.textContent = 'In Progress';
                }
            } else {
                // Pending stages
                if (progressBar) {
                    progressBar.style.width = '0%';
                    progressBar.classList.remove('bg-success', 'bg-primary');
                    progressBar.classList.add('bg-light');
                }
                if (icon) icon.textContent = '○';
                if (badge) {
                    badge.className = 'badge badge-secondary ml-2';
                    badge.textContent = 'Pending';
                }
            }
        });
    }
    
    handleProcessingComplete(data) {
        this.stopAutoRefresh();
        
        // Show completion notification
        const status = data.status;
        let message, variant;
        
        switch (status) {
            case 'completed':
                message = 'Processing completed successfully!';
                variant = 'success';
                break;
            case 'failed':
                message = 'Processing failed. Please check the errors below.';
                variant = 'danger';
                break;
            case 'partial':
                message = 'Processing completed with some errors.';
                variant = 'warning';
                break;
            default:
                message = `Processing status: ${status}`;
                variant = 'info';
        }
        
        this.showNotification(message, variant);
        
        // Redirect to results page after successful completion
        if (status === 'completed') {
            setTimeout(() => {
                window.location.href = `/results-manager/results/${this.sessionId}/`;
            }, 2000);
        }
    }
    
    handleFetchError(error) {
        this.retryCount++;
        
        if (this.retryCount >= this.maxRetries) {
            this.stopAutoRefresh();
            this.showNotification(
                'Unable to fetch processing status. Please refresh the page.',
                'danger'
            );
        } else {
            console.warn(`Fetch attempt ${this.retryCount} failed, retrying...`);
            // Continue with auto-refresh, will retry on next interval
        }
    }
    
    showNotification(message, variant = 'info') {
        // Create and show a notification
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${variant} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="close" data-dismiss="alert">
                <span>&times;</span>
            </button>
        `;
        
        // Insert at the top of the container
        const container = document.querySelector('.container-fluid');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
            
            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }
    
    showAutoRefreshIndicator() {
        let indicator = document.querySelector('.auto-refresh-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'auto-refresh-indicator';
            indicator.innerHTML = `
                <small class="text-muted">
                    <i class="fas fa-sync-alt fa-spin"></i> Auto-refreshing every 5 seconds
                </small>
            `;
            document.body.appendChild(indicator);
        }
        indicator.style.display = 'block';
    }
    
    hideAutoRefreshIndicator() {
        const indicator = document.querySelector('.auto-refresh-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }
    
    formatStageName(stageName) {
        return stageName
            .replace(/_/g, ' ')
            .replace(/\b\w/g, l => l.toUpperCase());
    }
    
    getStatLabel(key) {
        const labels = {
            'duplicate_count': 'Duplicates Found',
            'error_count': 'Processing Errors',
            'processed_count': 'Results Processed',
            'total_raw_results': 'Total Raw Results'
        };
        return labels[key] || key;
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name="csrfmiddlewaretoken"]')?.value ||
                     document.querySelector('meta[name="csrf-token"]')?.content ||
                     '';
        return token;
    }
    
    // Action methods
    pauseProcessing() {
        // TODO: Implement pause functionality
        this.showNotification('Pause functionality will be implemented in a future version.', 'info');
    }
    
    cancelProcessing() {
        if (confirm('Are you sure you want to cancel processing? This cannot be undone.')) {
            // TODO: Implement cancel functionality
            this.showNotification('Cancel functionality will be implemented in a future version.', 'info');
        }
    }
    
    viewAllErrors() {
        // TODO: Implement view all errors modal
        this.showNotification('View all errors functionality will be implemented in a future version.', 'info');
    }
}

// Global functions for backward compatibility
function pauseProcessing() {
    if (window.processingStatusManager) {
        window.processingStatusManager.pauseProcessing();
    }
}

function cancelProcessing() {
    if (window.processingStatusManager) {
        window.processingStatusManager.cancelProcessing();
    }
}

function viewAllErrors() {
    if (window.processingStatusManager) {
        window.processingStatusManager.viewAllErrors();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // This will be set by the template
    if (typeof sessionId !== 'undefined' && typeof processingStatus !== 'undefined') {
        window.processingStatusManager = new ProcessingStatusManager(sessionId, processingStatus);
    }
});