// Dashboard functionality for Genesis Replicator Admin Interface

document.addEventListener('DOMContentLoaded', function() {
    // Initialize real-time updates
    initializeMetricsUpdate();

    // Set up event listeners
    setupEventListeners();
});

function initializeMetricsUpdate() {
    // Update metrics every 5 seconds
    setInterval(async () => {
        try {
            const response = await fetch('/api/metrics');
            const metrics = await response.json();
            updateMetricsDisplay(metrics);
        } catch (error) {
            console.error('Failed to update metrics:', error);
        }
    }, 5000);
}

function updateMetricsDisplay(metrics) {
    // Update each metric card with new values
    Object.entries(metrics).forEach(([key, value]) => {
        const element = document.querySelector(`[data-metric="${key}"]`);
        if (element) {
            element.textContent = formatMetricValue(key, value);
        }
    });
}

function formatMetricValue(key, value) {
    // Format metric values based on their type
    switch (key) {
        case 'cpu_usage':
        case 'memory_usage':
        case 'disk_usage':
            return `${value}%`;
        default:
            return value;
    }
}

function setupEventListeners() {
    // Add click handlers for interactive elements
    document.querySelectorAll('.metric-card').forEach(card => {
        card.addEventListener('click', () => {
            const metricType = card.getAttribute('data-metric-type');
            if (metricType) {
                showMetricDetails(metricType);
            }
        });
    });
}

function showMetricDetails(metricType) {
    // Show detailed view for the selected metric
    console.log(`Showing details for: ${metricType}`);
    // Implementation placeholder for metric details modal
}

// Error handling
window.addEventListener('error', function(event) {
    console.error('Dashboard error:', event.error);
    // Implementation placeholder for error reporting
});
