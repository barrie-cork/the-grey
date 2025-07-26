/**
 * SERP Execution Monitor
 * Handles real-time progress monitoring and UI updates
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        pollInterval: 2000,  // 2 seconds
        maxRetries: 3,
        retryDelay: 5000,   // 5 seconds
        csrfTokenName: 'csrfmiddlewaretoken'
    };

    // State management
    let pollTimer = null;
    let retryCount = 0;
    let isPolling = false;
    let lastStatus = null;

    /**
     * Initialize the execution monitor
     */
    function init() {
        const statusContainer = document.getElementById('execution-status');
        if (!statusContainer) {
            console.warn('Execution status container not found');
            return;
        }

        const sessionId = statusContainer.dataset.sessionId;
        if (!sessionId) {
            console.error('Session ID not found');
            return;
        }

        // Start polling
        startPolling(sessionId);

        // Setup event listeners
        setupEventListeners();

        // Initialize tooltips and popovers
        initializeBootstrapComponents();
    }

    /**
     * Start polling for execution status
     */
    function startPolling(sessionId) {
        if (isPolling) return;
        
        isPolling = true;
        poll(sessionId);
    }

    /**
     * Stop polling
     */
    function stopPolling() {
        isPolling = false;
        if (pollTimer) {
            clearTimeout(pollTimer);
            pollTimer = null;
        }
    }

    /**
     * Poll for execution status
     */
    function poll(sessionId) {
        if (!isPolling) return;

        fetch(`/api/execution/progress/${sessionId}/`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json'
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            retryCount = 0;  // Reset retry count on success
            updateUI(data);
            
            // Check if we should continue polling
            if (shouldContinuePolling(data)) {
                pollTimer = setTimeout(() => poll(sessionId), CONFIG.pollInterval);
            } else {
                stopPolling();
                showCompletionNotification(data);
            }
        })
        .catch(error => {
            console.error('Error polling status:', error);
            handlePollingError(sessionId);
        });
    }

    /**
     * Update UI with new status data
     */
    function updateUI(data) {
        // Update overall progress
        updateOverallProgress(data);
        
        // Update individual query statuses
        updateQueryStatuses(data.executions || []);
        
        // Update statistics
        updateStatistics(data);
        
        // Update status message
        updateStatusMessage(data);
        
        // Store last status
        lastStatus = data;
    }

    /**
     * Update overall progress bar
     */
    function updateOverallProgress(data) {
        const progressBar = document.querySelector('.overall-progress .progress-bar');
        if (!progressBar) return;

        const percentage = data.overall_progress || 0;
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);
        progressBar.textContent = `${percentage}%`;

        // Update progress bar color based on status
        progressBar.className = 'progress-bar';
        if (data.session_status === 'failed') {
            progressBar.classList.add('bg-danger');
        } else if (data.session_status === 'completed') {
            progressBar.classList.add('bg-success');
        } else if (data.failed_queries > 0) {
            progressBar.classList.add('bg-warning');
        } else {
            progressBar.classList.add('bg-primary');
        }
    }

    /**
     * Update individual query statuses
     */
    function updateQueryStatuses(executions) {
        executions.forEach(execution => {
            const queryRow = document.querySelector(`[data-query-id="${execution.query_id}"]`);
            if (!queryRow) return;

            // Update status
            const statusCell = queryRow.querySelector('.query-status');
            if (statusCell) {
                statusCell.innerHTML = formatStatus(execution.status);
            }

            // Update progress
            const progressCell = queryRow.querySelector('.query-progress');
            if (progressCell) {
                progressCell.textContent = `${execution.progress || 0}%`;
            }

            // Update results
            const resultsCell = queryRow.querySelector('.query-results');
            if (resultsCell) {
                resultsCell.textContent = execution.results || 0;
            }

            // Update error message if any
            if (execution.error) {
                showQueryError(queryRow, execution.error);
            }
        });
    }

    /**
     * Update statistics cards with smooth number animations
     */
    function updateStatistics(data) {
        const stats = data.statistics || {};
        
        // Update all statistics cards with animations
        animateStatisticCard('total-queries', stats.total_executions || 0);
        animateStatisticCard('completed-queries', stats.successful_executions || 0);
        animateStatisticCard('running-queries', stats.running_executions || 0);
        animateStatisticCard('failed-queries', stats.failed_executions || 0);
        animateStatisticCard('total-results', stats.total_results || 0);
        animateStatisticCard('retrying-queries', stats.retrying_executions || 0);
        
        // Update progress bar
        updateProgressBar(stats);
    }
    
    /**
     * Animate statistic card number updates
     */
    function animateStatisticCard(elementId, newValue) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const currentValue = parseInt(element.textContent) || 0;
        if (currentValue === newValue) return;
        
        // Add updating class for visual feedback
        element.classList.add('updating');
        
        // Animate number change
        const duration = 800;
        const steps = 20;
        const difference = newValue - currentValue;
        const stepValue = difference / steps;
        const stepDuration = duration / steps;
        
        let currentStep = 0;
        const timer = setInterval(() => {
            currentStep++;
            const value = Math.round(currentValue + (stepValue * currentStep));
            element.textContent = value;
            
            if (currentStep >= steps) {
                clearInterval(timer);
                element.textContent = newValue;
                element.classList.remove('updating');
                
                // Add pulse effect if value changed significantly
                if (Math.abs(difference) > 0) {
                    const card = element.closest('.execution-stats-card');
                    if (card) {
                        card.classList.add('active');
                        setTimeout(() => card.classList.remove('active'), 2000);
                    }
                }
            }
        }, stepDuration);
    }
    
    /**
     * Update multi-segment progress bar
     */
    function updateProgressBar(stats) {
        const total = stats.total_executions || 1;
        const success = stats.successful_executions || 0;
        const failed = stats.failed_executions || 0;
        const pending = stats.pending_executions || 0;
        
        const successWidth = (success / total) * 100;
        const failedWidth = (failed / total) * 100;
        const pendingWidth = (pending / total) * 100;
        
        const progressBars = document.querySelectorAll('.progress-bar');
        if (progressBars.length >= 3) {
            // Animate progress bar changes
            progressBars[0].style.width = successWidth + '%';
            progressBars[1].style.width = failedWidth + '%';
            progressBars[2].style.width = pendingWidth + '%';
        }
    }

    /**
     * Update status message with enhanced styling
     */
    function updateStatusMessage(data) {
        const messageContainer = document.getElementById('status-message');
        if (!messageContainer) return;

        const stats = data.statistics || {};
        let message = '';
        let alertClass = 'alert-info';
        let icon = 'fas fa-info-circle';

        if (data.has_running) {
            message = `<i class="fas fa-spinner fa-spin"></i> <strong>Search Execution In Progress...</strong><br>Processing ${stats.total_executions} queries based on your strategy.`;
            alertClass = 'alert-primary';
        } else if (stats.successful_executions === stats.total_executions && stats.total_executions > 0) {
            message = `<i class="fas fa-check-circle"></i> <strong>Search Completed Successfully!</strong><br>All ${stats.total_executions} queries executed. Retrieved ${stats.total_results} results.`;
            alertClass = 'alert-success';
        } else if (stats.failed_executions > 0) {
            message = `<i class="fas fa-exclamation-triangle"></i> <strong>Search Partially Completed</strong><br>${stats.successful_executions} succeeded, ${stats.failed_executions} failed. You can retry failed executions.`;
            alertClass = 'alert-warning';
        } else if (stats.total_executions === 0) {
            message = `<i class="fas fa-clock"></i> <strong>Search Execution Ready</strong><br>Waiting for search queries to be executed.`;
            alertClass = 'alert-info';
        }

        if (message) {
            messageContainer.className = `alert ${alertClass}`;
            messageContainer.innerHTML = message;
            messageContainer.style.display = 'block';
            
            // Add subtle animation on update
            messageContainer.style.opacity = '0.8';
            setTimeout(() => {
                messageContainer.style.opacity = '1';
            }, 200);
        }
    }

    /**
     * Format status with appropriate icon and color
     */
    function formatStatus(status) {
        const statusMap = {
            'pending': '<span class="badge bg-secondary"><i class="bi bi-clock"></i> Pending</span>',
            'running': '<span class="badge bg-primary"><i class="bi bi-arrow-repeat spin"></i> Running</span>',
            'completed': '<span class="badge bg-success"><i class="bi bi-check-circle"></i> Completed</span>',
            'failed': '<span class="badge bg-danger"><i class="bi bi-x-circle"></i> Failed</span>',
            'cancelled': '<span class="badge bg-warning"><i class="bi bi-slash-circle"></i> Cancelled</span>',
            'rate_limited': '<span class="badge bg-warning"><i class="bi bi-exclamation-triangle"></i> Rate Limited</span>'
        };
        return statusMap[status] || `<span class="badge bg-secondary">${status}</span>`;
    }

    /**
     * Show error message for a query
     */
    function showQueryError(queryRow, error) {
        const errorCell = queryRow.querySelector('.query-error');
        if (errorCell) {
            errorCell.innerHTML = `
                <button class="btn btn-sm btn-outline-danger" 
                        data-bs-toggle="popover" 
                        data-bs-content="${escapeHtml(error)}"
                        title="Error Details">
                    <i class="bi bi-exclamation-triangle"></i>
                </button>
            `;
            // Initialize popover
            const popoverTrigger = errorCell.querySelector('[data-bs-toggle="popover"]');
            if (popoverTrigger) {
                new bootstrap.Popover(popoverTrigger);
            }
        }
    }

    /**
     * Check if we should continue polling
     */
    function shouldContinuePolling(data) {
        const finalStatuses = ['completed', 'failed', 'cancelled'];
        return !finalStatuses.includes(data.session_status);
    }

    /**
     * Handle polling errors
     */
    function handlePollingError(sessionId) {
        retryCount++;
        
        if (retryCount >= CONFIG.maxRetries) {
            stopPolling();
            showError('Failed to get execution status. Please refresh the page.');
        } else {
            // Retry with exponential backoff
            const retryDelay = CONFIG.retryDelay * Math.pow(2, retryCount - 1);
            pollTimer = setTimeout(() => poll(sessionId), retryDelay);
        }
    }

    /**
     * Show completion notification with enhanced feedback
     */
    function showCompletionNotification(data) {
        const stats = data.statistics || {};
        let title, message, type;

        if (stats.successful_executions === stats.total_executions && stats.total_executions > 0) {
            title = 'Search Completed Successfully!';
            message = `All ${stats.total_executions} queries executed successfully. Retrieved ${stats.total_results} results.`;
            type = 'success';
        } else if (stats.failed_executions > 0) {
            title = 'Search Partially Completed';
            message = `${stats.successful_executions} queries succeeded, ${stats.failed_executions} failed. Retrieved ${stats.total_results} results.`;
            type = 'warning';
        } else if (stats.total_executions === 0) {
            title = 'No Queries to Execute';
            message = 'No search queries were found to execute.';
            type = 'info';
        }

        if (title && message) {
            showNotification(title, message, type);
            
            // Update page elements to reflect completion
            updateCompletionState(data);
        }
    }
    
    /**
     * Update page elements when execution completes
     */
    function updateCompletionState(data) {
        // Hide running spinners
        const runningBadges = document.querySelectorAll('.badge .spinner-border');
        runningBadges.forEach(spinner => {
            spinner.remove();
        });
        
        // Show action buttons
        const actionContainer = document.querySelector('.btn-block');
        if (actionContainer) {
            actionContainer.style.display = 'block';
        }
        
        // Update quick actions visibility
        const quickActions = document.querySelector('.text-center.text-muted');
        if (quickActions && data.statistics.successful_executions > 0) {
            quickActions.style.display = 'none';
            
            // Show continue button if results are available
            const continueBtn = document.querySelector('.btn-outline-success');
            if (continueBtn) {
                continueBtn.style.display = 'inline-block';
            }
        }
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Cancel button
        const cancelBtn = document.getElementById('cancel-execution');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', handleCancelExecution);
        }

        // Retry all button
        const retryAllBtn = document.getElementById('retry-all-failed');
        if (retryAllBtn) {
            retryAllBtn.addEventListener('click', handleRetryAll);
        }

        // Individual retry buttons
        document.addEventListener('click', function(e) {
            if (e.target.matches('.retry-query-btn')) {
                handleRetryQuery(e.target);
            }
        });

        // Auto-refresh toggle
        const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', function(e) {
                if (e.target.checked) {
                    startPolling(document.getElementById('execution-status').dataset.sessionId);
                } else {
                    stopPolling();
                }
            });
        }
    }

    /**
     * Handle cancel execution
     */
    function handleCancelExecution(e) {
        e.preventDefault();
        
        if (!confirm('Are you sure you want to cancel the execution?')) {
            return;
        }

        const sessionId = document.getElementById('execution-status').dataset.sessionId;
        const csrfToken = getCsrfToken();

        fetch(`/api/execution/cancel/${sessionId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Execution Cancelled', 'The search execution has been cancelled.', 'warning');
                stopPolling();
                setTimeout(() => location.reload(), 2000);
            } else {
                showError(data.message || 'Failed to cancel execution');
            }
        })
        .catch(error => {
            console.error('Error cancelling execution:', error);
            showError('Failed to cancel execution');
        });
    }

    /**
     * Handle retry all failed queries
     */
    function handleRetryAll(e) {
        e.preventDefault();
        
        const sessionId = document.getElementById('execution-status').dataset.sessionId;
        window.location.href = `/review/session/${sessionId}/execution/recovery/`;
    }

    /**
     * Handle retry individual query
     */
    function handleRetryQuery(button) {
        const executionId = button.dataset.executionId;
        const csrfToken = getCsrfToken();

        button.disabled = true;
        button.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Retrying...';

        fetch(`/api/execution/retry/${executionId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Retry Started', 'The query is being retried.', 'info');
                // Resume polling to show progress
                startPolling(document.getElementById('execution-status').dataset.sessionId);
            } else {
                showError(data.message || 'Failed to retry query');
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Retry';
            }
        })
        .catch(error => {
            console.error('Error retrying query:', error);
            showError('Failed to retry query');
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Retry';
        });
    }

    /**
     * Initialize Bootstrap components
     */
    function initializeBootstrapComponents() {
        // Initialize all tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Initialize all popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function(popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }

    /**
     * Show notification with enhanced styling
     */
    function showNotification(title, message, type = 'info') {
        // Create a modern notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} notification-toast`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            max-width: 400px;
            z-index: 9999;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideInRight 0.3s ease-out;
        `;
        
        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="flex-grow-1">
                    <strong>${title}</strong><br>
                    <small>${message}</small>
                </div>
                <button type="button" class="btn-close ms-2" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.animation = 'slideOutRight 0.3s ease-in';
                setTimeout(() => notification.remove(), 300);
            }
        }, 5000);
        
        // Fallback for browsers without CSS animation support
        if (window.toastr) {
            toastr[type](message, title);
            notification.remove();
        }
    }
    
    /**
     * Update activity feed in real-time
     */
    function updateActivityFeed(activities) {
        const activityContainer = document.querySelector('.card-body[style*="max-height: 400px"]');
        if (!activityContainer || !activities || activities.length === 0) return;
        
        // Clear existing activities
        activityContainer.innerHTML = '';
        
        // Add new activities
        activities.slice(0, 10).forEach(activity => {
            const activityElement = createActivityElement(activity);
            activityContainer.appendChild(activityElement);
        });
    }
    
    /**
     * Create activity element
     */
    function createActivityElement(activity) {
        const div = document.createElement('div');
        div.className = 'activity-item mb-3';
        
        const iconClass = getActivityIcon(activity.type);
        
        div.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="activity-icon me-3">
                    <i class="${iconClass}"></i>
                </div>
                <div class="activity-content flex-grow-1">
                    <div class="activity-title small">${activity.title}</div>
                    <div class="activity-description text-muted small">${activity.description}</div>
                    <div class="activity-time text-muted small">${activity.time_ago}</div>
                </div>
            </div>
        `;
        
        return div;
    }
    
    /**
     * Get appropriate icon for activity type
     */
    function getActivityIcon(type) {
        const iconMap = {
            'status_changed': 'fas fa-exchange-alt text-info',
            'search_executed': 'fas fa-play text-success',
            'search_defined': 'fas fa-edit text-primary',
            'created': 'fas fa-plus text-success',
            'completed': 'fas fa-check-circle text-success',
            'failed': 'fas fa-times-circle text-danger'
        };
        
        return iconMap[type] || 'fas fa-info-circle text-muted';
    }

    /**
     * Show error message
     */
    function showError(message) {
        showNotification('Error', message, 'error');
    }

    /**
     * Get CSRF token
     */
    function getCsrfToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        // Fallback to form input
        const csrfInput = document.querySelector(`input[name="${CONFIG.csrfTokenName}"]`);
        return csrfInput ? csrfInput.value : '';
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Export for external use
    window.ExecutionMonitor = {
        startPolling,
        stopPolling,
        getStatus: () => lastStatus
    };

})();