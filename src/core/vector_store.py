"""
Enhanced vector store with Pinecone integration and Gemini embeddings.
"""
import os
from typing import List, Dict, Optional, Tuple
import numpy as np
from pinecone import Pinecone, ServerlessSpec
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)


class GeminiEmbeddings:
    """Gemini embeddings wrapper compatible with LangChain interface."""
    
    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004"):
        """Initialize Gemini embeddings.
        
        text-embedding-004 is the best Gemini embedding model available on free tier.
        It produces 768-dimensional embeddings.
        """
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini embeddings")
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.dimension = 768  # text-embedding-004 dimension
        logger.info(f"Initialized Gemini embeddings with model: {model_name}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        embeddings = []
        # Process in batches of 100 (Gemini API limit)
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                # For batch processing, embed each text individually
                for text in batch:
                    result = genai.embed_content(
                        model=self.model_name,
                        content=text,
                        task_type="retrieval_document"
                    )
                    embedding = result['embedding']
                    # Validate embedding is not all zeros
                    if all(v == 0 for v in embedding):
                        logger.warning(f"Zero embedding for text: {text[:50]}...")
                    embeddings.append(embedding)
            except Exception as e:
                error_str = str(e)
                logger.error(f"Embedding batch failed: {e}")
                # If quota exceeded, raise immediately with clear message
                if "429" in error_str or "quota" in error_str.lower():
                    raise ValueError(
                        "⚠️ Gemini API quota exceeded! Please create a new API key at https://aistudio.google.com/apikey "
                        "(select 'Create API key in new project') and update GOOGLE_API_KEY in your .env file."
                    )
                # Return zero vectors for other failures
                embeddings.extend([[0.0] * self.dimension for _ in batch])
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        # Validate input
        if not text or not text.strip():
            logger.warning("Empty query text provided for embedding")
            return [0.0] * self.dimension
        
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=text.strip(),
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            error_str = str(e)
            logger.error(f"Query embedding failed: {e}")
            if "429" in error_str or "quota" in error_str.lower():
                raise ValueError(
                    "⚠️ Gemini API quota exceeded! Please create a new API key at https://aistudio.google.com/apikey"
                )
            return [0.0] * self.dimension


class EnhancedVectorStore:
    """Enhanced vector store with Pinecone and Gemini embeddings."""
    
    def __init__(self, api_key: str, environment: str, index_name: str, google_api_key: str = None):
        logger.info(f"Initializing Pinecone client...")
        self.pc = Pinecone(api_key=api_key)
        self.index_name = index_name
        logger.info(f"Pinecone client initialized, connecting to index: {index_name}")
        
        # Use Gemini embeddings
        google_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        self.embeddings = GeminiEmbeddings(api_key=google_key)
        self.embedding_dimension = 768  # Gemini text-embedding-004 dimension
        
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize Pinecone index."""
        try:
            # Check if index exists
            if self.index_name not in self.pc.list_indexes().names():
                # Create index with Gemini embedding dimension (768)
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.embedding_dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                logger.info(f"Created Pinecone index: {self.index_name} with dimension {self.embedding_dimension}")
            else:
                logger.info(f"Using existing Pinecone index: {self.index_name}")
            
            self.index = self.pc.Index(self.index_name)
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {e}")
            raise
    
    def add_documents(self, documents: List[Dict], video_id: str, metadata: Dict = None):
        """Add documents to vector store with metadata."""
        try:
            # Prepare documents for indexing
            texts = [doc['text'] for doc in documents]
            
            # Generate embeddings using Gemini
            embeddings = self.embeddings.embed_documents(texts)
            
            # Prepare vectors for upsert
            vectors = []
            for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
                meta = {
                    'video_id': video_id,
                    'chunk_id': f"{video_id}_{i}",
                    'chunk_type': doc.get('type', 'paragraph'),
                    'length': doc.get('length', 0),
                    'timestamp': doc.get('timestamp', ''),
                    'text': doc['text'],  # Store text in metadata for retrieval
                    **(metadata or {})
                }
                vectors.append({
                    'id': f"{video_id}_{i}",
                    'values': embedding,
                    'metadata': meta
                })
            
            # Upsert in batches of 100
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
            
            logger.info(f"Added {len(documents)} documents for video {video_id}")
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def similarity_search(self, query: str, top_k: int = 6, filter_dict: Dict = None) -> List[Dict]:
        """Perform similarity search with filtering using Gemini embeddings."""
        try:
            logger.info(f"Similarity search: query='{query[:50]}...', top_k={top_k}, filter={filter_dict}")
            
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            if not query_embedding or all(v == 0 for v in query_embedding):
                logger.warning(f"Zero embedding generated for query: {query}")
                return []
            
            # Build query parameters
            query_params = {
                'vector': query_embedding,
                'top_k': top_k,
                'include_metadata': True
            }
            
            if filter_dict:
                query_params['filter'] = filter_dict
            
            # Query Pinecone
            results = self.index.query(**query_params)
            
            logger.info(f"Pinecone returned {len(results.get('matches', []))} matches")
            
            # Format results
            formatted_results = []
            for match in results.get('matches', []):
                metadata = match.get('metadata', {})
                formatted_results.append({
                    'text': metadata.get('text', ''),
                    'metadata': metadata,
                    'score': float(match.get('score', 0))
                })
            
            logger.info(f"Returning {len(formatted_results)} formatted results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}", exc_info=True)
            return []
    
    def hybrid_search(self, query: str, top_k: int = 6, filter_dict: Dict = None) -> List[Dict]:
        """Perform hybrid search combining semantic and keyword search."""
        try:
            # Semantic search
            semantic_results = self.similarity_search(query, top_k, filter_dict)
            
            # Keyword search (simple implementation)
            keyword_results = self._keyword_search(query, top_k, filter_dict)
            
            # Combine and rerank results
            combined_results = self._combine_and_rerank(
                semantic_results, keyword_results, query
            )
            
            return combined_results[:top_k]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []
    
    def _keyword_search(self, query: str, top_k: int, filter_dict: Dict = None) -> List[Dict]:
        """Simple keyword search implementation."""
        try:
            # This is a simplified implementation
            # In production, you'd use Pinecone's metadata filtering
            query_terms = query.lower().split()
            
            # For now, return empty list - in production, implement proper keyword search
            return []
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def _combine_and_rerank(self, semantic_results: List[Dict], keyword_results: List[Dict], query: str) -> List[Dict]:
        """Combine and rerank search results."""
        # Simple combination - in production, use more sophisticated reranking
        all_results = semantic_results + keyword_results
        
        # Remove duplicates based on text content
        seen_texts = set()
        unique_results = []
        for result in all_results:
            if result['text'] not in seen_texts:
                seen_texts.add(result['text'])
                unique_results.append(result)
        
        # Sort by score
        unique_results.sort(key=lambda x: x['score'], reverse=True)
        
        return unique_results
    
    def delete_video(self, video_id: str):
        """Delete all documents for a specific video."""
        try:
            # Delete by metadata filter
            self.index.delete(filter={"video_id": video_id})
            logger.info(f"Deleted all documents for video {video_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete video documents: {e}")
            raise
    
    def get_video_stats(self, video_id: str) -> Dict:
        """Get statistics for a video."""
        try:
            # Get index stats with filter
            stats_response = self.index.describe_index_stats()
            
            # Query for video documents using a generic query
            results = self.similarity_search(
                query="summary of video content",  # Use a generic query instead of empty
                top_k=1000,  # Large number to get all
                filter_dict={"video_id": video_id}
            )
            
            total_chunks = len(results)
            if total_chunks > 0:
                chunk_lengths = [len(r['text']) for r in results]
                return {
                    'video_id': video_id,
                    'total_chunks': total_chunks,
                    'avg_chunk_length': sum(chunk_lengths) / total_chunks,
                    'total_text_length': sum(chunk_lengths)
                }
            else:
                return {
                    'video_id': video_id,
                    'total_chunks': 0,
                    'avg_chunk_length': 0.0,
                    'total_text_length': 0
                }
            
        except Exception as e:
            logger.error(f"Failed to get video stats: {e}", exc_info=True)
            return {'video_id': video_id, 'total_chunks': 0, 'error': str(e)}
