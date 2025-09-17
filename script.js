class SubdomainDashboard {
    constructor() {
        this.storageKey = 'subdomain_scanner_data';
        this.currentView = 'scanner';
        this.currentDomain = '';
        this.allSubdomains = [];
        this.currentMetadata = {}; // subdomain -> meta

        // Configure API endpoints based on environment
        this.configureApiEndpoints();

        // Inject minimal UI styles (sidebar + table + status badges)
        this.injectUIStyles();

        this.initializeElements();
        this.bindEvents();
        this.loadStoredData();
        this.updateDashboardStats();
    }

    injectUIStyles() {
        const css = `
        /* App shell layout */
        .app-shell { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; background: #f8fafc; }
        .sidebar { background: #ffffff; border-right: 1px solid #e5e7eb; padding: 16px; }
        .content { min-width: 0; }

        /* Sidebar nav */
        .sidebar-nav { display: flex; flex-direction: column; gap: 8px; }
        .nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 16px; color: #374151; font-weight: 600; cursor: default; }
        .nav-item i { color: #6b7280; }
        .nav-item.active { background: #ffe8d9; color: #f97316; }
        .nav-item.active i { color: #f97316; }
        .nav-group > summary { list-style: none; cursor: pointer; }
        .nav-group > summary::-webkit-details-marker { display: none; }
        .nav-group .chevron { margin-left: auto; font-size: 12px; }
        .nav-subitems { display: flex; flex-direction: column; gap: 6px; padding-left: 10px; margin-left: 8px; border-left: 2px solid #f1f5f9; }
        .nav-subitem { color: #374151; font-weight: 600; padding: 6px 10px; border-radius: 10px; }
        .nav-subitem:hover { background: #f3f4f6; }
        .nav-subitem.active { background: #e0ecff; color: #1d4ed8; }

        /* Table */
        .table-wrap { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden; }
        table.sd-table { width: 100%; border-collapse: separate; border-spacing: 0; }
        .sd-table thead th { background: #f9fafb; text-align: left; font-weight: 700; font-size: 13px; color: #374151; padding: 10px 12px; border-bottom: 1px solid #e5e7eb; }
        .sd-table tbody td { padding: 10px 12px; font-size: 14px; color: #111827; border-bottom: 1px solid #f3f4f6; vertical-align: middle; }
        .sd-table tbody tr:hover { background: #f9fafb; }
        .sd-table .col-actions { white-space: nowrap; }

        /* Status badge colors (teal OK, amber warn, red down, grey unknown) */
        .status-badge { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; border-radius: 999px; font-weight:700; font-size:12px; border:1px solid #cbd5e0; background:#e2e8f0; color:#2d3748; }
        .status-badge .dot { width:8px; height:8px; border-radius:50%; background:#a0aec0; }
        .status-up { background:#e6fffa; color:#276749; border-color:#9ae6b4; }
        .status-up .dot { background:#38a169; }
        .status-warn { background:#fffaf0; color:#975a16; border-color:#f6ad55; }
        .status-warn .dot { background:#dd6b20; }
        .status-down { background:#fff5f5; color:#9b2c2c; border-color:#fc8181; }
        .status-down .dot { background:#e53e3e; }
        .status-unknown { background:#edf2f7; color:#4a5568; border-color:#cbd5e0; }
        .status-unknown .dot { background:#a0aec0; }

        .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
        `;
        const style = document.createElement('style');
        style.setAttribute('data-injected', 'ui-styles');
        style.textContent = css;
        document.head.appendChild(style);
    }

    configureApiEndpoints() {
        const apiBaseMetaTag = document.querySelector('meta[name="api-base-url"]');
        let apiBase;
        if (apiBaseMetaTag && apiBaseMetaTag.content) {
            apiBase = apiBaseMetaTag.content.replace(/\/$/, '');
        } else {
            apiBase = `${window.location.origin}/api`;
        }
        this.crtApiBase = `${apiBase}/crt`;
        this.metaApiBase = `${apiBase}/meta`;
        this.waybackApiBase = `${apiBase}/wayback`;
        this.subfinderApiBase = `${apiBase}/subfinder`;
    }

    initializeElements() {
        // Scanner elements
        this.domainInput = document.getElementById('domainInput');
        this.searchBtn = document.getElementById('searchBtn');
        this.loadingSection = document.getElementById('loadingSection');
        this.resultsSection = document.getElementById('resultsSection');
        this.errorSection = document.getElementById('errorSection');
        this.subdomainsTableBody = document.getElementById('subdomainsTableBody');
        this.subdomainCount = document.getElementById('subdomainCount');
        this.searchedDomain = document.getElementById('searchedDomain');
        this.filterInput = document.getElementById('filterInput');
        this.exportBtn = document.getElementById('exportBtn');
        this.errorMessage = document.getElementById('errorMessage');
        this.retryBtn = document.getElementById('retryBtn');

        // Left navigation elements
        this.leftScannerLink = document.getElementById('leftScannerLink');
        this.leftDashboardLink = document.getElementById('leftDashboardLink');

        // Views
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
            if (e.key === 'Enter') this.searchSubdomains();
        });
        this.filterInput.addEventListener('input', () => this.filterSubdomains());
        this.exportBtn.addEventListener('click', () => this.exportSubdomains());
        this.retryBtn.addEventListener('click', () => this.searchSubdomains());

        // Left navigation switching
        this.leftScannerLink.addEventListener('click', () => this.switchView('scanner'));
        this.leftDashboardLink.addEventListener('click', () => this.switchView('dashboard'));

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

    saveScanResult(domain, subdomains, metadataMap = {}) {
        const timestamp = new Date().toISOString();
        const scanId = `scan_${Date.now()}`;

        if (!this.scanData.domains[domain]) {
            this.scanData.domains[domain] = {
                scans: [],
                totalSubdomains: 0,
                firstScan: timestamp,
                lastScan: timestamp
            };
        }

        this.scanData.domains[domain].scans.push({
            id: scanId,
            timestamp: timestamp,
            subdomains: subdomains,
            metadata: metadataMap,
            count: subdomains.length
        });

        this.scanData.domains[domain].totalSubdomains = subdomains.length;
        this.scanData.domains[domain].lastScan = timestamp;

        this.scanData.totalScans++;
        this.scanData.lastScan = timestamp;

        this.saveData();
        this.updateDashboardStats();
        this.updateScanHistory();
    }

    // View Management
    switchView(view) {
        this.currentView = view;

        // Left nav active states
        this.leftScannerLink.classList.toggle('active', view === 'scanner');
        this.leftDashboardLink.classList.toggle('active', view === 'dashboard');

        // View visibility
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
            // Fetch from all sources in parallel
            const [crtSubdomains, waybackSubdomains, subfinderSubdomains] = await Promise.allSettled([
                this.fetchSubdomainsFromCrtSh(domain),
                this.fetchSubdomainsFromWayback(domain),
                this.fetchSubdomainsFromSubfinder(domain)
            ]);

            const crtList = crtSubdomains.status === 'fulfilled' ? crtSubdomains.value : [];
            const wbList = waybackSubdomains.status === 'fulfilled' ? waybackSubdomains.value : [];
            const sfList = subfinderSubdomains.status === 'fulfilled' ? subfinderSubdomains.value : [];

            // Merge and deduplicate
            const merged = new Set([...crtList, ...wbList, ...sfList]);
            const finalSubdomains = Array.from(merged).sort();

            if (finalSubdomains.length === 0) {
                throw new Error('No subdomains found from crt.sh, Wayback, or Subfinder');
            }

            // Draw the table first
            this.displayResults(finalSubdomains);

            // Then enrich with metadata in batches
            this.currentMetadata = {};
            await this.enrichSubdomainsWithMetadata(finalSubdomains);

            // Save scan including metadata
            this.saveScanResult(domain, finalSubdomains, this.currentMetadata);
        } catch (error) {
            console.error('Error fetching subdomains:', error);
            this.showError(`Failed to fetch subdomains: ${error.message}`);
        }
    }

    async fetchSubdomainsFromCrtSh(domain) {
        try {
            const url = `${this.crtApiBase}?domain=${encodeURIComponent(domain)}`;
            const response = await fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' }});
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            if (!Array.isArray(data)) throw new Error('Invalid response format from crt.sh');

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
            console.warn('CRT fetch failed:', error);
            return [];
        }
    }

    async fetchSubdomainsFromWayback(domain) {
        try {
            const url = `${this.waybackApiBase}?domain=${encodeURIComponent(domain)}`;
            const response = await fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' }});
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            if (!Array.isArray(data)) throw new Error('Invalid response format from Wayback');
            const normalized = data
                .filter(Boolean)
                .map(s => String(s).trim().toLowerCase())
                .filter(s => s.endsWith(`.${domain.toLowerCase()}`) || s === domain.toLowerCase());
            return Array.from(new Set(normalized)).sort();
        } catch (error) {
            console.warn('Wayback fetch failed:', error);
            return [];
        }
    }

    async fetchSubdomainsFromSubfinder(domain) {
        try {
            const url = `${this.subfinderApiBase}?domain=${encodeURIComponent(domain)}`;
            const response = await fetch(url, { method: 'GET', headers: { 'Accept': 'application/json' }});
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            if (!Array.isArray(data)) throw new Error('Invalid response format from Subfinder');
            const normalized = data
                .filter(Boolean)
                .map(s => String(s).trim().toLowerCase())
                .filter(s => s.endsWith(`.${domain.toLowerCase()}`) || s === domain.toLowerCase());
            return Array.from(new Set(normalized)).sort();
        } catch (error) {
            console.warn('Subfinder fetch failed:', error);
            return [];
        }
    }

    async enrichSubdomainsWithMetadata(subdomains) {
        const batchSize = 25;
        for (let i = 0; i < subdomains.length; i += batchSize) {
            const batch = subdomains.slice(i, i + batchSize);
            try {
                const results = await this.fetchMetadataBatch(batch);
                results.forEach(res => {
                    const host = res.host || '';
                    if (!host) return;
                    this.currentMetadata[host] = res;
                    this.updateSubdomainItemUI(host, res);
                });
            } catch (e) {
                console.warn('Metadata batch failed:', e);
            }
        }
    }

    async fetchMetadataBatch(hosts) {
        const resp = await fetch(this.metaApiBase, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify({ hosts, timeout_ms: 4000 })
        });
        if (!resp.ok) throw new Error(`Meta API error: ${resp.status}`);
        return await resp.json();
    }

    // Tabular rendering
    displayResults(subdomains) {
        this.hideLoading();
        this.showResults();

        this.searchedDomain.textContent = this.currentDomain;
        this.subdomainCount.textContent = subdomains.length;

        this.subdomainsTableBody.innerHTML = '';

        if (subdomains.length === 0) {
            this.subdomainsTableBody.innerHTML = `
                <tr><td colspan="6">
                    <div class="no-results">
                        <i class="fas fa-search"></i>
                        <h3>No subdomains found</h3>
                        <p>No subdomains were found for <strong>${this.currentDomain}</strong> in crt.sh, Wayback, or Subfinder.</p>
                    </div>
                </td></tr>
            `;
            return;
        }

        const frag = document.createDocumentFragment();
        subdomains.forEach(sd => frag.appendChild(this.createSubdomainRow(sd)));
        this.subdomainsTableBody.appendChild(frag);

        this.allSubdomains = subdomains;
    }

    createSubdomainRow(subdomain) {
        const tr = document.createElement('tr');
        tr.className = 'subdomain-row';
        tr.dataset.subdomain = subdomain;

        tr.innerHTML = `
            <td class="col-subdomain">
                <div class="sd-cell">
                    <span class="subdomain-name">${subdomain}</span>
                </div>
            </td>
            <td class="col-status">
                <span class="status-badge status-unknown" data-role="status" title="Checking...">
                    <span class="dot"></span>
                    <span data-role="status-text">Checking</span>
                </span>
            </td>
            <td class="col-title" data-role="title"></td>
            <td class="col-scheme" data-role="scheme"></td>
            <td class="col-elapsed" data-role="elapsed"></td>
            <td class="col-actions">
                <button class="action-btn copy-btn" title="Copy" aria-label="Copy subdomain">
                    <i class="fas fa-copy"></i>
                </button>
                <a href="https://${subdomain}" target="_blank" class="action-btn visit-btn" title="Open" aria-label="Open subdomain">
                    <i class="fas fa-external-link-alt"></i>
                </a>
            </td>
        `;

        const copyBtn = tr.querySelector('.copy-btn');
        copyBtn.addEventListener('click', () => navigator.clipboard.writeText(subdomain));

        return tr;
    }

    updateSubdomainItemUI(subdomain, meta) {
        const selector = `.subdomain-row[data-subdomain="${window.CSS && CSS.escape ? CSS.escape(subdomain) : subdomain}"]`;
        const row = this.subdomainsTableBody.querySelector(selector);
        if (!row) return;

        const badge = row.querySelector('[data-role="status"]');
        const statusText = row.querySelector('[data-role="status-text"]');
        const titleEl = row.querySelector('[data-role="title"]');
        const schemeEl = row.querySelector('[data-role="scheme"]');
        const elapsedEl = row.querySelector('[data-role="elapsed"]');

        const status = typeof meta?.status_code === 'number' ? meta.status_code : null;
        const title = meta?.title || '';
        const scheme = meta?.scheme || '';
        const elapsed = typeof meta?.elapsed_ms === 'number' ? `${meta.elapsed_ms}ms` : '';
        const url = meta?.url || `https://${subdomain}`;
        const checkedAt = meta?.checked_at || '';
        const error = meta?.error || '';

        // Reset classes
        badge.classList.remove('status-up', 'status-warn', 'status-down', 'status-unknown');

        let cls = 'status-unknown';
        let label = 'No Response';
        let display = 'No Response';
        if (status === null) {
            cls = 'status-unknown';
            display = 'No Response';
        } else if (status >= 200 && status < 300) {
            cls = 'status-up';
            label = 'OK';
            display = `${status} ${label}`;
        } else if (status >= 300 && status < 400) {
            cls = 'status-up';
            label = 'Redirect';
            display = `${status} ${label}`;
        } else if (status >= 400 && status < 500) {
            cls = 'status-warn';
            label = 'Client Error';
            display = `${status} ${label}`;
        } else {
            cls = 'status-down';
            label = 'Server Error';
            display = `${status} ${label}`;
        }
        badge.classList.add(cls);
        statusText.textContent = display;

        titleEl.textContent = title || '';
        schemeEl.textContent = scheme || '';
        elapsedEl.textContent = elapsed || '';

        const tooltip = [
            `URL: ${url}`,
            `Status: ${status !== null ? status : 'No Response'}${status !== null ? ` (${label})` : ''}`,
            elapsed ? `Latency: ${elapsed}` : '',
            checkedAt ? `Checked: ${new Date(checkedAt).toLocaleString()}` : '',
            error ? `Error: ${error}` : ''
        ].filter(Boolean).join('\n');
        badge.title = tooltip;

        // Update open link to correct scheme if available
        const openLink = row.querySelector('.visit-btn');
        if (openLink && meta?.scheme) openLink.href = `${meta.scheme}://${subdomain}`;
    }

    filterSubdomains() {
        const filter = this.filterInput.value.toLowerCase();
        const rows = this.subdomainsTableBody.querySelectorAll('.subdomain-row');

        rows.forEach(row => {
            const sub = row.dataset.subdomain.toLowerCase();
            const status = (row.querySelector('[data-role="status-text"]')?.textContent || '').toLowerCase();
            const title = (row.querySelector('[data-role="title"]')?.textContent || '').toLowerCase();
            const visible = sub.includes(filter) || status.includes(filter) || title.includes(filter);
            row.style.display = visible ? '' : 'none';
        });

        const visibleCount = Array.from(rows).filter(r => r.style.display !== 'none').length;
        this.subdomainCount.textContent = visibleCount;
    }

    exportSubdomains() {
        if (!this.allSubdomains || this.allSubdomains.length === 0) return;
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

        const allScans = [];
        Object.entries(this.scanData.domains).forEach(([domain, domainData]) => {
            domainData.scans.forEach(scan => {
                allScans.push({ domain, ...scan, domainData });
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
        allScans.slice(0, 20).forEach(scan => {
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

        const topDomains = domains
            .map(domain => ({ domain, ...this.scanData.domains[domain] }))
            .sort((a, b) => b.totalSubdomains - a.totalSubdomains)
            .slice(0, 10);

        const httpOverview = [];
        topDomains.forEach(d => {
            const lastScan = d.scans[d.scans.length - 1];
            const meta = (lastScan && lastScan.metadata) || {};
            const counters = { up: 0, warn: 0, down: 0, unknown: 0 };
            Object.values(meta).forEach(m => {
                const s = m?.status_code;
                if (typeof s !== 'number') counters.unknown++;
                else if (s >= 200 && s < 400) counters.up++;
                else if (s >= 400 && s < 500) counters.warn++;
                else counters.down++;
            });
            httpOverview.push({ domain: d.domain, counters, total: d.totalSubdomains });
        });

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

                <h4 style="margin-top: 20px;">HTTP Status Overview (latest scan)</h4>
                <div class="analytics-list">
                    ${httpOverview.map(row => `
                        <div class="analytics-item">
                            <span class="analytics-domain">${row.domain}</span>
                            <span class="status-badge status-up"><span class="dot"></span>Up: ${row.counters.up}</span>
                            <span class="status-badge status-warn"><span class="dot"></span>4xx: ${row.counters.warn}</span>
                            <span class="status-badge status-down"><span class="dot"></span>5xx: ${row.counters.down}</span>
                            <span class="status-badge status-unknown"><span class="dot"></span>No Resp: ${row.counters.unknown}</span>
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

        this.switchView('scanner');
        this.domainInput.value = domain;
        this.currentDomain = domain;
        this.allSubdomains = scan.subdomains;
        this.currentMetadata = scan.metadata || {};
        this.displayResults(scan.subdomains);
        this.applyMetadataToUI(this.currentMetadata);
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
            this.scanData = { domains: {}, totalScans: 0, lastScan: null };
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
                totalSubdomains: Object.values(this.scanData.domains).reduce((sum, d) => sum + d.totalSubdomains, 0)
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

    // UI State
    showLoading() {
        this.loadingSection.classList.remove('hidden');
        this.searchBtn.disabled = true;
        this.searchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>Enumerating...</span>';
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

    applyMetadataToUI(metadataMap) {
        Object.entries(metadataMap || {}).forEach(([host, meta]) => {
            this.updateSubdomainItemUI(host, meta);
        });
    }
}

// Global instance
let subdomainDashboard;

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    subdomainDashboard = new SubdomainDashboard();
});
