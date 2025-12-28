/**
 * Background service worker for YouTube RAG Assistant Chrome Extension
 * Handles communication between content script, popup, and backend API
 *
 * NOTE: This file is intended to be a drop-in replacement of your previous
 * background.js. It preserves all original message actions and endpoints,
 * while improving robustness (tab injection, timeouts, and race conditions).
 */

class RAGBackgroundService {
    constructor() {
        this.backendUrl = 'http://localhost:8000';
        this.isBackendConnected = false;
        this.injectedTabs = new Set(); // Track which tabs we've injected into
        this.setupEventListeners();

        // Kick off an initial backend check (don't await in constructor)
        this.checkBackendConnection();
    }

    setupEventListeners() {
        // Handle extension installation
        chrome.runtime.onInstalled.addListener((details) => {
            if (details.reason === 'install') {
                this.handleInstall();
            }
        });

        // Handle messages from content script and popup
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            // delegate to async handler; return true to keep message channel open
            try {
                this.handleMessage(request, sender, sendResponse);
            } catch (err) {
                console.error('Unhandled error in onMessage dispatcher:', err);
                sendResponse({ error: err.message });
            }
            return true; // keep the channel open for async responses
        });

        // Handle tab updates (YouTube navigation)
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            try {
                // guard: tab may be undefined in some chrome events
                if (changeInfo.status === 'complete' && tab && tab.url && this.isYouTubeVideoPage(tab.url)) {
                    // Prevent multiple injections per tab
                    if (!this.injectedTabs.has(tabId)) {
                        console.log(`Injecting content script into YouTube tab ${tabId}`);
                        this.handleYouTubePageLoad(tabId, tab);
                        this.injectedTabs.add(tabId);
                    }
                } else {
                    // If the tab navigated away from YouTube, remove from injected set (cleanup)
                    if (tab && tab.url && !this.isYouTubeVideoPage(tab.url) && this.injectedTabs.has(tabId)) {
                        this.injectedTabs.delete(tabId);
                        // console.log(`Tab ${tabId} navigated away from YouTube - cleaned injected flag`);
                    }
                }
            } catch (err) {
                console.error('onUpdated listener error:', err);
            }
        });

        // Clean up injectedTabs when tabs are closed (prevents stale tab ids)
        chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
            if (this.injectedTabs.has(tabId)) {
                this.injectedTabs.delete(tabId);
                console.log(`Tab ${tabId} closed — removed from injected set`);
            }
        });

        // Handle tab activation
        chrome.tabs.onActivated.addListener((activeInfo) => {
            this.handleTabActivation(activeInfo.tabId);
        });
    }

    async handleMessage(request, sender, sendResponse) {
        try {
            switch (request.action) {
                case 'checkBackendConnection':
                    {
                        const isConnected = await this.checkBackendConnection();
                        sendResponse({ connected: isConnected });
                    }
                    break;

                case 'processVideo':
                    {
                        const result = await this.processVideo(request.videoId, request.language);
                        sendResponse(result);
                    }
                    break;

                case 'askQuestion':
                    {
                        const answer = await this.askQuestion(request.question, request.videoId);
                        sendResponse(answer);
                    }
                    break;

                case 'getVideoInfo':
                    {
                        const videoInfo = await this.getVideoInfo(request.videoId);
                        sendResponse(videoInfo);
                    }
                    break;

                case 'togglePanel':
                    {
                        // sender.tab may be undefined (message from popup or devtools). handle both.
                        const senderTabId = sender && sender.tab && sender.tab.id;
                        if (senderTabId) {
                            this.toggleChatPanel(senderTabId);
                            sendResponse({ success: true });
                        } else {
                            // Fallback: find active tab in current window and toggle there
                            try {
                                chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                                    const activeTabId = tabs && tabs.length ? tabs[0].id : null;
                                    if (activeTabId) {
                                        this.toggleChatPanel(activeTabId);
                                        sendResponse({ success: true });
                                    } else {
                                        sendResponse({ success: false, error: 'No active tab found' });
                                    }
                                });
                                // We returned true from runtime.onMessage listener so async sendResponse is OK
                            } catch (err) {
                                console.error('togglePanel fallback failed:', err);
                                sendResponse({ success: false, error: err.message });
                            }
                        }
                    }
                    break;

                case 'getSettings':
                    {
                        const settings = await this.getSettings();
                        sendResponse(settings);
                    }
                    break;

                case 'updateSettings':
                    {
                        await this.updateSettings(request.settings);
                        sendResponse({ success: true });
                    }
                    break;

                case 'getConversationHistory':
                    {
                        const history = await this.getConversationHistory(request.videoId);
                        sendResponse(history);
                    }
                    break;

                case 'clearConversationHistory':
                    {
                        await this.clearConversationHistory(request.videoId);
                        sendResponse({ success: true });
                    }
                    break;

                default:
                    sendResponse({ error: 'Unknown action' });
            }
        } catch (error) {
            console.error('Background service error:', error);
            sendResponse({ error: error.message });
        }
    }

    // Use AbortController to implement a real timeout for fetch.
    // Returns parsed JSON or text.
    async makeRequest(url, options = {}, timeout = 10000) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(url, {
                signal: controller.signal,
                ...options
            });
            clearTimeout(id);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Parse JSON if possible, otherwise return text
            const text = await response.text();
            try {
                return JSON.parse(text);
            } catch {
                return text;
            }
        } catch (err) {
            clearTimeout(id);
            if (err.name === 'AbortError') {
                throw new Error('Request timed out');
            }
            throw err;
        }
    }

    async checkBackendConnection() {
        try {
            // Use makeRequest with a short timeout to check health
            await this.makeRequest(`${this.backendUrl}/health`, {}, 5000);
            this.isBackendConnected = true;
            console.log(`Backend status: ✅ Connected`);
            return this.isBackendConnected;
        } catch (err) {
            this.isBackendConnected = false;
            console.warn(`Backend status: ❌ Offline (${err.message})`);
            return false;
        }
    }

    async processVideo(videoId, language = 'en') {
        try {
            if (!this.isBackendConnected) {
                throw new Error('Backend not connected');
            }

            const result = await this.makeRequest(`${this.backendUrl}/process_video`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ video_id: videoId, language: language, force_reprocess: false })
            }, 120000); // allow longer timeout for processing

            return { success: true, data: result };
        } catch (error) {
            console.error('Video processing failed:', error);
            return { success: false, error: error.message };
        }
    }

    async askQuestion(question, videoId) {
        try {
            if (!this.isBackendConnected) {
                throw new Error('Backend not connected');
            }

            const result = await this.makeRequest(`${this.backendUrl}/ask_question`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: question, video_id: videoId, include_sources: true })
            }, 60000);

            return { success: true, data: result };
        } catch (error) {
            console.error('Question asking failed:', error);
            return { success: false, error: error.message };
        }
    }

    async getVideoInfo(videoId) {
        try {
            if (!this.isBackendConnected) {
                throw new Error('Backend not connected');
            }

            const result = await this.makeRequest(`${this.backendUrl}/video/${videoId}/summary`, {}, 10000);
            return { success: true, data: result };
        } catch (error) {
            console.error('Video info retrieval failed:', error);
            return { success: false, error: error.message };
        }
    }

    async toggleChatPanel(tabId) {
        try {
            // Ensure content script is injected first
            await this.ensureContentScriptInjected(tabId);
            
            chrome.tabs.sendMessage(tabId, { action: 'togglePanel' }, (resp) => {
                if (chrome.runtime.lastError) {
                    console.warn('⚠️ toggleChatPanel: content script not ready:', chrome.runtime.lastError.message);
                    // Try injecting content script and retry
                    this.handleYouTubePageLoad(tabId, null).then(() => {
                        setTimeout(() => {
                            chrome.tabs.sendMessage(tabId, { action: 'togglePanel' }, (retryResp) => {
                                if (chrome.runtime.lastError) {
                                    console.error('❌ Failed to toggle panel after retry:', chrome.runtime.lastError.message);
                                } else {
                                    console.log('✅ Panel toggled after retry');
                                }
                            });
                        }, 500);
                    });
                } else {
                    console.log('✅ togglePanel message sent successfully');
                }
            });
        } catch (error) {
            console.error('❌ Failed to toggle chat panel:', error);
        }
    }
    
    async ensureContentScriptInjected(tabId) {
        try {
            const results = await chrome.scripting.executeScript({
                target: { tabId },
                func: () => !!window.YouTubeRAGAssistantInitialized
            });
            
            if (!results[0]?.result) {
                console.log('📦 Content script not initialized, injecting...');
                await this.handleYouTubePageLoad(tabId, null);
            }
        } catch (error) {
            console.error('Error checking content script:', error);
        }
    }

    async getSettings() {
        try {
            return new Promise((resolve) => {
                chrome.storage.sync.get(
                    ['darkMode', 'autoProcess', 'showSources', 'backendUrl', 'language'],
                    (result) => {
                        const payload = {
                            success: true,
                            data: {
                                darkMode: result.darkMode || false,
                                autoProcess: result.autoProcess || false,
                                showSources: result.showSources !== false, // default true
                                backendUrl: result.backendUrl || 'http://localhost:8000',
                                language: result.language || 'en'
                            }
                        };
                        resolve(payload);
                    }
                );
            });
        } catch (error) {
            console.error('Failed to get settings:', error);
            return { success: false, error: error.message };
        }
    }

    async updateSettings(settings) {
        try {
            return new Promise((resolve) => {
                chrome.storage.sync.set(settings, async () => {
                    // Update local backendUrl if provided and re-check
                    if (settings.backendUrl) {
                        this.backendUrl = settings.backendUrl;
                        await this.checkBackendConnection();
                    }
                    resolve({ success: true });
                });
            });
        } catch (error) {
            console.error('Failed to update settings:', error);
            return { success: false, error: error.message };
        }
    }

    async getConversationHistory(videoId) {
        try {
            const key = `conversation_${videoId}`;
            return new Promise((resolve) => {
                chrome.storage.local.get([key], (result) => {
                    resolve({ success: true, data: result[key] || [] });
                });
            });
        } catch (error) {
            console.error('Failed to get conversation history:', error);
            return { success: false, error: error.message };
        }
    }

    async clearConversationHistory(videoId) {
        try {
            const key = `conversation_${videoId}`;
            return new Promise((resolve) => {
                chrome.storage.local.remove([key], () => {
                    resolve({ success: true });
                });
            });
        } catch (error) {
            console.error('Failed to clear conversation history:', error);
            return { success: false, error: error.message };
        }
    }

    isYouTubeVideoPage(url) {
        return url && url.includes('youtube.com/watch');
    }

    async handleInstall() {
        try {
            await new Promise((resolve) => {
                chrome.storage.sync.set({
                    darkMode: false,
                    autoProcess: false,
                    showSources: true,
                    backendUrl: 'http://localhost:8000',
                    language: 'en'
                }, resolve);
            });
            console.log('YouTube RAG Assistant installed');
        } catch (err) {
            console.error('handleInstall error:', err);
        }
    }

    async handleYouTubePageLoad(tabId, tab) {
        try {
            const results = await chrome.scripting.executeScript({
                target: { tabId },
                func: () => !!document.getElementById('rag-chat-panel')
            });
    
            const alreadyInjected = results[0]?.result;
    
            if (!alreadyInjected) {
                await chrome.scripting.executeScript({
                    target: { tabId },
                    files: ['content.js']
                });
    
                await chrome.scripting.insertCSS({
                    target: { tabId },
                    files: ['styles.css']
                });
    
                console.log(`✅ content.js injected into tab ${tabId}`);
            } else {
                console.log(`⏭️ content.js already active in tab ${tabId}`);
            }
        } catch (error) {
            console.error('Failed to inject content script:', error);
        }
    }
    

    async handleTabActivation(tabId) {
        try {
            const tab = await new Promise((resolve, reject) => {
                chrome.tabs.get(tabId, (t) => {
                    if (chrome.runtime.lastError) {
                        reject(new Error(chrome.runtime.lastError.message));
                    } else {
                        resolve(t);
                    }
                });
            });

            if (tab && this.isYouTubeVideoPage(tab.url)) {
                await this.checkBackendConnection();
                // send a message safely — include callback to surface lastError
                chrome.tabs.sendMessage(tabId, { action: 'tabActivated' }, () => {
                    if (chrome.runtime.lastError) {
                        console.warn('Content script not ready yet:', chrome.runtime.lastError.message);
                    } else {
                        console.log('Tab activated message sent successfully');
                    }
                });
            }
        } catch (error) {
            console.error('Failed to handle tab activation:', error);
        }
    }

    // Periodic backend health check
    startHealthCheck() {
        setInterval(async () => {
            await this.checkBackendConnection();
        }, 30000); // every 30 seconds
    }
}

// Initialize background service
const ragBackgroundService = new RAGBackgroundService();

// Start periodic health check
ragBackgroundService.startHealthCheck();
