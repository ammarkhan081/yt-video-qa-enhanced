"""
Tests for core RAG components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from src.core.document_processor import MultilingualDocumentProcessor
from src.core.retrieval import AdvancedRetriever


class TestDocumentProcessor:
    """Test cases for document processor."""
    
    @pytest.fixture
    def processor(self):
        """Create document processor instance."""
        with patch('src.core.document_processor.genai') as mock_genai:
            return MultilingualDocumentProcessor()
    
    def test_clean_transcript(self, processor):
        """Test transcript cleaning."""
        transcript_data = [
            {'text': 'Hello world [Speaker 1]', 'start': 0, 'duration': 2},
            {'text': 'This is a test', 'start': 2, 'duration': 2},
            {'text': 'Subscribe to our channel', 'start': 4, 'duration': 2}
        ]
        
        cleaned = processor._clean_transcript(transcript_data)
        
        assert 'Hello world' in cleaned
        assert 'This is a test' in cleaned
    
    def test_semantic_split(self, processor):
        """Test semantic text splitting."""
        text = "This is a test paragraph. It contains multiple sentences. Each sentence should be preserved."
        
        chunks = processor.semantic_split(text, chunk_size=50, overlap=10)
        
        assert len(chunks) > 0
        assert all('text' in chunk for chunk in chunks)
        assert all('type' in chunk for chunk in chunks)


class TestRetriever:
    """Test cases for retriever."""
    
    @pytest.fixture
    def retriever(self):
        """Create retriever instance."""
        mock_vector_store = Mock()
        mock_vector_store.similarity_search.return_value = []
        return AdvancedRetriever(mock_vector_store, "gemini-1.5-flash")
    
    def test_process_query(self, retriever):
        """Test query processing."""
        result = retriever.process_query("Original query", "Context")
        assert result == "Original query"
    
    def test_generate_multi_queries(self, retriever):
        """Test multi-query generation."""
        queries = retriever.generate_multi_queries("Original query")
        assert len(queries) == 1
        assert queries[0] == "Original query"
    
    def test_rerank_documents(self, retriever):
        """Test document reranking with keyword-based scoring."""
        documents = [
            {'text': 'Document about test query topic', 'score': 0.8},
            {'text': 'Document with different content', 'score': 0.9}
        ]
        
        results = retriever.rerank_documents("test query", documents)
        
        assert len(results) == 2
        assert all('rerank_score' in doc for doc in results)
    
    def test_calculate_text_similarity(self, retriever):
        """Test text similarity calculation."""
        similarity = retriever._calculate_text_similarity(
            "hello world test",
            "hello world example"
        )
        
        assert 0.0 <= similarity <= 1.0
        assert similarity > 0
