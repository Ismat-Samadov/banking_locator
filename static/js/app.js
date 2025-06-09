// Banking Locator - Frontend JavaScript

class BankingLocator {
    constructor() {
        this.map = null;
        this.userLocation = null;
        this.markers = [];
        this.userMarker = null;
        this.currentView = 'map'; // 'map' or 'list'
        this.isLoading = false;
        this.nearbyLocations = [];
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeApp();
    }

    setupEventListeners() {
        // Location controls
        document.getElementById('refresh-location')?.addEventListener('click', () => {
            this.getCurrentLocation();
        });

        document.getElementById('enable-location')?.addEventListener('click', () => {
            this.getCurrentLocation();
        });

        document.getElementById('locate-me')?.addEventListener('click', () => {
            this.centerMapOnUser();
        });

        // View toggle
        document.getElementById('toggle-view')?.addEventListener('click', () => {
            this.toggleView();
        });

        // Filters
        document.getElementById('apply-filters')?.addEventListener('click', () => {
            this.applyFilters();
        });

        // Modal controls
        document.getElementById('close-error')?.addEventListener('click', () => {
            this.hideModal('error-modal');
        });

        document.getElementById('retry-location')?.addEventListener('click', () => {
            this.hideModal('error-modal');
            this.getCurrentLocation();
        });

        document.getElementById('manual-location')?.addEventListener('click', () => {
            this.hideModal('error-modal');
            this.promptManualLocation();
        });

        // Panel controls
        document.getElementById('close-panel')?.addEventListener('click', () => {
            this.toggleInfoPanel(false);
        });
    }

    async initializeApp() {
        this.showLoading(true);
        
        try {
            // Initialize map
            this.initializeMap();
            
            // Get user's location
            await this.getCurrentLocation();
            
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Failed to initialize the application');
        } finally {
            this.showLoading(false);
        }
    }

    initializeMap() {
        // Initialize Leaflet map
        this.map = L.map('map').setView([40.3777, 49.8920], 13); // Default to Baku

        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(this.map);

        // Map click handler
        this.map.on('click', (e) => {
            this.handleMapClick(e);
        });
    }

