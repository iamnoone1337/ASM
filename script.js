class SubdomainDashboard {
    constructor() {
        this.storageKey = 'subdomain_scanner_data';
        this.currentView = 'scanner';
        this.currentDomain = '';
        this.allSubdomains = [];
        
        // Configure API endpoints based on environment
        this.configureApiEndpoints();
        
        this.initializeElements();
        this.bindEvents();
        this.loadStoredData();
        this.updateDashboardStats();
    }

    configureApiEndpoints() {
        // Always use backend server for API calls to avoid CORS issues
        this.crtApiBase = 'http://localhost:8001/api/crt';
        this.webarchiveApiBase = 'http://localhost:8001/api/webarchive';
        console.log('Using backend server for all API calls');
    }

    initializeElements() {
        // Scanner elements
        this.domainInput = document.getElementById('domainInput');
        this.searchBtn = document.getElementById('searchBtn');
        this.loadingSection = document.getElementById('loadingSection');
        this.resultsSection = document.getElementById('resultsSection');
        this.errorSection = document.getElementById('errorSection');
        this.subdomainsList = document.getElementById('subdomainsList');
        this.subdomainCount = document.getElementById('subdomainCount');
        this.searchedDomain = document.getElementById('searchedDomain');
        this.filterInput = document.getElementById('filterInput');
        this.exportBtn = document.getElementById('exportBtn');
        this.errorMessage = document.getElementById('errorMessage');
        this.retryBtn = document.getElementById('retryBtn');

        // Navigation elements
        this.scannerTab = document.getElementById('scannerTab');
        this.dashboardTab = document.getElementById('dashboardTab');
        this.scannerView = document.getElementById('scannerView');
        this.dashboardView = document.getElementById('dashboardView');

        // Dashboard elements
        this.totalDomains = document.getElementById('totalDomains');
        this.totalSubdomains = document.getElementById('totalSubdomains');
        this.lastScanTime = document.getElementById('lastScanTime');
        this.totalScans = document.getElementById('totalScans');
        this.scanHistoryList = document.getElementById('scanHistoryList');
        this.domainAnalytics = document.getElementById('domainAnalytics');
        this.clearHistoryBtn = document.getElementById('clearHistoryBtn');
        this.exportAllBtn = document.getElementById('exportAllBtn');
    }

    bindEvents() {
        // Scanner events
        this.searchBtn.addEventListener('click', () => this.searchSubdomains());
        this.domainInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchSubdomains();
            }
        });
        this.filterInput.addEventListener('input', () => this.filterSubdomains());
        this.exportBtn.addEventListener('click', () => this.exportSubdomains());
        this.retryBtn.addEventListener('click', () => this.searchSubdomains());

        // Navigation events
        this.scannerTab.addEventListener('click', () => this.switchView('scanner'));
        this.dashboardTab.addEventListener('click', () => this.switchView('dashboard'));

        // Dashboard events
        this.clearHistoryBtn.addEventListener('click', () => this.clearHistory());
        this.exportAllBtn.addEventListener('click', () => this.exportAllData());
    }

    // Data Management
    loadStoredData() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            this.scanData = stored ? JSON.parse(stored) : {
                domains: {},
                totalScans: 0,
                lastScan: null
            };
        } catch (error) {
            console.error('Error loading stored data:', error);
            this.scanData = {
                domains: {},
                totalScans: 0,
                lastScan: null
            };
        }
    }

    saveData() {
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(this.scanData));
        } catch (error) {
            console.error('Error saving data:', error);
        }
    }

    saveScanResult(domain, subdomains) {
        const timestamp = new Date().toISOString();
        const scanId = `scan_${Date.now()}`;

        // Update or create domain entry
        if (!this.scanData.domains[domain]) {
            this.scanData.domains[domain] = {
                scans: [],
                totalSubdomains: 0,
                firstScan: timestamp,
                lastScan: timestamp
            };
        }

        // Add new scan
        this.scanData.domains[domain].scans.push({
            id: scanId,
            timestamp: timestamp,
            subdomains: subdomains,
            count: subdomains.length
        });

        // Update domain metadata
        this.scanData.domains[domain].totalSubdomains = subdomains.length;
        this.scanData.domains[domain].lastScan = timestamp;

        // Update global metadata
        this.scanData.totalScans++;
        this.scanData.lastScan = timestamp;

        this.saveData();
        this.updateDashboardStats();
        this.updateScanHistory();
    }

    // View Management
    switchView(view) {
        this.currentView = view;

        // Update tab states
        this.scannerTab.classList.toggle('active', view === 'scanner');
        this.dashboardTab.classList.toggle('active', view === 'dashboard');

        // Update view visibility
        this.scannerView.classList.toggle('active', view === 'scanner');
        this.dashboardView.classList.toggle('active', view === 'dashboard');

        if (view === 'dashboard') {
            this.updateDashboardStats();
            this.updateScanHistory();
            this.updateDomainAnalytics();
        }
    }

    // Scanner Functionality
    async searchSubdomains() {
        const domain = this.domainInput.value.trim();
        
        if (!domain) {
            this.showError('Please enter a domain name');
            return;
        }

        if (!this.isValidDomain(domain)) {
            this.showError('Please enter a valid domain name (e.g., example.com)');
            return;
        }

        this.currentDomain = domain;
        this.showLoading();
        this.hideError();
        this.hideResults();

        try {
            // Fetch subdomains from both sources concurrently
            const [crtSubdomains, webArchiveSubdomains] = await Promise.allSettled([
                this.fetchSubdomainsFromCrtSh(domain),
                this.fetchSubdomainsFromWebArchive(domain)
            ]);

            // Combine results from both sources
            const allSubdomains = new Set();
            
            if (crtSubdomains.status === 'fulfilled') {
                crtSubdomains.value.forEach(subdomain => allSubdomains.add(subdomain));
            } else {
                console.warn('crt.sh failed:', crtSubdomains.reason);
            }
            
            if (webArchiveSubdomains.status === 'fulfilled') {
                webArchiveSubdomains.value.forEach(subdomain => allSubdomains.add(subdomain));
            } else {
                console.warn('Web Archive failed:', webArchiveSubdomains.reason);
            }

            const finalSubdomains = Array.from(allSubdomains).sort();
            
            if (finalSubdomains.length === 0) {
                throw new Error('No subdomains found from any source');
            }
            
            this.displayResults(finalSubdomains);
            this.saveScanResult(domain, finalSubdomains);
        } catch (error) {
            console.error('Error fetching subdomains:', error);
            this.showError(`Failed to fetch subdomains: ${error.message}`);
        }
    }

    async fetchSubdomainsFromCrtSh(domain) {
        try {
            // Always use backend server to make API calls
            const url = `${this.crtApiBase}?domain=${encodeURIComponent(domain)}`;
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (!Array.isArray(data)) {
                throw new Error('Invalid response format from crt.sh');
            }

            const subdomains = new Set();
            
            data.forEach(cert => {
                if (cert.name_value) {
                    const names = cert.name_value.split('\n');
                    names.forEach(name => {
                        const cleanName = name.trim().toLowerCase();
                        if (cleanName.endsWith(`.${domain.toLowerCase()}`) || cleanName === domain.toLowerCase()) {
                            subdomains.add(cleanName);
                        }
                    });
                }
            });

            return Array.from(subdomains).sort();
        } catch (error) {
            throw new Error(`Backend server error: ${error.message}`);
        }
    }

    async fetchSubdomainsFromWebArchive(domain) {
        try {
            // Always use backend server to make API calls
            const url = `${this.webarchiveApiBase}?domain=${encodeURIComponent(domain)}`;
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'text/plain',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.text();
            
            if (!data || data.trim() === '') {
                return [];
            }

            const subdomains = new Set();
            const lines = data.split('\n');
            
            lines.forEach(line => {
                if (line.trim()) {
                    try {
                        // Extract URL from CDX line (URL is the first field)
                        const url = line.trim();
                        
                        // Parse URL to extract hostname
                        const urlObj = new URL(url.startsWith('http') ? url : 'http://' + url);
                        const hostname = urlObj.hostname.toLowerCase();
                        
                        // Check if hostname belongs to the target domain
                        if (hostname.endsWith(`.${domain.toLowerCase()}`) || hostname === domain.toLowerCase()) {
                            subdomains.add(hostname);
                        }
                    } catch (e) {
                        // Skip malformed URLs
                        console.debug('Skipping malformed URL:', line);
                    }
                }
            });

            return Array.from(subdomains).sort();
        } catch (error) {
            throw new Error(`Backend server error: ${error.message}`);
        }
    }

    displayResults(subdomains) {
        this.hideLoading();
        this.showResults();
        
        this.searchedDomain.textContent = this.currentDomain;
        this.subdomainCount.textContent = subdomains.length;
        
        this.subdomainsList.innerHTML = '';
        
        if (subdomains.length === 0) {
            this.subdomainsList.innerHTML = `
                <div class="no-results">
                    <i class="fas fa-search"></i>
                    <h3>No subdomains found</h3>
                    <p>No subdomains were found for <strong>${this.currentDomain}</strong> in certificate transparency logs or web archive.</p>
                </div>
            `;
            return;
        }

        subdomains.forEach(subdomain => {
            const subdomainElement = this.createSubdomainElement(subdomain);
            this.subdomainsList.appendChild(subdomainElement);
        });

        this.allSubdomains = subdomains;
    }

    createSubdomainElement(subdomain) {
        const element = document.createElement('div');
        element.className = 'subdomain-item';
        element.dataset.subdomain = subdomain;
        
        const isMainDomain = subdomain === this.currentDomain.toLowerCase();
        const subdomainType = isMainDomain ? 'main' : 'sub';
        
        element.innerHTML = `
            <div class="subdomain-content">
                <div class="subdomain-info">
                    <span class="subdomain-name">${subdomain}</span>
                    <span class="subdomain-type ${subdomainType}">${isMainDomain ? 'Main Domain' : 'Subdomain'}</span>
                </div>
                <div class="subdomain-actions">
                    <button class="action-btn copy-btn" onclick="navigator.clipboard.writeText('${subdomain}')" title="Copy to clipboard">
                        <i class="fas fa-copy"></i>
                    </button>
                    <a href="https://${subdomain}" target="_blank" class="action-btn visit-btn" title="Visit website">
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                </div>
            </div>
        `;
        
        return element;
    }

    filterSubdomains() {
        const filter = this.filterInput.value.toLowerCase();
        const items = this.subdomainsList.querySelectorAll('.subdomain-item');
        
        items.forEach(item => {
            const subdomain = item.dataset.subdomain;
            if (subdomain.includes(filter)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });

        const visibleCount = Array.from(items).filter(item => item.style.display !== 'none').length;
        this.subdomainCount.textContent = visibleCount;
    }

    exportSubdomains() {
        if (!this.allSubdomains || this.allSubdomains.length === 0) {
            return;
        }

        const content = this.allSubdomains.join('\n');
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `subdomains_${this.currentDomain}_${new Date().toISOString().split('T')[0]}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Dashboard Functionality
    updateDashboardStats() {
        const domainCount = Object.keys(this.scanData.domains).length;
        const totalSubdomains = Object.values(this.scanData.domains)
            .reduce((sum, domain) => sum + domain.totalSubdomains, 0);
        
        this.totalDomains.textContent = domainCount;
        this.totalSubdomains.textContent = totalSubdomains;
        this.totalScans.textContent = this.scanData.totalScans;
        
        if (this.scanData.lastScan) {
            const lastScan = new Date(this.scanData.lastScan);
            this.lastScanTime.textContent = this.formatRelativeTime(lastScan);
        } else {
            this.lastScanTime.textContent = 'Never';
        }
    }

    updateScanHistory() {
        const historyContainer = this.scanHistoryList;
        
        // Get all scans sorted by timestamp (most recent first)
        const allScans = [];
        Object.entries(this.scanData.domains).forEach(([domain, domainData]) => {
            domainData.scans.forEach(scan => {
                allScans.push({
                    domain,
                    ...scan,
                    domainData
                });
            });
        });

        allScans.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        if (allScans.length === 0) {
            historyContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <h4>No scans yet</h4>
                    <p>Start by scanning your first domain using the Scanner tab</p>
                </div>
            `;
            return;
        }

        historyContainer.innerHTML = '';
        allScans.slice(0, 20).forEach(scan => { // Show latest 20 scans
            const historyItem = this.createHistoryItem(scan);
            historyContainer.appendChild(historyItem);
        });
    }

    createHistoryItem(scan) {
        const element = document.createElement('div');
        element.className = 'history-item';
        element.dataset.domain = scan.domain;
        element.dataset.scanId = scan.id;

        const scanDate = new Date(scan.timestamp);
        
        element.innerHTML = `
            <div class="history-header">
                <span class="history-domain">${scan.domain}</span>
                <span class="history-date">${this.formatDate(scanDate)}</span>
            </div>
            <div class="history-stats">
                <div class="history-stat">
                    <i class="fas fa-sitemap"></i>
                    <span>${scan.count} subdomains</span>
                </div>
                <div class="history-stat">
                    <i class="fas fa-clock"></i>
                    <span>${this.formatRelativeTime(scanDate)}</span>
                </div>
                <div class="history-stat">
                    <i class="fas fa-history"></i>
                    <span>${scan.domainData.scans.length} total scans</span>
                </div>
            </div>
            <div class="history-actions">
                <button class="history-action" onclick="subdomainDashboard.viewScanDetails('${scan.domain}', '${scan.id}')">
                    <i class="fas fa-eye"></i>
                    View Details
                </button>
                <button class="history-action" onclick="subdomainDashboard.exportScanData('${scan.domain}', '${scan.id}')">
                    <i class="fas fa-download"></i>
                    Export
                </button>
                <button class="history-action" onclick="subdomainDashboard.rescanDomain('${scan.domain}')">
                    <i class="fas fa-redo"></i>
                    Rescan
                </button>
            </div>
        `;

        return element;
    }

    updateDomainAnalytics() {
        const analyticsContainer = this.domainAnalytics;
        const domains = Object.keys(this.scanData.domains);

        if (domains.length === 0) {
            analyticsContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-chart-line"></i>
                    <h4>No data available</h4>
                    <p>Analytics will appear here after you scan some domains</p>
                </div>
            `;
            return;
        }

        // Create simple analytics display
        const topDomains = domains
            .map(domain => ({
                domain,
                ...this.scanData.domains[domain]
            }))
            .sort((a, b) => b.totalSubdomains - a.totalSubdomains)
            .slice(0, 10);

        analyticsContainer.innerHTML = `
            <div class="analytics-content">
                <h4>Top Domains by Subdomain Count</h4>
                <div class="analytics-list">
                    ${topDomains.map(domain => `
                        <div class="analytics-item">
                            <span class="analytics-domain">${domain.domain}</span>
                            <span class="analytics-count">${domain.totalSubdomains} subdomains</span>
                            <span class="analytics-scans">${domain.scans.length} scans</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Dashboard Actions
    async viewScanDetails(domain, scanId) {
        const domainData = this.scanData.domains[domain];
        if (!domainData) return;

        const scan = domainData.scans.find(s => s.id === scanId);
        if (!scan) return;

        // Switch to scanner view and populate with scan data
        this.switchView('scanner');
        this.domainInput.value = domain;
        this.currentDomain = domain;
        this.allSubdomains = scan.subdomains;
        this.displayResults(scan.subdomains);
    }

    exportScanData(domain, scanId) {
        const domainData = this.scanData.domains[domain];
        if (!domainData) return;

        const scan = domainData.scans.find(s => s.id === scanId);
        if (!scan) return;

        const content = scan.subdomains.join('\n');
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `subdomains_${domain}_${new Date(scan.timestamp).toISOString().split('T')[0]}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    async rescanDomain(domain) {
        this.switchView('scanner');
        this.domainInput.value = domain;
        await this.searchSubdomains();
    }

    clearHistory() {
        if (confirm('Are you sure you want to clear all scan history? This action cannot be undone.')) {
            this.scanData = {
                domains: {},
                totalScans: 0,
                lastScan: null
            };
            this.saveData();
            this.updateDashboardStats();
            this.updateScanHistory();
            this.updateDomainAnalytics();
        }
    }

    exportAllData() {
        if (Object.keys(this.scanData.domains).length === 0) {
            alert('No data to export');
            return;
        }

        const exportData = {
            exportDate: new Date().toISOString(),
            summary: {
                totalDomains: Object.keys(this.scanData.domains).length,
                totalScans: this.scanData.totalScans,
                totalSubdomains: Object.values(this.scanData.domains)
                    .reduce((sum, domain) => sum + domain.totalSubdomains, 0)
            },
            domains: this.scanData.domains
        };

        const content = JSON.stringify(exportData, null, 2);
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `subdomain_scanner_export_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Utility Functions
    isValidDomain(domain) {
        const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.([a-zA-Z]{2,}|[a-zA-Z]{2,}\.[a-zA-Z]{2,})$/;
        return domainRegex.test(domain);
    }

    formatDate(date) {
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }

    formatRelativeTime(date) {
        const now = new Date();
        const diff = now - date;
        const minutes = Math.floor(diff / (1000 * 60));
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 30) return `${days}d ago`;
        return date.toLocaleDateString();
    }

    // UI State Management
    showLoading() {
        this.loadingSection.classList.remove('hidden');
        this.searchBtn.disabled = true;
        this.searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Searching...</span>';
    }

    hideLoading() {
        this.loadingSection.classList.add('hidden');
        this.searchBtn.disabled = false;
        this.searchBtn.innerHTML = '<i class="fas fa-search"></i><span>Enumerate</span>';
    }

    showResults() {
        this.resultsSection.classList.remove('hidden');
    }

    hideResults() {
        this.resultsSection.classList.add('hidden');
    }

    showError(message) {
        this.errorMessage.textContent = message;
        this.errorSection.classList.remove('hidden');
        this.hideLoading();
    }

    hideError() {
        this.errorSection.classList.add('hidden');
    }
}

// Global instance for onclick handlers
let subdomainDashboard;

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    subdomainDashboard = new SubdomainDashboard();
});