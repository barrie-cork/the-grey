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
     * Update statistics cards
     */
    function updateStatistics(data) {
        // Total queries
        const totalQueriesElement = document.getElementById('total-queries');
        if (totalQueriesElement) {
            totalQueriesElement.textContent = data.total_queries || 0;
        }

        // Completed queries
        const completedElement = document.getElementById('completed-queries');
        if (completedElement) {
            completedElement.textContent = data.completed_queries || 0;
        }

        // Total results
        const totalResultsElement = document.getElementById('total-results');
        if (totalResultsElement) {
            totalResultsElement.textContent = data.total_results || 0;
        }

        // Total cost
        const totalCostElement = document.getElementById('total-cost');
        if (totalCostElement) {
            totalCostElement.textContent = `$${(data.total_cost || 0).toFixed(3)}`;
        }

        // Failed queries
        const failedElement = document.getElementById('failed-queries');
        if (failedElement) {
            failedElement.textContent = data.failed_queries || 0;
            if (data.failed_queries > 0) {
                failedElement.classList.add('text-danger');
            }
        }
    }

    /**
     * Update status message
     */
    function updateStatusMessage(data) {
        const messageContainer = document.getElementById('status-message');
        if (!messageContainer) return;

        let message = '';
        let alertClass = 'alert-info';

        switch (data.session_status) {
            case 'executing':
                message = `Executing search queries... ${data.completed_queries} of ${data.total_queries} completed.`;
                break;
            case 'processing':
                message = 'Processing search results...';
                break;
            case 'completed':
                message = `Search completed successfully! Retrieved ${data.total_results} results.`;
                alertClass = 'alert-success';
                break;
            case 'failed':
                message = `Search failed with ${data.failed_queries} errors. You can retry failed queries.`;
                alertClass = 'alert-danger';
                break;
            case 'partial':
                message = `Search partially completed. ${data.completed_queries} queries succeeded, ${data.failed_queries} failed.`;
                alertClass = 'alert-warning';
                break;
        }

        if (message) {
            messageContainer.className = `alert ${alertClass}`;
            messageContainer.textContent = message;
            messageContainer.style.display = 'block';
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
     * Show completion notification
     */
    function showCompletionNotification(data) {
        let title, message, type;

        if (data.session_status === 'completed') {
            title = 'Search Completed!';
            message = `Successfully retrieved ${data.total_results} results.`;
            type = 'success';
        } else if (data.session_status === 'failed') {
            title = 'Search Failed';
            message = `${data.failed_queries} queries failed. You can retry them from the error recovery page.`;
            type = 'error';
        } else if (data.failed_queries > 0) {
            title = 'Search Partially Completed';
            message = `Retrieved ${data.total_results} results. ${data.failed_queries} queries failed.`;
            type = 'warning';
        }

        if (title && message) {
            showNotification(title, message, type);
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
     * Show notification
     */
    function showNotification(title, message, type = 'info') {
        // If using a notification library like toastr
        if (window.toastr) {
            toastr[type](message, title);
        } else {
            // Fallback to alert
            alert(`${title}\n\n${message}`);
        }
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