    async getCurrentLocation() {
        this.updateLocationStatus('loading', 'Getting your location...');
        
        if (!navigator.geolocation) {
            this.showLocationError('Geolocation is not supported by this browser');
            return;
        }

        const options = {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 300000 // 5 minutes
        };

        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, options);
            });

            const { latitude, longitude } = position.coords;
            this.userLocation = { lat: latitude, lng: longitude };

            // Update map
            this.updateMapLocation(latitude, longitude);
            
            // Get location information
            await this.getLocationInfo(latitude, longitude);
            
            this.updateLocationStatus('success', 'Location found');

        } catch (error) {
            console.error('Geolocation error:', error);
            this.handleLocationError(error);
        }
    }

    handleLocationError(error) {
        let message = 'Unable to get your location';
        
        switch (error.code) {
            case error.PERMISSION_DENIED:
                message = 'Location access denied. Please enable location services.';
                break;
            case error.POSITION_UNAVAILABLE:
                message = 'Location information unavailable.';
                break;
            case error.TIMEOUT:
                message = 'Location request timed out.';
                break;
        }
        
        this.showLocationError(message);
    }

    showLocationError(message) {
        this.updateLocationStatus('error', message);
        document.getElementById('enable-location').style.display = 'block';
        
        // Show error modal
        document.getElementById('error-message').textContent = message;
        this.showModal('error-modal');
    }

    updateMapLocation(lat, lng) {
        // Remove existing user marker
        if (this.userMarker) {
            this.map.removeLayer(this.userMarker);
        }

        // Add user marker
        const userIcon = L.divIcon({
            className: 'user-marker',
            html: `<div style="background: #2563eb; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        this.userMarker = L.marker([lat, lng], { icon: userIcon })
            .addTo(this.map)
            .bindPopup('Your Location');

        // Center map on user location
        this.map.setView([lat, lng], 14);
    }

    async getLocationInfo(lat, lng) {
        try {
            const response = await fetch('/api/location-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ lat, lng })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Update UI with location info
            this.updateLocationDetails(data);
            this.updateExchangeRates(data.exchange_rates, data.base_currency);
            
            // Get nearby banking locations
            await this.getNearbyBanking(lat, lng);

        } catch (error) {
            console.error('Error getting location info:', error);
            this.showError('Failed to get location information');
        }
    }

    async getNearbyBanking(lat, lng) {
        const radius = document.getElementById('search-radius').value;
        const type = document.getElementById('location-type').value;

        try {
            const params = new URLSearchParams({
                lat: lat,
                lng: lng,
                radius: radius,
                type: type
            });

            const response = await fetch(`/api/nearby-banking?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.nearbyLocations = data.locations;
            
            // Update map markers
            this.updateMapMarkers(data.locations);
            
            // Update list view
            this.updateBankingList(data.locations);
            
            // Update results count
            document.getElementById('results-count').textContent = 
                `${data.total} result${data.total !== 1 ? 's' : ''}`;

        } catch (error) {
            console.error('Error getting nearby banking:', error);
            this.showError('Failed to find nearby banking services');
        }
    }

    updateMapMarkers(locations) {
        // Clear existing markers (except user marker)
        this.markers.forEach(marker => {
            this.map.removeLayer(marker);
        });
        this.markers = [];

        // Add new markers
        locations.forEach(location => {
            const isBank = location.type === 'bank';
            const iconColor = isBank ? '#10b981' : '#f59e0b';
            
            const icon = L.divIcon({
                className: 'banking-marker',
                html: `
                    <div style="
                        background: ${iconColor}; 
                        width: 16px; 
                        height: 16px; 
                        border-radius: 50%; 
                        border: 2px solid white; 
                        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                        position: relative;
                    ">
                        <div style="
                            position: absolute;
                            top: -8px;
                            left: -8px;
                            width: 32px;
                            height: 32px;
                            border-radius: 50%;
                            background: ${iconColor}20;
                            animation: ping 2s infinite;
                        "></div>
                    </div>
                `,
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            });

            const marker = L.marker([location.lat, location.lng], { icon })
                .addTo(this.map)
                .bindPopup(this.createMarkerPopup(location));

            marker.on('click', () => {
                this.selectBankingLocation(location);
            });

            this.markers.push(marker);
        });
    }

    createMarkerPopup(location) {
        return `
            <div class="marker-popup">
                <div style="font-weight: 600; margin-bottom: 0.5rem;">${location.name}</div>
                <div style="font-size: 0.875rem; color: #64748b; margin-bottom: 0.5rem;">${location.address}</div>
                <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <span style="
                        background: ${location.type === 'bank' ? '#10b981' : '#f59e0b'}; 
                        color: white; 
                        padding: 0.25rem 0.5rem; 
                        border-radius: 0.25rem; 
                        font-size: 0.75rem;
                        text-transform: uppercase;
                    ">${location.type}</span>
                    <span style="font-size: 0.875rem; color: #64748b;">${location.distance} km away</span>
                </div>
                <div style="font-size: 0.875rem;">${location.hours}</div>
            </div>
        `;
    }

    updateBankingList(locations) {
        const listContainer = document.getElementById('banking-list');
        
        if (locations.length === 0) {
            listContainer.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: #64748b;">
                    <p>No banking services found in this area.</p>
                    <p style="font-size: 0.875rem; margin-top: 0.5rem;">Try increasing the search radius.</p>
                </div>
            `;
            return;
        }

        listContainer.innerHTML = locations.map(location => `
            <div class="banking-item" data-id="${location.id}">
                <div class="item-header">
                    <div>
                        <div class="item-name">${location.name}</div>
                        <div class="item-address">${location.address}</div>
                    </div>
                    <div style="text-align: right;">
                        <div class="item-type ${location.type}">${location.type}</div>
                        <div class="item-distance">${location.distance} km</div>
                    </div>
                </div>
                <div class="item-services">
                    ${location.services.map(service => `<span class="service-tag">${service}</span>`).join('')}
                </div>
                <div class="item-footer">
                    <span>${location.hours}</span>
                    <span>${location.phone}</span>
                </div>
            </div>
        `).join('');

        // Add click handlers
        listContainer.querySelectorAll('.banking-item').forEach(item => {
            item.addEventListener('click', () => {
                const locationId = parseInt(item.dataset.id);
                const location = locations.find(loc => loc.id === locationId);
                if (location) {
                    this.selectBankingLocation(location);
                }
            });
        });
    }

    selectBankingLocation(location) {
        // Center map on selected location
        this.map.setView([location.lat, location.lng], 16);
        
        // Find and open popup
        const marker = this.markers.find(m => 
            m.getLatLng().lat === location.lat && m.getLatLng().lng === location.lng
        );
        if (marker) {
            marker.openPopup();
        }

        // Highlight in list view
        document.querySelectorAll('.banking-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        const listItem = document.querySelector(`[data-id="${location.id}"]`);
        if (listItem) {
            listItem.classList.add('selected');
            listItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    updateLocationDetails(data) {
        const detailsContainer = document.getElementById('location-details');
        const address = data.address;
        
        detailsContainer.innerHTML = `
            <div class="detail-item">
                <span class="detail-label">Country</span>
                <span class="detail-value">${address.country}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">City</span>
                <span class="detail-value">${address.city}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Address</span>
                <span class="detail-value">${address.road || 'Not available'}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Coordinates</span>
                <span class="detail-value">${data.coordinates.lat.toFixed(4)}, ${data.coordinates.lng.toFixed(4)}</span>
            </div>
        `;
    }

    updateExchangeRates(rates, baseCurrency) {
        const ratesContainer = document.getElementById('exchange-rates');
        const ratesList = document.getElementById('rates-list');
        
        if (!rates || Object.keys(rates).length === 0) {
            ratesContainer.style.display = 'none';
            return;
        }

        ratesContainer.style.display = 'block';
        ratesList.innerHTML = Object.entries(rates).map(([currency, rate]) => `
            <div class="rate-item">
                <span class="rate-currency">1 ${baseCurrency} = ${currency}</span>
                <span class="rate-value">${rate}</span>
            </div>
        `).join('');
    }

    toggleView() {
        const mapContainer = document.getElementById('map-container');
        const listContainer = document.getElementById('list-container');
        const toggleBtn = document.getElementById('toggle-view');
        
        if (this.currentView === 'map') {
            mapContainer.style.display = 'none';
            listContainer.style.display = 'block';
            this.currentView = 'list';
            toggleBtn.title = 'Show Map View';
        } else {
            mapContainer.style.display = 'block';
            listContainer.style.display = 'none';
            this.currentView = 'map';
            toggleBtn.title = 'Show List View';
            
            // Refresh map size
            setTimeout(() => {
                this.map.invalidateSize();
            }, 100);
        }
    }

    async applyFilters() {
        if (!this.userLocation) {
            this.showError('Please enable location services first');
            return;
        }

        this.showLoading(true);
        
        try {
            await this.getNearbyBanking(this.userLocation.lat, this.userLocation.lng);
        } catch (error) {
            this.showError('Failed to apply filters');
        } finally {
            this.showLoading(false);
        }
    }

    centerMapOnUser() {
        if (!this.userLocation) {
            this.showError('Location not available');
            return;
        }

        this.map.setView([this.userLocation.lat, this.userLocation.lng], 14);
        
        if (this.userMarker) {
            this.userMarker.openPopup();
        }
    }

    handleMapClick(e) {
        // Optional: Allow manual location selection
        const { lat, lng } = e.latlng;
        console.log(`Map clicked at: ${lat}, ${lng}`);
    }

    toggleInfoPanel(show) {
        const panel = document.getElementById('info-panel');
        if (show) {
            panel.style.display = 'flex';
        } else {
            panel.style.display = 'none';
        }
    }

    promptManualLocation() {
        // Simple prompt for manual location entry
        const location = prompt('Enter a city name or address:');
        if (location) {
            this.geocodeLocation(location);
        }
    }

    async geocodeLocation(query) {
        this.showLoading(true);
        
        try {
            const response = await fetch(
                `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`,
                {
                    headers: {
                        'User-Agent': 'BankingLocator/1.0'
                    }
                }
            );
            
            const data = await response.json();
            
            if (data.length > 0) {
                const result = data[0];
                const lat = parseFloat(result.lat);
                const lng = parseFloat(result.lon);
                
                this.userLocation = { lat, lng };
                this.updateMapLocation(lat, lng);
                await this.getLocationInfo(lat, lng);
                
                this.updateLocationStatus('success', `Location set to: ${result.display_name}`);
            } else {
                this.showError('Location not found. Please try a different search term.');
            }
        } catch (error) {
            console.error('Geocoding error:', error);
            this.showError('Failed to find location');
        } finally {
            this.showLoading(false);
        }
    }

    updateLocationStatus(status, message) {
        const statusDot = document.getElementById('status-dot');
        const locationText = document.getElementById('location-text');
        const enableBtn = document.getElementById('enable-location');
        
        statusDot.className = `status-dot ${status}`;
        locationText.textContent = message;
        
        if (status === 'success') {
            enableBtn.style.display = 'none';
        } else if (status === 'error') {
            enableBtn.style.display = 'block';
        }
    }

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = show ? 'flex' : 'none';
        this.isLoading = show;
    }

    showModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.style.display = 'flex';
        
        // Close on backdrop click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hideModal(modalId);
            }
        });
    }

    hideModal(modalId) {
        const modal = document.getElementById(modalId);
        modal.style.display = 'none';
    }

    showError(message) {
        // Simple error notification
        const notification = document.createElement('div');
        notification.className = 'error-notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ef4444;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 0.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 10000;
            max-width: 300px;
            font-size: 0.875rem;
            animation: slideInRight 0.3s ease;
        `;
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 5000);
        
        // Click to dismiss
        notification.addEventListener('click', () => {
            document.body.removeChild(notification);
        });
    }

    // Utility methods
    formatDistance(distance) {
        if (distance < 1) {
            return `${Math.round(distance * 1000)}m`;
        }
        return `${distance}km`;
    }

    formatCurrency(amount, currency) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }

    // Export location data
    exportLocationData() {
        if (!this.nearbyLocations.length) {
            this.showError('No data to export');
            return;
        }

        const data = {
            userLocation: this.userLocation,
            nearbyBanking: this.nearbyLocations,
            exportDate: new Date().toISOString()
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'banking-locations.json';
        a.click();
        
        URL.revokeObjectURL(url);
    }
}

