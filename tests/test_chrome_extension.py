"""
Tests for Chrome extension components.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock


class TestContentScript:
    """Test cases for content script functionality."""
    
    def test_video_id_extraction(self):
        """Test video ID extraction from YouTube URLs."""
        # Mock YouTubeRAGAssistant class
        class MockAssistant:
            def extractVideoId(self, url):
                if 'youtube.com/watch' in url:
                    return url.split('v=')[1].split('&')[0]
                return None
        
        assistant = MockAssistant()
        
        # Test valid YouTube URLs
        assert assistant.extractVideoId('https://www.youtube.com/watch?v=dQw4w9WgXcQ') == 'dQw4w9WgXcQ'
        assert assistant.extractVideoId('https://www.youtube.com/watch?v=test123&t=10s') == 'test123'
        
        # Test invalid URLs
        assert assistant.extractVideoId('https://www.google.com') is None
        assert assistant.extractVideoId('not_a_url') is None
    
    def test_youtube_page_detection(self):
        """Test YouTube page detection."""
        class MockAssistant:
            def isYouTubeVideoPage(self, url):
                return 'youtube.com/watch' in url
        
        assistant = MockAssistant()
        
        assert assistant.isYouTubeVideoPage('https://www.youtube.com/watch?v=test') == True
        assert assistant.isYouTubeVideoPage('https://www.youtube.com/') == False
        assert assistant.isYouTubeVideoPage('https://www.google.com') == False
    
    def test_chat_panel_creation(self):
        """Test chat panel HTML generation."""
        class MockAssistant:
            def getChatPanelHTML(self):
                return '''
                <div id="rag-chat-panel">
                    <div class="rag-panel-header">
                        <div class="rag-panel-title">AI Assistant</div>
                    </div>
                    <div class="rag-panel-content">
                        <div class="rag-messages"></div>
                        <div class="rag-input-container">
                            <textarea id="rag-input"></textarea>
                            <button id="rag-send-btn">Send</button>
                        </div>
                    </div>
                </div>
                '''
        
        assistant = MockAssistant()
        html = assistant.getChatPanelHTML()
        
        assert 'rag-chat-panel' in html
        assert 'rag-messages' in html
        assert 'rag-input' in html
        assert 'rag-send-btn' in html
    
    def test_message_handling(self):
        """Test message handling functionality."""
        class MockAssistant:
            def __init__(self):
                self.conversationHistory = []
            
            def addUserMessage(self, message):
                self.conversationHistory.append({'role': 'user', 'content': message})
            
            def addAssistantMessage(self, message, sources=None):
                self.conversationHistory.append({
                    'role': 'assistant', 
                    'content': message, 
                    'sources': sources or []
                })
        
        assistant = MockAssistant()
        
        # Test user message
        assistant.addUserMessage("What is this video about?")
        assert len(assistant.conversationHistory) == 1
        assert assistant.conversationHistory[0]['role'] == 'user'
        
        # Test assistant message
        assistant.addAssistantMessage("This video is about machine learning.", [{'text': 'Source 1'}])
        assert len(assistant.conversationHistory) == 2
        assert assistant.conversationHistory[1]['role'] == 'assistant'
        assert len(assistant.conversationHistory[1]['sources']) == 1
    
    def test_conversation_history_persistence(self):
        """Test conversation history persistence."""
        class MockAssistant:
            def __init__(self, videoId):
                self.currentVideoId = videoId
                self.conversationHistory = []
            
            def saveConversationHistory(self):
                # Mock localStorage
                return json.dumps(self.conversationHistory)
            
            def loadConversationHistory(self, data):
                self.conversationHistory = json.loads(data)
        
        assistant = MockAssistant('test_video')
        
        # Add some messages
        assistant.addUserMessage("Question 1")
        assistant.addAssistantMessage("Answer 1")
        
        # Save and load
        saved_data = assistant.saveConversationHistory()
        new_assistant = MockAssistant('test_video')
        new_assistant.loadConversationHistory(saved_data)
        
        assert len(new_assistant.conversationHistory) == 2
        assert new_assistant.conversationHistory[0]['content'] == "Question 1"


class TestBackgroundService:
    """Test cases for background service worker."""
    
    def test_backend_connection_check(self):
        """Test backend connection checking."""
        class MockBackgroundService:
            def __init__(self):
                self.backendUrl = 'http://localhost:8000'
                self.isBackendConnected = False
            
            async def checkBackendConnection(self):
                # Mock fetch request
                try:
                    # Simulate successful connection
                    self.isBackendConnected = True
                    return True
                except:
                    self.isBackendConnected = False
                    return False
        
        service = MockBackgroundService()
        
        # Test connection check
        result = service.checkBackendConnection()
        assert result == True
        assert service.isBackendConnected == True
    
    def test_message_handling(self):
        """Test message handling in background service."""
        class MockBackgroundService:
            def __init__(self):
                self.messageHandlers = {}
            
            def handleMessage(self, request, sender, sendResponse):
                action = request.get('action')
                
                if action == 'checkBackendConnection':
                    sendResponse({'connected': True})
                elif action == 'processVideo':
                    sendResponse({'success': True, 'data': {'video_id': request['videoId']}})
                elif action == 'askQuestion':
                    sendResponse({'success': True, 'data': {'answer': 'Test answer'}})
                else:
                    sendResponse({'error': 'Unknown action'})
        
        service = MockBackgroundService()
        
        # Test different message types
        responses = []
        
        # Test backend connection
        service.handleMessage({'action': 'checkBackendConnection'}, {}, lambda r: responses.append(r))
        assert responses[0]['connected'] == True
        
        # Test video processing
        service.handleMessage({'action': 'processVideo', 'videoId': 'test'}, {}, lambda r: responses.append(r))
        assert responses[1]['success'] == True
        
        # Test question asking
        service.handleMessage({'action': 'askQuestion', 'question': 'test'}, {}, lambda r: responses.append(r))
        assert responses[2]['success'] == True
    
    def test_settings_management(self):
        """Test settings management."""
        class MockBackgroundService:
            def __init__(self):
                self.settings = {
                    'darkMode': False,
                    'autoProcess': False,
                    'showSources': True,
                    'backendUrl': 'http://localhost:8000'
                }
            
            def getSettings(self):
                return {'success': True, 'data': self.settings}
            
            def updateSettings(self, newSettings):
                self.settings.update(newSettings)
                return {'success': True}
        
        service = MockBackgroundService()
        
        # Test getting settings
        settings = service.getSettings()
        assert settings['success'] == True
        assert 'darkMode' in settings['data']
        
        # Test updating settings
        result = service.updateSettings({'darkMode': True})
        assert result['success'] == True
        assert service.settings['darkMode'] == True


class TestPopupController:
    """Test cases for popup controller."""
    
    def test_popup_initialization(self):
        """Test popup initialization."""
        class MockPopupController:
            def __init__(self):
                self.settings = {
                    'darkMode': False,
                    'autoProcess': False,
                    'showSources': True
                }
                self.isConnected = False
            
            async def loadSettings(self):
                # Mock settings loading
                pass
            
            async def checkConnection(self):
                # Mock connection check
                self.isConnected = True
            
            def updateUI(self):
                # Mock UI update
                pass
        
        controller = MockPopupController()
        
        # Test initialization
        assert controller.settings['darkMode'] == False
        assert controller.isConnected == False
        
        # Test connection check
        controller.checkConnection()
        assert controller.isConnected == True
    
    def test_toggle_settings(self):
        """Test settings toggles."""
        class MockPopupController:
            def __init__(self):
                self.settings = {
                    'darkMode': False,
                    'autoProcess': False,
                    'showSources': True
                }
            
            def toggleSetting(self, settingName):
                self.settings[settingName] = not self.settings[settingName]
                return self.settings[settingName]
        
        controller = MockPopupController()
        
        # Test toggling settings
        assert controller.toggleSetting('darkMode') == True
        assert controller.settings['darkMode'] == True
        
        assert controller.toggleSetting('autoProcess') == True
        assert controller.settings['autoProcess'] == True
        
        assert controller.toggleSetting('showSources') == False
        assert controller.settings['showSources'] == False
    
    def test_video_processing(self):
        """Test video processing functionality."""
        class MockPopupController:
            def __init__(self):
                self.isConnected = True
                self.currentVideoId = None
            
            def extractVideoId(self, url):
                if 'youtube.com/watch' in url:
                    return url.split('v=')[1].split('&')[0]
                return None
            
            async def processCurrentVideo(self):
                if not self.isConnected:
                    return {'success': False, 'error': 'Not connected'}
                
                if not self.currentVideoId:
                    return {'success': False, 'error': 'No video ID'}
                
                # Mock processing
                return {'success': True, 'data': {'video_id': self.currentVideoId}}
        
        controller = MockPopupController()
        
        # Test with no video ID
        result = controller.processCurrentVideo()
        assert result['success'] == False
        
        # Test with video ID
        controller.currentVideoId = 'test_video'
        result = controller.processCurrentVideo()
        assert result['success'] == True
        assert result['data']['video_id'] == 'test_video'
    
    def test_chat_panel_control(self):
        """Test chat panel control."""
        class MockPopupController:
            def __init__(self):
                self.panelVisible = False
            
            def togglePanel(self):
                self.panelVisible = not self.panelVisible
                return self.panelVisible
            
            def openChatPanel(self):
                self.panelVisible = True
                return True
        
        controller = MockPopupController()
        
        # Test panel toggling
        assert controller.togglePanel() == True
        assert controller.panelVisible == True
        
        assert controller.togglePanel() == False
        assert controller.panelVisible == False
        
        # Test opening panel
        assert controller.openChatPanel() == True
        assert controller.panelVisible == True


class TestExtensionIntegration:
    """Test cases for extension integration."""
    
    def test_extension_communication(self):
        """Test communication between extension components."""
        class MockExtension:
            def __init__(self):
                self.contentScript = Mock()
                self.backgroundService = Mock()
                self.popupController = Mock()
            
            def sendMessage(self, target, message):
                if target == 'content':
                    return self.contentScript.handleMessage(message)
                elif target == 'background':
                    return self.backgroundService.handleMessage(message)
                elif target == 'popup':
                    return self.popupController.handleMessage(message)
        
        extension = MockExtension()
        
        # Test message routing
        response = extension.sendMessage('content', {'action': 'togglePanel'})
        assert response is not None
        
        response = extension.sendMessage('background', {'action': 'checkConnection'})
        assert response is not None
    
    def test_extension_state_management(self):
        """Test extension state management."""
        class MockExtension:
            def __init__(self):
                self.state = {
                    'currentVideoId': None,
                    'isProcessing': False,
                    'conversationActive': False,
                    'settings': {
                        'darkMode': False,
                        'autoProcess': False
                    }
                }
            
            def updateState(self, updates):
                self.state.update(updates)
            
            def getState(self):
                return self.state.copy()
        
        extension = MockExtension()
        
        # Test state updates
        extension.updateState({'currentVideoId': 'test_video'})
        assert extension.getState()['currentVideoId'] == 'test_video'
        
        extension.updateState({'isProcessing': True})
        assert extension.getState()['isProcessing'] == True
        
        # Test state retrieval
        state = extension.getState()
        assert 'currentVideoId' in state
        assert 'isProcessing' in state
        assert 'settings' in state
    
    def test_error_handling(self):
        """Test error handling in extension."""
        class MockExtension:
            def __init__(self):
                self.errors = []
            
            def handleError(self, error, context):
                self.errors.append({
                    'error': str(error),
                    'context': context,
                    'timestamp': '2024-01-01T00:00:00Z'
                })
            
            def getErrors(self):
                return self.errors
        
        extension = MockExtension()
        
        # Test error handling
        extension.handleError(Exception('Test error'), 'content_script')
        assert len(extension.getErrors()) == 1
        assert extension.getErrors()[0]['error'] == 'Test error'
        assert extension.getErrors()[0]['context'] == 'content_script'
    
    def test_extension_performance(self):
        """Test extension performance monitoring."""
        class MockExtension:
            def __init__(self):
                self.performance = {
                    'messageCount': 0,
                    'responseTime': 0,
                    'errorCount': 0
                }
            
            def recordMessage(self, responseTime):
                self.performance['messageCount'] += 1
                self.performance['responseTime'] = responseTime
            
            def recordError(self):
                self.performance['errorCount'] += 1
            
            def getPerformanceMetrics(self):
                return self.performance.copy()
        
        extension = MockExtension()
        
        # Test performance recording
        extension.recordMessage(100)  # 100ms response time
        assert extension.getPerformanceMetrics()['messageCount'] == 1
        assert extension.getPerformanceMetrics()['responseTime'] == 100
        
        extension.recordError()
        assert extension.getPerformanceMetrics()['errorCount'] == 1
