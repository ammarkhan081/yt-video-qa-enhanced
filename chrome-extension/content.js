if (window.YouTubeRAGAssistantLoaded) {
    console.log("YouTubeRAGAssistant already loaded — using existing instance.");
} else {
    window.YouTubeRAGAssistantLoaded = true;
    console.log("🎬 Loading YouTubeRAGAssistant for the first time...");


    /**
     * Content script for YouTube RAG Assistant Chrome Extension
     * Injects chat panel into YouTube pages and handles communication
     */
    class YouTubeRAGAssistant {
        constructor() {
            this.isInitialized = false;
            this.chatPanel = null;
            this.currentVideoId = null;
            this.conversationHistory = [];
            this.backendUrl = 'http://localhost:8000';
            this.isProcessing = false;
            this.isDarkMode = false;

            this.init();
        }

        init() {
            // Wait for YouTube page to load
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.setup());
            } else {
                this.setup();
            }
        }

        setup() {
            console.log('🚀 YouTubeRAGAssistant setup called');

            // Create chat panel first (it will be visible on all YouTube pages)
            this.createChatPanel();

            // Check if we're on a YouTube video page
            if (!this.isYouTubeVideoPage()) {
                console.log('⚠️ Not a YouTube video page - panel created but waiting for video');
                // Still set up listeners for when user navigates to a video
                this.setupVideoChangeListener();
                this.setupMessageListener();
                this.isInitialized = true;
                return;
            }

            // Extract video ID
            this.currentVideoId = this.extractVideoId();
            if (!this.currentVideoId) {
                console.log('⚠️ Could not extract video ID');
                // Still create panel and set up listeners
                this.setupVideoChangeListener();
                this.setupMessageListener();
                this.isInitialized = true;
                return;
            }

            console.log('✅ Video ID:', this.currentVideoId);

            // Listen for video changes
            this.setupVideoChangeListener();

            // Listen for messages from popup
            this.setupMessageListener();

            this.isInitialized = true;
            console.log('✅ YouTube RAG Assistant initialized');

        }

        isYouTubeVideoPage() {
            const hostname = window.location.hostname;
            const pathname = window.location.pathname;
            const search = window.location.search;
            
            // Check for both www.youtube.com and youtube.com
            const isYouTube = hostname === 'www.youtube.com' || hostname === 'youtube.com';
            
            // Check if it's a watch page (either /watch in path OR v= parameter in URL)
            const isWatchPage = pathname.includes('/watch') || search.includes('v=');
            
            console.log('🔍 Page check:', { hostname, pathname, search, isYouTube, isWatchPage });
            
            return isYouTube && isWatchPage;
        }

        extractVideoId() {
            const urlParams = new URLSearchParams(window.location.search);
            return urlParams.get('v');
        }

        createChatPanel() {
            // Remove existing panel if any
            const existingPanel = document.getElementById('rag-chat-panel');
            if (existingPanel) {
                existingPanel.remove();
            }

            // Create panel container
            this.chatPanel = document.createElement('div');
            this.chatPanel.id = 'rag-chat-panel';
            this.chatPanel.innerHTML = this.getChatPanelHTML();

            // Show panel by default
            this.chatPanel.style.visibility = 'visible';
            this.chatPanel.style.opacity = '1';
            this.chatPanel.style.pointerEvents = 'auto';

            // Insert into body
            document.body.appendChild(this.chatPanel);
            console.log("✅ Chat panel inserted into page body");

            // Setup panel functionality
            this.setupChatPanelEvents();

            // Load and apply dark mode setting
            this.loadDarkModeSetting();

            // Load conversation history
            this.loadConversationHistory();
        }

        getChatPanelHTML() {
            return `
            <div class="rag-panel-header">
                <div class="rag-panel-title">ChatBot</div>
                <div class="rag-panel-controls">
                    <button id="rag-settings-btn" class="rag-btn" title="Settings">⚙️</button>
                </div>
            </div>
            
            <div class="rag-subtitle">Ask anything about this video</div>
            
            <div class="rag-messages" id="rag-messages">
                <!-- Messages will appear here -->
            </div>
            
            <div class="rag-input-container">
                <div class="rag-input-wrapper">
                    <textarea 
                        id="rag-input" 
                        placeholder="Send a message..."
                        rows="1"
                    ></textarea>
                    <button id="rag-send-btn" class="rag-btn-send" title="Send message">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
                        </svg>
                    </button>
                </div>
            </div>
            
            <div id="rag-settings-menu" class="rag-settings-menu" style="display: none;">
                <button id="rag-darkmode-toggle" class="rag-settings-item">Dark Mode</button>
                <button id="rag-new-chat" class="rag-settings-item">New Chat</button>
                <button id="rag-close-settings" class="rag-settings-item">Close Panel</button>
            </div>
            
            <div class="rag-status" id="rag-status" style="display: none;">
                <span class="rag-status-indicator rag-status-ready"></span>
                <span class="rag-status-text">Ready</span>
            </div>
        `;
        }

        setupChatPanelEvents() {
            // Settings button toggle
            const settingsBtn = document.getElementById('rag-settings-btn');
            const settingsMenu = document.getElementById('rag-settings-menu');

            settingsBtn?.addEventListener('click', (e) => {
                e.stopPropagation();
                const isVisible = settingsMenu.style.display === 'block';
                settingsMenu.style.display = isVisible ? 'none' : 'block';
            });

            // Close settings when clicking outside
            document.addEventListener('click', () => {
                if (settingsMenu) {
                    settingsMenu.style.display = 'none';
                }
            });

            // Settings menu items
            const closeSettingsBtn = document.getElementById('rag-close-settings');
            const newChatBtn = document.getElementById('rag-new-chat');
            const darkModeToggle = document.getElementById('rag-darkmode-toggle');

            closeSettingsBtn?.addEventListener('click', () => {
                this.chatPanel.remove();
                this.chatPanel = null;
                console.log('Chat panel closed.');
            });

            newChatBtn?.addEventListener('click', () => {
                this.refreshConversation();
                settingsMenu.style.display = 'none';
            });

            darkModeToggle?.addEventListener('click', () => {
                this.toggleDarkMode();
                settingsMenu.style.display = 'none';
            });

            // Suggestion buttons
            const suggestionBtns = document.querySelectorAll('.rag-suggestion-btn');
            suggestionBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    const question = btn.getAttribute('data-question');
                    const input = document.getElementById('rag-input');
                    if (input && question) {
                        input.value = question;
                        this.sendMessage();
                    }
                });
            });

            // Send message
            const sendBtn = document.getElementById('rag-send-btn');
            const input = document.getElementById('rag-input');

            // Auto-grow textarea
            if (input && input.tagName === 'TEXTAREA') {
                input.addEventListener('input', function () {
                    this.style.height = 'auto';
                    this.style.height = Math.min(this.scrollHeight, 100) + 'px';
                });
            }

            sendBtn?.addEventListener('click', () => this.sendMessage());
            input?.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        refreshConversation() {
            this.conversationHistory = [];
            const messagesContainer = document.getElementById('rag-messages');
            if (messagesContainer) {
                messagesContainer.innerHTML = '';
            }
            console.log('Conversation refreshed');
        }

        loadDarkModeSetting() {
            // Load dark mode setting from Chrome storage
            try {
                chrome.storage.sync.get(['darkMode'], (result) => {
                    this.isDarkMode = result.darkMode || false;
                    this.applyDarkMode();

                    // Update button text based on loaded setting
                    const darkModeToggle = document.getElementById('rag-darkmode-toggle');
                    if (darkModeToggle) {
                        darkModeToggle.textContent = this.isDarkMode ? 'Light Mode' : 'Dark Mode';
                    }
                });

                // Listen for storage changes
                chrome.storage.onChanged.addListener((changes, namespace) => {
                    if (namespace === 'sync' && changes.darkMode) {
                        this.isDarkMode = changes.darkMode.newValue || false;
                        this.applyDarkMode();
                    }
                });
            } catch (error) {
                console.log('Chrome storage not available, using light mode');
                this.isDarkMode = false;
            }
        }

        toggleDarkMode() {
            this.isDarkMode = !this.isDarkMode;
            this.applyDarkMode();

            // Update the button text
            const darkModeToggle = document.getElementById('rag-darkmode-toggle');
            if (darkModeToggle) {
                darkModeToggle.textContent = this.isDarkMode ? 'Light Mode' : 'Dark Mode';
            }

            // Save to Chrome storage
            try {
                chrome.storage.sync.set({ darkMode: this.isDarkMode });
                console.log(`Dark mode ${this.isDarkMode ? 'enabled' : 'disabled'}`);
            } catch (error) {
                console.log('Could not save dark mode setting');
            }
        }

        applyDarkMode() {
            const panel = document.getElementById('rag-chat-panel');
            const darkModeToggle = document.getElementById('rag-darkmode-toggle');

            if (!panel) return;

            // Update button text
            if (darkModeToggle) {
                darkModeToggle.textContent = this.isDarkMode ? 'Light Mode' : 'Dark Mode';
            }

            if (this.isDarkMode) {
                panel.classList.add('dark-mode');
            } else {
                panel.classList.remove('dark-mode');
            }
        }

        setupVideoChangeListener() {
            // Watch for URL changes on YouTube (SPA navigation)
            let lastUrl = window.location.href;

            const observer = new MutationObserver(() => {
                const currentUrl = window.location.href;
                if (currentUrl !== lastUrl) {
                    lastUrl = currentUrl;
                    this.handleVideoChange();
                }
            });

            observer.observe(document.body, {
                childList: true,
                subtree: true
            });

            // Also listen for popstate events
            window.addEventListener('popstate', () => this.handleVideoChange());
        }

        handleVideoChange() {
            console.log('🔄 Video change detected');
            
            if (!this.isYouTubeVideoPage()) {
                console.log('⚠️ Not on a video page after navigation');
                return;
            }

            const newVideoId = this.extractVideoId();
            if (newVideoId !== this.currentVideoId) {
                console.log('📹 New video detected:', newVideoId);
                this.currentVideoId = newVideoId;
                this.conversationHistory = [];
                this.updateChatPanel();
                
                // Ensure panel is visible
                const panel = document.getElementById('rag-chat-panel');
                if (panel) {
                    panel.style.visibility = 'visible';
                    panel.style.opacity = '1';
                    console.log('✅ Panel updated for new video');
                }
            }
        }

        updateChatPanel() {
            if (!this.chatPanel) return;

            const messagesContainer = document.getElementById('rag-messages');
            if (messagesContainer) {
                messagesContainer.innerHTML = '';
            }
        }

        setupMessageListener() {
            chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
                console.log('📬 Message received:', request.action);
                try {
                    switch (request.action) {
                        case 'togglePanel':
                            console.log('🔄 Toggling panel...');
                            this.togglePanel();
                            sendResponse({ success: true });
                            break;
                        case 'processVideo':
                            console.log('🎬 Processing video...');
                            this.processCurrentVideo();
                            sendResponse({ success: true });
                            break;
                        case 'getVideoId':
                            console.log('🎥 Getting video ID...');
                            sendResponse({ videoId: this.currentVideoId });
                            break;
                        case 'tabActivated':
                            console.log('👁️ Tab activated');
                            // Re-initialize if needed
                            if (!this.isInitialized) {
                                this.setup();
                            }
                            sendResponse({ success: true });
                            break;
                        default:
                            console.warn('⚠️ Unknown action:', request.action);
                            sendResponse({ success: false, error: 'Unknown action' });
                    }
                } catch (error) {
                    console.error('❌ Error handling message:', error);
                    sendResponse({ success: false, error: error.message });
                }
                return true; // Keep message channel open for async responses
            });
        }

        togglePanel() {
            try {
                // Ensure panel exists, create if needed
                if (!this.chatPanel || !document.getElementById('rag-chat-panel')) {
                    console.log('📦 Creating chat panel...');
                    this.createChatPanel();
                    // Show it immediately after creation
                    setTimeout(() => {
                        const panel = document.getElementById('rag-chat-panel');
                        if (panel) {
                            panel.style.visibility = 'visible';
                            panel.style.opacity = '1';
                            panel.style.pointerEvents = 'auto';
                            console.log('✅ Chat panel created and shown');

                            // Focus on input
                            const input = panel.querySelector('#rag-input');
                            if (input) {
                                input.focus();
                            }
                        }
                    }, 100);
                    return;
                }

                const panel = document.getElementById('rag-chat-panel');
                if (!panel) {
                    console.error('❌ Chat panel not found');
                    return;
                }

                const isHidden = panel.style.visibility === 'hidden' ||
                    panel.style.opacity === '0';

                if (isHidden) {
                    // Show panel
                    panel.style.visibility = 'visible';
                    panel.style.opacity = '1';
                    panel.style.pointerEvents = 'auto';

                    console.log('✅ Chat panel shown');

                    // Focus on input
                    setTimeout(() => {
                        const input = panel.querySelector('#rag-input');
                        if (input) {
                            input.focus();
                        }
                    }, 100);
                } else {
                    // Hide panel
                    panel.style.visibility = 'hidden';
                    panel.style.opacity = '0';
                    panel.style.pointerEvents = 'none';
                    console.log('🔁 Chat panel hidden');
                }
            } catch (error) {
                console.error('❌ Error in togglePanel:', error);
            }
        }


        async processCurrentVideo() {
            if (!this.currentVideoId || this.isProcessing) return;

            this.isProcessing = true;
            this.updateStatus('Processing video...', 'processing');

            try {
                const response = await fetch(this.backendUrl + '/process_video', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        video_id: this.currentVideoId,
                        language: 'en',
                        force_reprocess: false
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    this.updateStatus(`Video processed! ${result.total_chunks} chunks indexed.`, 'success');
                    this.addSystemMessage(`✅ Video processed successfully! I can now answer questions about this video.`);
                    // Auto-show chat panel after successful processing
                    setTimeout(() => {
                        this.togglePanel(); // Use togglePanel to ensure proper visibility
                        console.log('✅ Chat panel auto-opened after video processing');
                    }, 500);
                } else {
                    throw new Error('Failed to process video');
                }
            } catch (error) {
                console.error('Video processing failed:', error);
                this.updateStatus('Failed to process video', 'error');
                this.addSystemMessage(`❌ Failed to process video: ${error.message}`);
            } finally {
                this.isProcessing = false;
            }
        }

        async sendMessage() {
            const input = document.getElementById('rag-input');
            const sendBtn = document.getElementById('rag-send-btn');
            const message = input?.value.trim();

            console.log('📤 Sending message:', message);
            console.log('🎥 Current video ID:', this.currentVideoId);

            if (!message) {
                console.warn('⚠️ Empty message, ignoring');
                return;
            }
            
            if (this.isProcessing) {
                console.warn('⚠️ Already processing, ignoring');
                return;
            }

            if (!this.currentVideoId) {
                console.error('❌ No video ID available');
                this.addAssistantMessage('Please navigate to a YouTube video page first.', []);
                return;
            }

            this.isProcessing = true;

            // Disable input and button during processing
            if (input) input.disabled = true;
            if (sendBtn) {
                sendBtn.disabled = true;
                sendBtn.innerHTML = '<div class=\"rag-spinner\"></div>';
            }

            // Clear input
            input.value = '';

            // Reset textarea height
            if (input && input.tagName === 'TEXTAREA') {
                input.style.height = 'auto';
            }

            // Add user message to chat
            this.addUserMessage(message);

            // Update status
            this.updateStatus('Thinking...', 'processing');

            // Create streaming message placeholder with loading indicator
            const messageId = this.createStreamingMessage();

            try {
                console.log('🌐 Making API request to:', this.backendUrl + '/ask_question_stream');
                console.log('📦 Request payload:', {
                    question: message,
                    video_id: this.currentVideoId,
                    include_sources: true
                });
                
                const response = await fetch(this.backendUrl + '/ask_question_stream', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        question: message,
                        video_id: this.currentVideoId,
                        include_sources: true
                    })
                });
                
                console.log('📡 Response status:', response.status);
                console.log('📡 Response headers:', response.headers.get('content-type'));

                if (response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
                    // Handle streaming response
                    console.log('📡 Streaming response detected');
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let fullAnswer = '';
                    let sources = [];

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        const chunk = decoder.decode(value, { stream: true });
                        const lines = chunk.split('\n');  // Fixed: was \\n, should be \n
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    console.log('📨 Streaming data:', data);
                                    if (data.type === 'token') {
                                        fullAnswer += data.content;
                                        this.updateStreamingMessage(messageId, fullAnswer);
                                    } else if (data.type === 'sources') {
                                        sources = data.content;
                                    } else if (data.type === 'done') {
                                        this.finalizeStreamingMessage(messageId, fullAnswer, sources);
                                    } else if (data.type === 'error') {
                                        console.error('❌ Streaming error:', data.content);
                                        this.removeStreamingMessage(messageId);
                                        this.addAssistantMessage(`Error: ${data.content}`, []);
                                    }
                                } catch (e) {
                                    console.warn('⚠️ Failed to parse streaming data:', line, e);
                                }
                            }
                        }
                    }

                    this.updateStatus('Ready', 'ready');

                    // Save to conversation history
                    this.conversationHistory.push({
                        question: message,
                        answer: fullAnswer,
                        timestamp: new Date().toISOString()
                    });
                    this.saveConversationHistory();
                } else {
                    // Fallback to non-streaming response
                    console.log('📝 Non-streaming response detected');
                    const result = await response.json();
                    console.log('✅ Received answer:', result);
                    
                    if (result.error) {
                        this.removeStreamingMessage(messageId);
                        this.addAssistantMessage(`Error: ${result.error}`, []);
                    } else {
                        this.updateStreamingMessage(messageId, result.answer || 'No answer received');
                        this.finalizeStreamingMessage(messageId, result.answer || 'No answer received', result.sources || []);
                    }
                    this.updateStatus('Ready', 'ready');

                    // Save to conversation history
                    this.conversationHistory.push({
                        question: message,
                        answer: result.answer,
                        timestamp: new Date().toISOString()
                    });
                    this.saveConversationHistory();
                }
            } catch (error) {
                console.error('Question answering failed:', error);
                this.removeStreamingMessage(messageId);
                this.addAssistantMessage('Sorry, I encountered an error. Please try again.', []);
                this.updateStatus('Error occurred', 'error');
            } finally {
                this.isProcessing = false;
                // Re-enable input and button
                if (input) input.disabled = false;
                if (sendBtn) {
                    sendBtn.disabled = false;
                    sendBtn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>`;
                }
                // Focus back on input
                if (input) input.focus();
            }
        }

        createStreamingMessage() {
            const messagesContainer = document.getElementById('rag-messages');
            if (!messagesContainer) return null;

            const messageId = 'streaming-' + Date.now();
            const messageElement = document.createElement('div');
            messageElement.id = messageId;
            messageElement.className = 'rag-message rag-message-assistant';
            messageElement.innerHTML = `
                <div class="rag-message-content rag-streaming">
                    <div class="rag-typing-indicator">
                        <div class="rag-typing-dots">
                            <div class="rag-typing-dot"></div>
                            <div class="rag-typing-dot"></div>
                            <div class="rag-typing-dot"></div>
                        </div>
                    </div>
                </div>
            `;

            messagesContainer.appendChild(messageElement);
            this.scrollToBottom();
            return messageId;
        }

        updateStreamingMessage(messageId, text) {
            const messageElement = document.getElementById(messageId);
            if (!messageElement) return;

            const content = messageElement.querySelector('.rag-message-content');
            if (content) {
                // Format text with proper line breaks and preserve formatting
                const formattedText = this.formatMessageText(text);
                content.innerHTML = `<p class="rag-streaming-text">${formattedText}<span class="rag-cursor"></span></p>`;
                content.classList.add('rag-streaming');
            }
            this.scrollToBottom();
        }

        finalizeStreamingMessage(messageId, text, sources) {
            const messageElement = document.getElementById(messageId);
            if (!messageElement) return;

            const formattedText = this.formatMessageText(text);

            let sourcesHtml = '';
            if (sources && sources.length > 0) {
                sourcesHtml = `
                    <div class="rag-sources">
                        <div class="rag-sources-header">📚 Sources</div>
                        ${sources.map((source, index) => `
                            <div class="rag-source">
                                <span class="rag-source-id">${index + 1}</span>
                                <span class="rag-source-text">${this.escapeHtml(source.text || '')}</span>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            const content = messageElement.querySelector('.rag-message-content');
            if (content) {
                content.classList.remove('rag-streaming');
                content.innerHTML = `
                    <p>${formattedText}</p>
                    ${sourcesHtml}
                `;
            }
            this.scrollToBottom();
        }

        formatMessageText(text) {
            // Escape HTML and convert newlines to <br>
            const escaped = this.escapeHtml(text);
            return escaped.replace(/\\n/g, '<br>');
        }

        removeStreamingMessage(messageId) {
            const messageElement = document.getElementById(messageId);
            if (messageElement) {
                messageElement.remove();
            }
        }

        addUserMessage(message) {
            const messagesContainer = document.getElementById('rag-messages');
            if (!messagesContainer) return;

            const messageElement = document.createElement('div');
            messageElement.className = 'rag-message rag-message-user';
            messageElement.innerHTML = `<div class="rag-message-content">${this.escapeHtml(message)}</div>`;

            messagesContainer.appendChild(messageElement);
            this.scrollToBottom();
        }

        addAssistantMessage(message, sources = []) {
            const messagesContainer = document.getElementById('rag-messages');
            if (!messagesContainer) return;

            const messageElement = document.createElement('div');
            messageElement.className = 'rag-message rag-message-assistant';

            let sourcesHtml = '';
            if (sources && sources.length > 0) {
                sourcesHtml = `
                <div class="rag-sources">
                    <div class="rag-sources-header">Sources:</div>
                    ${sources.map((source, index) => `
                        <div class="rag-source">
                            <span class="rag-source-id">${index + 1}</span>
                            <span class="rag-source-text">${this.escapeHtml(source.text)}</span>
                        </div>
                    `).join('')}
                </div>
            `;
            }

            messageElement.innerHTML = `
            <div class="rag-message-content">
                <p>${this.escapeHtml(message)}</p>
                ${sourcesHtml}
            </div>
        `;

            messagesContainer.appendChild(messageElement);
            this.scrollToBottom();
        }

        addSystemMessage(message) {
            const messagesContainer = document.getElementById('rag-messages');
            if (!messagesContainer) return;

            const messageElement = document.createElement('div');
            messageElement.className = 'rag-message rag-message-system';
            messageElement.innerHTML = `
            <div class="rag-message-content">
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;

            messagesContainer.appendChild(messageElement);
            this.scrollToBottom();
        }

        updateStatus(message, type = 'ready') {
            const statusElement = document.getElementById('rag-status');
            if (!statusElement) return;

            const indicator = statusElement.querySelector('.rag-status-indicator');
            const text = statusElement.querySelector('span');

            if (indicator) {
                indicator.className = `rag-status-indicator rag-status-${type}`;
            }
            if (text) {
                text.textContent = message;
            }
        }

        scrollToBottom() {
            const messagesContainer = document.getElementById('rag-messages');
            if (messagesContainer) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }

        loadConversationHistory() {
            // Load from localStorage
            const saved = localStorage.getItem(`rag_conversation_${this.currentVideoId}`);
            if (saved) {
                try {
                    this.conversationHistory = JSON.parse(saved);
                    // Restore messages to UI
                    this.conversationHistory.forEach(conv => {
                        this.addUserMessage(conv.question);
                        this.addAssistantMessage(conv.answer);
                    });
                } catch (error) {
                    console.error('Failed to load conversation history:', error);
                }
            }
        }

        saveConversationHistory() {
            try {
                localStorage.setItem(
                    `rag_conversation_${this.currentVideoId}`,
                    JSON.stringify(this.conversationHistory)
                );
            } catch (error) {
                console.error('Failed to save conversation history:', error);
            }
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // Initialize the assistant
    new YouTubeRAGAssistant();
}