// Add custom styles for animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    @keyframes ping {
        0% {
            transform: scale(1);
            opacity: 1;
        }
        75%, 100% {
            transform: scale(2);
            opacity: 0;
        }
    }
    
    .banking-item.selected {
        background: #f1f5f9;
        border-left: 4px solid #2563eb;
    }
    
    .user-marker,
    .banking-marker {
        border: none !important;
        background: transparent !important;
    }
    
    .error-notification {
        cursor: pointer;
        transition: transform 0.2s ease;
    }
    
    .error-notification:hover {
        transform: translateY(-2px);
    }
`;
document.head.appendChild(style);

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const app = new BankingLocator();
    
    // Make app globally available for debugging
    window.bankingLocator = app;
    
    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden && app.map) {
            // Refresh map when page becomes visible
            setTimeout(() => {
                app.map.invalidateSize();
            }, 100);
        }
    });
    
    // Handle window resize
    window.addEventListener('resize', () => {
        if (app.map) {
            setTimeout(() => {
                app.map.invalidateSize();
            }, 100);
        }
    });
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + R to refresh location
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            app.getCurrentLocation();
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal[style*="flex"]');
            modals.forEach(modal => {
                modal.style.display = 'none';
            });
        }
        
        // Space to toggle view
        if (e.key === ' ' && e.target === document.body) {
            e.preventDefault();
            app.toggleView();
        }
    });
    
    // Add geolocation watchPosition for continuous tracking (optional)
    if (navigator.geolocation && 'watchPosition' in navigator.geolocation) {
        let watchId = null;
        
        const startWatching = () => {
            watchId = navigator.geolocation.watchPosition(
                (position) => {
                    const { latitude, longitude } = position.coords;
                    
                    // Only update if location changed significantly (>100m)
                    if (app.userLocation) {
                        const distance = app.calculateDistance(
                            app.userLocation.lat, app.userLocation.lng,
                            latitude, longitude
                        );
                        
                        if (distance < 0.1) return; // Less than 100m
                    }
                    
                    app.userLocation = { lat: latitude, lng: longitude };
                    app.updateMapLocation(latitude, longitude);
                },
                (error) => {
                    console.warn('Watch position error:', error);
                },
                {
                    enableHighAccuracy: false,
                    timeout: 30000,
                    maximumAge: 60000 // 1 minute
                }
            );
        };
        
        const stopWatching = () => {
            if (watchId) {
                navigator.geolocation.clearWatch(watchId);
                watchId = null;
            }
        };
        
        // Start watching when user enables location
        // Stop watching when page is hidden to save battery
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                stopWatching();
            } else if (app.userLocation) {
                startWatching();
            }
        });
    }
});