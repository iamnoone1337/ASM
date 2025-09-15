class SubdomainEnumerator {
    constructor() {
        this.initializeElements();
        this.bindEvents();
        this.currentDomain = '';
    }

    initializeElements() {
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
    }

    bindEvents() {
        this.searchBtn.addEventListener('click', () => this.searchSubdomains());
        this.domainInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.searchSubdomains();
            }
        });
        this.filterInput.addEventListener('input', () => this.filterSubdomains());
        this.exportBtn.addEventListener('click', () => this.exportSubdomains());
        this.retryBtn.addEventListener('click', () => this.searchSubdomains());
    }

    async searchSubdomains() {
        const domain = this.domainInput.value.trim();
        
        if (!domain) {
            this.showError('Please enter a domain name');
            return;
        }

        // Basic domain validation
        if (!this.isValidDomain(domain)) {
            this.showError('Please enter a valid domain name (e.g., example.com)');
            return;
        }

        this.currentDomain = domain;
        this.showLoading();
        this.hideError();
        this.hideResults();

        try {
            const subdomains = await this.fetchSubdomainsFromCrtSh(domain);
            this.displayResults(subdomains);
        } catch (error) {
            console.error('Error fetching subdomains:', error);
            this.showError(`Failed to fetch subdomains: ${error.message}`);
        }
    }

    async fetchSubdomainsFromCrtSh(domain) {
        const url = `https://crt.sh/?q=%.${domain}&output=json`;
        
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

        // Extract unique subdomains
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
                    <p>No subdomains were found for <strong>${this.currentDomain}</strong> in certificate transparency logs.</p>
                </div>
            `;
            return;
        }

        subdomains.forEach(subdomain => {
            const subdomainElement = this.createSubdomainElement(subdomain);
            this.subdomainsList.appendChild(subdomainElement);
        });

        // Store subdomains for filtering and export
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

        // Update count
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

    isValidDomain(domain) {
        const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.([a-zA-Z]{2,}|[a-zA-Z]{2,}\.[a-zA-Z]{2,})$/;
        return domainRegex.test(domain);
    }

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

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new SubdomainEnumerator();
});