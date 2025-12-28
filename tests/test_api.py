"""
API tests for YouTube RAG System.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from src.api.main import app
from src.models import User, Video, Conversation


class TestAPI:
    """Test cases for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_components(self):
        """Mock RAG components."""
        with patch('src.api.main.document_processor') as mock_dp, \
             patch('src.api.main.vector_store') as mock_vs, \
             patch('src.api.main.retriever') as mock_ret, \
             patch('src.api.main.generator') as mock_gen:
            
            # Setup mock return values
            mock_dp.extract_transcript.return_value = {
                'original_text': 'Test transcript',
                'translated_text': 'Test transcript',
                'original_language': 'en',
                'target_language': 'en',
                'video_id': 'test_video'
            }
            
            mock_dp.semantic_split.return_value = [
                {'text': 'Test chunk 1', 'type': 'paragraph', 'length': 100},
                {'text': 'Test chunk 2', 'type': 'paragraph', 'length': 100}
            ]
            
            mock_vs.add_documents.return_value = None
            mock_vs.get_video_stats.return_value = {
                'total_chunks': 2,
                'avg_chunk_length': 100.0,
                'total_text_length': 200
            }
            
            mock_ret.retrieve_and_rank.return_value = [
                {
                    'text': 'Test retrieved text',
                    'metadata': {'video_id': 'test_video'},
                    'score': 0.9
                }
            ]
            
            mock_gen.generate_answer.return_value = {
                'answer': 'Test answer',
                'sources': [{'text': 'Test source', 'score': 0.9}],
                'confidence': 0.8
            }
            
            yield {
                'document_processor': mock_dp,
                'vector_store': mock_vs,
                'retriever': mock_ret,
                'generator': mock_gen
            }
    
    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "YouTube RAG System API" in response.json()["message"]
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "healthy" in response.json()["status"]
    
    def test_process_video_success(self, client, mock_components):
        """Test successful video processing."""
        request_data = {
            "video_id": "test_video",
            "language": "en",
            "force_reprocess": False
        }
        
        response = client.post("/process_video", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["video_id"] == "test_video"
        assert data["total_chunks"] == 2
        assert data["processing_status"] == "completed"
    
    def test_process_video_failure(self, client, mock_components):
        """Test video processing failure."""
        # Mock failure
        mock_components['document_processor'].extract_transcript.return_value = None
        
        request_data = {
            "video_id": "invalid_video",
            "language": "en",
            "force_reprocess": False
        }
        
        response = client.post("/process_video", json=request_data)
        assert response.status_code == 404
        assert "Could not extract transcript" in response.json()["detail"]
    
    def test_ask_question_success(self, client, mock_components):
        """Test successful question answering."""
        request_data = {
            "question": "What is this video about?",
            "video_id": "test_video",
            "include_sources": True
        }
        
        response = client.post("/ask_question", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "confidence" in data
        assert data["video_id"] == "test_video"
    
    def test_ask_question_no_results(self, client, mock_components):
        """Test question with no relevant results."""
        # Mock empty results
        mock_components['retriever'].retrieve_and_rank.return_value = []
        
        request_data = {
            "question": "Unrelated question",
            "video_id": "test_video",
            "include_sources": True
        }
        
        response = client.post("/ask_question", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "couldn't find relevant information" in data["answer"]
        assert data["sources"] == []
        assert data["confidence"] == 0.0
    
    def test_get_video_summary(self, client, mock_components):
        """Test video summary endpoint."""
        # Mock summary generation
        mock_components['generator'].generate_summary.return_value = {
            'summary': 'Test video summary',
            'video_id': 'test_video',
            'key_points': ['Point 1', 'Point 2']
        }
        
        response = client.get("/video/test_video/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        assert "key_points" in data
    
    def test_search_video(self, client, mock_components):
        """Test video search endpoint."""
        # Mock search results
        mock_components['vector_store'].similarity_search.return_value = [
            {
                'text': 'Search result 1',
                'metadata': {'video_id': 'test_video'},
                'score': 0.9
            }
        ]
        
        response = client.get("/video/test_video/search?query=test&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["query"] == "test"
        assert data["video_id"] == "test_video"
        assert len(data["results"]) == 1
    
    def test_delete_video(self, client, mock_components):
        """Test video deletion endpoint."""
        response = client.delete("/video/test_video")
        assert response.status_code == 200
        
        data = response.json()
        assert "deleted successfully" in data["message"]
    
    def test_evaluate_system(self, client, mock_components):
        """Test system evaluation endpoint."""
        # Mock RAGAS evaluator
        with patch('src.api.main.ragas_evaluator') as mock_ragas:
            mock_ragas.evaluate_rag_system.return_value = {
                'overall_score': 0.8,
                'metrics': {
                    'faithfulness': 0.9,
                    'answer_relevancy': 0.8,
                    'context_precision': 0.7,
                    'context_recall': 0.8
                }
            }
            
            mock_ragas.generate_evaluation_report.return_value = "Test report"
            
            request_data = {
                "questions": ["What is this about?"],
                "answers": ["Test answer"],
                "contexts": [["Test context"]],
                "ground_truths": ["Ground truth"]
            }
            
            response = client.post("/evaluate", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "evaluation_results" in data
            assert "report" in data
    
    def test_evaluate_system_no_ragas(self, client):
        """Test evaluation without RAGAS."""
        request_data = {
            "questions": ["What is this about?"],
            "answers": ["Test answer"],
            "contexts": [["Test context"]]
        }
        
        response = client.post("/evaluate", json=request_data)
        assert response.status_code == 503
        assert "RAGAS evaluator not available" in response.json()["detail"]
    
    def test_get_metrics(self, client, mock_components):
        """Test metrics endpoint."""
        # Mock LangSmith monitor
        with patch('src.api.main.langsmith_monitor') as mock_langsmith:
            mock_langsmith.get_project_metrics.return_value = {
                'total_runs': 100,
                'avg_retrieval_time': 0.5,
                'avg_generation_time': 1.0
            }
            
            response = client.get("/metrics")
            assert response.status_code == 200
            
            data = response.json()
            assert "total_runs" in data
            assert "avg_retrieval_time" in data
    
    def test_cors_headers(self, client):
        """Test CORS headers."""
        response = client.options("/")
        assert response.status_code == 200
    
    def test_invalid_video_id(self, client):
        """Test with invalid video ID format."""
        request_data = {
            "video_id": "invalid_id_format",
            "language": "en"
        }
        
        response = client.post("/process_video", json=request_data)
        # Should still process, but might fail at transcript extraction
        assert response.status_code in [200, 404, 500]
    
    def test_missing_required_fields(self, client):
        """Test with missing required fields."""
        request_data = {
            "video_id": "test_video"
            # Missing language field
        }
        
        response = client.post("/process_video", json=request_data)
        assert response.status_code == 200  # Should use default values
    
    def test_large_request(self, client, mock_components):
        """Test with large request data."""
        large_question = "What is this video about? " * 1000  # Very long question
        
        request_data = {
            "question": large_question,
            "video_id": "test_video",
            "include_sources": True
        }
        
        response = client.post("/ask_question", json=request_data)
        # Should handle large requests gracefully
        assert response.status_code in [200, 413, 422]
    
    def test_concurrent_requests(self, client, mock_components):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            request_data = {
                "question": "Test question",
                "video_id": "test_video",
                "include_sources": True
            }
            response = client.post("/ask_question", json=request_data)
            results.append(response.status_code)
        
        # Start multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5
