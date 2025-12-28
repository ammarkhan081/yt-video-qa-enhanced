/**
 * Popup script for YouTube RAG Assistant Chrome Extension
 * Handles popup UI interactions and settings management
 */

class RAGPopupController {
    constructor() {
        this.settings = {
            darkMode: false,
            autoProcess: false,
            showSources: true,
            backendUrl: 'http://localhost:8000',
            language: 'en'
        };

        this.isConnected = false;
        this.currentVideoId = null;

        this.init();
    }

    async init() {
        await this.loadSettings();
        await this.checkConnection();
        this.setupEventListeners();
        this.updateUI();
    }

    async loadSettings() {
        try {
            const response = await chrome.runtime.sendMessage({ action: 'getSettings' });
            if (response.success) {
                this.settings = { ...this.settings, ...response.data };
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }

    async checkConnection() {
        try {
            const response = await chrome.runtime.sendMessage({ action: 'checkBackendConnection' });
            this.isConnected = response.connected;
        } catch (error) {
            console.error('Failed to check connection:', error);
            this.isConnected = false;
        }
    }

    setupEventListeners() {
        // Open chat panel button
        const openChatBtn = document.getElementById('open-chat');
        openChatBtn?.addEventListener('click', () => this.openChatPanel());

        // Process video button
        const processVideoBtn = document.getElementById('process-video');
        processVideoBtn?.addEventListener('click', () => this.processCurrentVideo());

        // Toggle panel button
        const togglePanelBtn = document.getElementById('toggle-panel');
        togglePanelBtn?.addEventListener('click', () => this.togglePanel());

        // Settings toggles
        const darkModeToggle = document.getElementById('dark-mode-toggle');
        darkModeToggle?.addEventListener('click', () => this.toggleSetting('darkMode'));

        const autoProcessToggle = document.getElementById('auto-process-toggle');
        autoProcessToggle?.addEventListener('click', () => this.toggleSetting('autoProcess'));

        const showSourcesToggle = document.getElementById('show-sources-toggle');
        showSourcesToggle?.addEventListener('click', () => this.toggleSetting('showSources'));

        // Settings dropdown
        const settingsIcon = document.getElementById('settings-icon');
        const settingsDropdown = document.getElementById('settings-dropdown');
        settingsIcon?.addEventListener('click', (e) => {
            e.stopPropagation();
            settingsDropdown?.classList.toggle('show');
        });

        // Close popup option
        const closePopupBtn = document.getElementById('close-popup');
        closePopupBtn?.addEventListener('click', () => window.close());

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!settingsIcon?.contains(e.target) && !settingsDropdown?.contains(e.target)) {
                settingsDropdown?.classList.remove('show');
            }
        });
    }

    updateUI() {
        this.updateConnectionStatus();
        this.updateToggleStates();
        this.updateButtonStates();
        this.applyDarkMode();
    }

    updateConnectionStatus() {
        const statusElement = document.getElementById('status');
        const statusText = document.getElementById('status-text');

        if (!statusElement || !statusText) return;

        if (this.isConnected) {
            statusElement.className = 'status connected';
            statusText.textContent = 'Connected';
        } else {
            statusElement.className = 'status disconnected';
            statusText.textContent = 'Disconnected';
        }
    }

    updateToggleStates() {
        // Dark mode toggle
        const darkModeToggle = document.getElementById('dark-mode-toggle');
        if (darkModeToggle) {
            darkModeToggle.classList.toggle('active', this.settings.darkMode);
        }

        // Auto process toggle
        const autoProcessToggle = document.getElementById('auto-process-toggle');
        if (autoProcessToggle) {
            autoProcessToggle.classList.toggle('active', this.settings.autoProcess);
        }

        // Show sources toggle
        const showSourcesToggle = document.getElementById('show-sources-toggle');
        if (showSourcesToggle) {
            showSourcesToggle.classList.toggle('active', this.settings.showSources);
        }
    }

    updateButtonStates() {
        const processVideoBtn = document.getElementById('process-video');
        const openChatBtn = document.getElementById('open-chat');

        if (processVideoBtn) {
            processVideoBtn.disabled = !this.isConnected;
            processVideoBtn.innerHTML = this.isConnected ? '<span>Analyze Video</span><span class="btn-icon">▶️</span>' : '<span>❌ Backend Disconnected</span>';
        }

        if (openChatBtn) {
            openChatBtn.disabled = !this.isConnected;
        }
    }

    async openChatPanel() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

            if (!this.isYouTubeVideoPage(tab.url)) {
                this.showNotification('Please navigate to a YouTube video first!', 'error');
                return;
            }

            // Send through background script for reliability
            const response = await chrome.runtime.sendMessage({ action: 'togglePanel' });
            if (response && response.success) {
                console.log('✅ Chat panel toggle message sent successfully');
            } else {
                console.warn('⚠️ Chat panel toggle response:', response);
            }
            window.close();
        } catch (error) {
            console.error('Failed to open chat panel:', error);
            this.showNotification('Failed to open chat panel. Make sure you are on a YouTube video page.', 'error');
        }
    }

    async processCurrentVideo() {
        if (!this.isConnected) {
            this.showNotification('Backend not connected!', 'error');
            return;
        }

        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

            if (!this.isYouTubeVideoPage(tab.url)) {
                this.showNotification('Please navigate to a YouTube video first!', 'error');
                return;
            }

            const videoId = this.extractVideoId(tab.url);
            if (!videoId) {
                this.showNotification('Could not extract video ID', 'error');
                return;
            }

            this.currentVideoId = videoId;
            this.updateProcessButton('Processing...', true);

            const response = await chrome.runtime.sendMessage({
                action: 'processVideo',
                videoId: videoId,
                language: this.settings.language
            });

            if (response.success) {
                this.showNotification('Video processed successfully!', 'success');
                this.updateProcessButton('✅ Processed', false);

                // Auto-open chat if enabled
                if (this.settings.autoProcess) {
                    setTimeout(() => this.openChatPanel(), 1000);
                }
            } else {
                throw new Error(response.error || 'Processing failed');
            }
        } catch (error) {
            console.error('Video processing failed:', error);
            this.showNotification(`Processing failed: ${error.message}`, 'error');
            this.updateProcessButton('<span>Analyze Video</span><span class="btn-icon">▶️</span>', false);
        }
    }

    async togglePanel() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

            if (!this.isYouTubeVideoPage(tab.url)) {
                this.showNotification('Please navigate to a YouTube video first!', 'error');
                return;
            }

            // Send through background script for reliability
            const response = await chrome.runtime.sendMessage({ action: 'togglePanel' });
            if (response && response.success) {
                console.log('✅ Panel toggle message sent successfully');
            }
            window.close();
        } catch (error) {
            console.error('Failed to toggle panel:', error);
            this.showNotification('Failed to toggle panel', 'error');
        }
    }

    async toggleSetting(settingName) {
        this.settings[settingName] = !this.settings[settingName];

        try {
            await chrome.runtime.sendMessage({
                action: 'updateSettings',
                settings: { [settingName]: this.settings[settingName] }
            });

            this.updateToggleStates();

            // Apply dark mode immediately
            if (settingName === 'darkMode') {
                this.applyDarkMode();
            }
        } catch (error) {
            console.error('Failed to update setting:', error);
            // Revert the change
            this.settings[settingName] = !this.settings[settingName];
        }
    }

    applyDarkMode() {
        const body = document.body;
        if (this.settings.darkMode) {
            body.classList.add('dark-mode');
        } else {
            body.classList.remove('dark-mode');
        }
    }

    async openSettings() {
        // Open settings page or show settings modal
        try {
            await chrome.tabs.create({
                url: chrome.runtime.getURL('settings.html')
            });
        } catch (error) {
            console.error('Failed to open settings:', error);
        }
    }

    updateProcessButton(text, disabled) {
        const processVideoBtn = document.getElementById('process-video');
        if (processVideoBtn) {
            processVideoBtn.innerHTML = text;
            processVideoBtn.disabled = disabled;
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Add to page
        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    isYouTubeVideoPage(url) {
        return url && url.includes('youtube.com/watch');
    }

    extractVideoId(url) {
        const urlParams = new URLSearchParams(new URL(url).search);
        return urlParams.get('v');
    }

    // Handle keyboard shortcuts
    handleKeyboardShortcuts(event) {
        if (event.ctrlKey || event.metaKey) {
            switch (event.key) {
                case 'Enter':
                    event.preventDefault();
                    this.processCurrentVideo();
                    break;
                case 'o':
                    event.preventDefault();
                    this.openChatPanel();
                    break;
            }
        }
    }
}

// Initialize popup controller when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new RAGPopupController();
});

// Add keyboard shortcut support
document.addEventListener('keydown', (event) => {
    const controller = window.ragPopupController;
    if (controller) {
        controller.handleKeyboardShortcuts(event);
    }
});
