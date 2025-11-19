/**
 * Admin Panel JavaScript - Production Ready
 * Handles AJAX requests, charts, notifications, and interactive features
 */

// ============================================================================
// GLOBAL CONFIGURATION
// ============================================================================
const AdminPanel = {
    config: {
        refreshInterval: 30000, // 30 seconds
        searchDebounceDelay: 500, // 500ms
        toastDuration: 5000, // 5 seconds
        apiEndpoints: {
            blockUser: '/admin/api/users/{email}/block',
            unblockUser: '/admin/api/users/{email}/unblock',
            deleteUser: '/admin/api/users/{email}',
            realtimeStats: '/admin/api/stats/realtime'
        }
    },
    state: {
        csrfToken: null,
        refreshTimer: null,
        charts: {},
        searchTimeout: null
    }
};

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Get CSRF token from page
 */
function getCSRFToken() {
    if (AdminPanel.state.csrfToken) {
        return AdminPanel.state.csrfToken;
    }

    // Try to get from meta tag
    const metaToken = document.querySelector('meta[name="csrf-token"]');
    if (metaToken) {
        AdminPanel.state.csrfToken = metaToken.content;
        return AdminPanel.state.csrfToken;
    }

    // Try to get from hidden input
    const inputToken = document.querySelector('input[name="csrf_token"]');
    if (inputToken) {
        AdminPanel.state.csrfToken = inputToken.value;
        return AdminPanel.state.csrfToken;
    }

    // Try to get from window variable
    if (window.CSRF_TOKEN) {
        AdminPanel.state.csrfToken = window.CSRF_TOKEN;
        return AdminPanel.state.csrfToken;
    }

    console.warn('CSRF token not found');
    return null;
}

/**
 * Format number with commas
 */
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Format currency
 */
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

/**
 * Format date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Debounce function
 */
function debounce(func, delay) {
    let timeoutId;
    return function (...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

/**
 * Show loading overlay
 */
function showLoading() {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.id = 'loading-overlay';
    overlay.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(overlay);
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// ============================================================================
// TOAST NOTIFICATION SYSTEM
// ============================================================================

const Toast = {
    container: null,

    /**
     * Initialize toast container
     */
    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    },

    /**
     * Show toast notification
     */
    show(message, type = 'info', duration = AdminPanel.config.toastDuration) {
        this.init();

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };

        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;

        this.container.appendChild(toast);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateX(100%)';
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }

        return toast;
    },

    success(message, duration) {
        return this.show(message, 'success', duration);
    },

    error(message, duration) {
        return this.show(message, 'error', duration);
    },

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    },

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
};

// ============================================================================
// CONFIRM DIALOG
// ============================================================================

