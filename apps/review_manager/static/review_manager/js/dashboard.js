class DashboardManager {
    constructor() {
        this.initializeFilters();
        this.initializeCards();
        this.initializeMessages();
    }
    
    initializeFilters() {
        // Real-time search
        const searchInput = document.querySelector('input[name="q"]');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.filterSessions(e.target.value);
                }, 300);
            });
        }
    }
    
    initializeCards() {
        // Make cards clickable
        document.querySelectorAll('.session-card').forEach(card => {
            const link = card.querySelector('.primary-action');
            if (link) {
                card.style.cursor = 'pointer';
                card.addEventListener('click', (e) => {
                    if (!e.target.closest('a, button')) {
                        link.click();
                    }
                });
            }
        });
    }
    
    filterSessions(query) {
        // Client-side filtering for immediate feedback
        const cards = document.querySelectorAll('.session-card');
        const lowerQuery = query.toLowerCase();
        
        cards.forEach(card => {
            const title = card.querySelector('.card-title').textContent.toLowerCase();
            const description = card.querySelector('.card-text');
            const descText = description ? description.textContent.toLowerCase() : '';
            
            if (title.includes(lowerQuery) || descText.includes(lowerQuery)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    }
    
    initializeMessages() {
        // Auto-dismiss messages
        document.querySelectorAll('.alert-dismissible').forEach(alert => {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    new DashboardManager();
});