const ConfirmDialog = {
    /**
     * Show confirmation dialog
     */
    show(options = {}) {
        return new Promise((resolve) => {
            const {
                title = 'Confirm Action',
                message = 'Are you sure?',
                confirmText = 'Confirm',
                cancelText = 'Cancel',
                confirmClass = 'btn-danger',
                onConfirm = null,
                onCancel = null
            } = options;

            // Create backdrop
            const backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop';

            // Create modal
            const modal = document.createElement('div');
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-header">
                    <h3 class="modal-title">${title}</h3>
                    <button class="modal-close" id="confirm-close">×</button>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" id="confirm-cancel">${cancelText}</button>
                    <button class="btn ${confirmClass}" id="confirm-action">${confirmText}</button>
                </div>
            `;

            backdrop.appendChild(modal);
            document.body.appendChild(backdrop);

            // Handle confirm
            const confirmBtn = modal.querySelector('#confirm-action');
            confirmBtn.addEventListener('click', () => {
                backdrop.remove();
                if (onConfirm) onConfirm();
                resolve(true);
            });

            // Handle cancel
            const cancelBtn = modal.querySelector('#confirm-cancel');
            const closeBtn = modal.querySelector('#confirm-close');

            const handleCancel = () => {
                backdrop.remove();
                if (onCancel) onCancel();
                resolve(false);
            };

            cancelBtn.addEventListener('click', handleCancel);
            closeBtn.addEventListener('click', handleCancel);
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) handleCancel();
            });
        });
    }
};

// ============================================================================
// AJAX UTILITIES
// ============================================================================

const Ajax = {
    /**
     * Make AJAX request
     */
    async request(url, options = {}) {
        const {
            method = 'GET',
            data = null,
            headers = {},
            includeCSRF = true
        } = options;

        const config = {
            method: method.toUpperCase(),
            headers: {
                'Content-Type': 'application/json',
                ...headers
            },
            credentials: 'same-origin'
        };

        // Add CSRF token for state-changing requests
        if (includeCSRF && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(config.method)) {
            const csrfToken = getCSRFToken();
            if (csrfToken) {
                config.headers['X-CSRF-Token'] = csrfToken;
            }
        }

        // Add request body
        if (data && config.method !== 'GET') {
            if (data instanceof FormData) {
                delete config.headers['Content-Type'];
                config.body = data;
            } else {
                config.body = JSON.stringify(data);
            }
        }

        try {
            const response = await fetch(url, config);
            const responseData = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(responseData.error || responseData.detail || 'Request failed');
            }

            return responseData;
        } catch (error) {
            console.error('AJAX request failed:', error);
            throw error;
        }
    },

    get(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    },

    post(url, data, options = {}) {
        return this.request(url, { ...options, method: 'POST', data });
    },

    put(url, data, options = {}) {
        return this.request(url, { ...options, method: 'PUT', data });
    },

    delete(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    }
};

// ============================================================================
// USER MANAGEMENT FUNCTIONS
// ============================================================================

/**
 * Block user
 */
async function blockUser(email, reason = 'Blocked by admin') {
    try {
        const confirmed = await ConfirmDialog.show({
            title: 'Block User',
            message: `Are you sure you want to block ${email}?`,
            confirmText: 'Block User',
            confirmClass: 'btn-danger'
        });

        if (!confirmed) return;

        showLoading();

        const url = AdminPanel.config.apiEndpoints.blockUser.replace('{email}', email);
        const response = await Ajax.post(url, {
            reason,
            csrf_token: getCSRFToken()
        });

        hideLoading();

        if (response.success) {
            Toast.success(`User ${email} has been blocked`);

            // Update UI
            const row = document.querySelector(`tr[data-email="${email}"]`);
            if (row) {
                const statusBadge = row.querySelector('.user-status');
                if (statusBadge) {
                    statusBadge.textContent = 'Blocked';
                    statusBadge.className = 'badge badge-danger user-status';
                }

                // Update action buttons
                const blockBtn = row.querySelector('.btn-block');
                const unblockBtn = row.querySelector('.btn-unblock');
                if (blockBtn) blockBtn.style.display = 'none';
                if (unblockBtn) unblockBtn.style.display = 'inline-flex';
            }
        } else {
            Toast.error(response.error || 'Failed to block user');
        }
    } catch (error) {
        hideLoading();
        Toast.error('Error blocking user: ' + error.message);
        console.error('Block user error:', error);
    }
}

/**
 * Unblock user
 */
async function unblockUser(email) {
    try {
        const confirmed = await ConfirmDialog.show({
            title: 'Unblock User',
            message: `Are you sure you want to unblock ${email}?`,
            confirmText: 'Unblock User',
            confirmClass: 'btn-success'
        });

        if (!confirmed) return;

        showLoading();

        const url = AdminPanel.config.apiEndpoints.unblockUser.replace('{email}', email);
        const response = await Ajax.post(url, {
            csrf_token: getCSRFToken()
        });

        hideLoading();

        if (response.success) {
            Toast.success(`User ${email} has been unblocked`);

            // Update UI
            const row = document.querySelector(`tr[data-email="${email}"]`);
            if (row) {
                const statusBadge = row.querySelector('.user-status');
                if (statusBadge) {
                    statusBadge.textContent = 'Active';
                    statusBadge.className = 'badge badge-success user-status';
                }

                // Update action buttons
                const blockBtn = row.querySelector('.btn-block');
                const unblockBtn = row.querySelector('.btn-unblock');
                if (blockBtn) blockBtn.style.display = 'inline-flex';
                if (unblockBtn) unblockBtn.style.display = 'none';
            }
        } else {
            Toast.error(response.error || 'Failed to unblock user');
        }
    } catch (error) {
        hideLoading();
        Toast.error('Error unblocking user: ' + error.message);
        console.error('Unblock user error:', error);
    }
}

/**
 * Delete user
 */
async function deleteUser(email) {
    try {
        const confirmed = await ConfirmDialog.show({
            title: 'Delete User',
            message: `⚠️ WARNING: This will permanently delete ${email} and all associated data. This action cannot be undone!`,
            confirmText: 'Delete Permanently',
            confirmClass: 'btn-danger'
        });

        if (!confirmed) return;

        showLoading();

        const url = AdminPanel.config.apiEndpoints.deleteUser.replace('{email}', email);
        const response = await Ajax.delete(url, {
            headers: {
                'X-CSRF-Token': getCSRFToken()
            }
        });

        hideLoading();

        if (response.success) {
            Toast.success(`User ${email} has been permanently deleted`);

            // Remove row from table
            const row = document.querySelector(`tr[data-email="${email}"]`);
            if (row) {
                row.style.opacity = '0';
                setTimeout(() => row.remove(), 300);
            }
        } else {
            Toast.error(response.error || 'Failed to delete user');
        }
    } catch (error) {
        hideLoading();
        Toast.error('Error deleting user: ' + error.message);
        console.error('Delete user error:', error);
    }
}

// ============================================================================
// REAL-TIME STATS UPDATE
// ============================================================================

/**
 * Fetch and update real-time statistics
 */
async function updateRealtimeStats() {
    try {
        const response = await Ajax.get(AdminPanel.config.apiEndpoints.realtimeStats);

        if (response.success && response.stats) {
            const stats = response.stats;

            // Update stat cards
            updateStatElement('total-users', stats.total_users);
            updateStatElement('active-users', stats.active_users);
            updateStatElement('requests-last-hour', stats.requests_last_hour);
            updateStatElement('current-mrr', stats.mrr, true);

            console.log('Real-time stats updated:', stats);
        }
    } catch (error) {
        console.error('Failed to update real-time stats:', error);
    }
}

/**
 * Update stat element value
 */
function updateStatElement(id, value, isCurrency = false) {
    const element = document.getElementById(id);
    if (element) {
        const formattedValue = isCurrency ? formatCurrency(value) : formatNumber(value);

        // Animate value change
        element.style.transform = 'scale(1.1)';
        element.textContent = formattedValue;

        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 200);
    }
}

/**
 * Start auto-refresh
 */
function startAutoRefresh() {
    // Initial update
    updateRealtimeStats();

    // Set interval for periodic updates
    AdminPanel.state.refreshTimer = setInterval(() => {
        updateRealtimeStats();
    }, AdminPanel.config.refreshInterval);

    console.log(`Auto-refresh started (${AdminPanel.config.refreshInterval / 1000}s interval)`);
}

/**
 * Stop auto-refresh
 */
function stopAutoRefresh() {
    if (AdminPanel.state.refreshTimer) {
        clearInterval(AdminPanel.state.refreshTimer);
        AdminPanel.state.refreshTimer = null;
        console.log('Auto-refresh stopped');
    }
}

// ============================================================================
// CHART.JS INITIALIZATION
// ============================================================================

/**
 * Initialize all charts
 */
function initializeCharts() {
    // Chart 1: Requests Over Time (Line Chart)
    initRequestsChart();

    // Chart 2: Plan Distribution (Doughnut Chart)
    initPlanDistributionChart();

    // Chart 3: Success Rate (Line Chart)
    initSuccessRateChart();

    // Chart 4: User Activity (Bar Chart)
    initUserActivityChart();

    // Chart 5: Revenue Forecast (Line Chart)
    initRevenueForecastChart();
}

/**
 * Chart 1: Requests Over Time
 */
function initRequestsChart() {
    const canvas = document.getElementById('requests-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const labels = JSON.parse(canvas.dataset.labels || '[]');
    const data = JSON.parse(canvas.dataset.values || '[]');

    AdminPanel.state.charts.requests = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Requests',
                data: data,
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatNumber(value);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Chart 2: Plan Distribution
 */
function initPlanDistributionChart() {
    const canvas = document.getElementById('plan-distribution-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const labels = JSON.parse(canvas.dataset.labels || '[]');
    const data = JSON.parse(canvas.dataset.values || '[]');

    AdminPanel.state.charts.planDistribution = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    'rgb(156, 163, 175)', // Gray for Free
                    'rgb(59, 130, 246)',  // Blue for Basic
                    'rgb(16, 185, 129)',  // Green for Pro
                    'rgb(245, 158, 11)'   // Orange for Business
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

/**
 * Chart 3: Success Rate Over Time
 */
function initSuccessRateChart() {
    const canvas = document.getElementById('success-rate-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const labels = JSON.parse(canvas.dataset.labels || '[]');
    const data = JSON.parse(canvas.dataset.values || '[]');

    AdminPanel.state.charts.successRate = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Success Rate (%)',
                data: data,
                borderColor: 'rgb(16, 185, 129)',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

/**
 * Chart 4: User Activity (Daily Active Users)
 */
function initUserActivityChart() {
    const canvas = document.getElementById('user-activity-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const labels = JSON.parse(canvas.dataset.labels || '[]');
    const data = JSON.parse(canvas.dataset.values || '[]');

    AdminPanel.state.charts.userActivity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Active Users',
                data: data,
                backgroundColor: 'rgba(59, 130, 246, 0.8)',
                borderColor: 'rgb(59, 130, 246)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * Chart 5: Revenue Forecast
 */
function initRevenueForecastChart() {
    const canvas = document.getElementById('revenue-forecast-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const labels = JSON.parse(canvas.dataset.labels || '[]');
    const data = JSON.parse(canvas.dataset.values || '[]');

    AdminPanel.state.charts.revenueForecast = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Projected MRR',
                data: data,
                borderColor: 'rgb(245, 158, 11)',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                borderDash: [5, 5]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + formatNumber(value);
                        }
                    }
                }
            }
        }
    });
}

// ============================================================================
// SEARCH & FILTER
// ============================================================================

/**
 * Setup search functionality with debouncing
 */
function setupSearch() {
    const searchInput = document.getElementById('user-search');
    if (!searchInput) return;

    const debouncedSearch = debounce((query) => {
        const currentUrl = new URL(window.location.href);

        if (query) {
            currentUrl.searchParams.set('search', query);
        } else {
            currentUrl.searchParams.delete('search');
        }

        currentUrl.searchParams.set('page', '1'); // Reset to first page
        window.location.href = currentUrl.toString();
    }, AdminPanel.config.searchDebounceDelay);

    searchInput.addEventListener('input', (e) => {
        debouncedSearch(e.target.value);
    });
}

/**
 * Setup filter functionality
 */
function setupFilters() {
    const planFilter = document.getElementById('plan-filter');
    const statusFilter = document.getElementById('status-filter');

    if (planFilter) {
        planFilter.addEventListener('change', (e) => {
            const currentUrl = new URL(window.location.href);

            if (e.target.value) {
                currentUrl.searchParams.set('plan', e.target.value);
            } else {
                currentUrl.searchParams.delete('plan');
            }

            currentUrl.searchParams.set('page', '1');
            window.location.href = currentUrl.toString();
        });
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', (e) => {
            const currentUrl = new URL(window.location.href);

            if (e.target.value) {
                currentUrl.searchParams.set('status', e.target.value);
            } else {
                currentUrl.searchParams.delete('status');
            }

            currentUrl.searchParams.set('page', '1');
            window.location.href = currentUrl.toString();
        });
    }
}

// ============================================================================
// FORM VALIDATION
// ============================================================================

/**
 * Validate form
 */
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;

    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');

    requiredFields.forEach(field => {
        const errorElement = field.parentElement.querySelector('.form-error');

        if (!field.value.trim()) {
            isValid = false;
            field.classList.add('error');

            if (errorElement) {
                errorElement.textContent = 'This field is required';
                errorElement.style.display = 'block';
            }
        } else {
            field.classList.remove('error');
            if (errorElement) {
                errorElement.style.display = 'none';
            }
        }
    });

    return isValid;
}

// ============================================================================
// MOBILE MENU TOGGLE
// ============================================================================

/**
 * Setup mobile menu
 */
function setupMobileMenu() {
    const menuToggle = document.getElementById('mobile-menu-toggle');
    const sidebar = document.querySelector('.admin-sidebar');

    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && !menuToggle.contains(e.target)) {
                sidebar.classList.remove('mobile-open');
            }
        });
    }
}

// ============================================================================
// DARK MODE TOGGLE
// ============================================================================

/**
 * Setup dark mode toggle
 */
function setupDarkMode() {
    const darkModeToggle = document.getElementById('dark-mode-toggle');
    if (!darkModeToggle) return;

    // Check for saved preference
    const savedTheme = localStorage.getItem('admin-theme');
    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
    }

    darkModeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('admin-theme', newTheme);
    });
}

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize admin panel when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin Panel initializing...');

    // Get CSRF token
    getCSRFToken();

    // Initialize Toast system
    Toast.init();

    // Initialize charts if Chart.js is available
    if (typeof Chart !== 'undefined') {
        initializeCharts();
    }

    // Setup search and filters
    setupSearch();
    setupFilters();

    // Setup mobile menu
    setupMobileMenu();

    // Setup dark mode
    setupDarkMode();

    // Start auto-refresh on dashboard
    if (window.location.pathname.includes('/dashboard')) {
        startAutoRefresh();
    }

    // Cleanup on page unload
    window.addEventListener('beforeunload', () => {
        stopAutoRefresh();
    });

    // Expose functions globally for onclick handlers
    window.blockUser = blockUser;
    window.unblockUser = unblockUser;
    window.deleteUser = deleteUser;

    console.log('Admin Panel initialized successfully');
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AdminPanel,
        Toast,
        ConfirmDialog,
        Ajax,
        blockUser,
        unblockUser,
        deleteUser
    };
}
