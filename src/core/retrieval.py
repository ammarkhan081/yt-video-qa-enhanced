"""
Advanced retrieval with MMR and reranking.
"""
import re
from typing import List, Dict, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class AdvancedRetriever:
    """Advanced retrieval with query processing and reranking."""
    
    def __init__(self, vector_store, llm_model: str = "gemini-1.5-flash"):
        self.vector_store = vector_store
    
    def process_query(self, query: str, context: str = "") -> str:
        """Return the original query (simplified: no LLM rewriting)."""
        return query

    def generate_multi_queries(self, query: str) -> List[str]:
        """Simplified: just return the original query as a single candidate."""
        return [query]
    
    def retrieve_with_mmr(self, query: str, top_k: int = 20, diversity_threshold: float = 0.3) -> List[Dict]:
        """Retrieve documents using Maximal Marginal Relevance."""
        try:
            # Get more documents than needed for MMR
            initial_results = self.vector_store.similarity_search(
                query=query,
                top_k=top_k * 3
            )
            
            if not initial_results:
                return []
            
            # Apply MMR algorithm
            mmr_results = self._apply_mmr(
                query=query,
                documents=initial_results,
                top_k=top_k,
                diversity_threshold=diversity_threshold
            )
            
            return mmr_results
            
        except Exception as e:
            logger.error(f"MMR retrieval failed: {e}")
            return []
    
    def _apply_mmr(self, query: str, documents: List[Dict], top_k: int, diversity_threshold: float) -> List[Dict]:
        """Apply Maximal Marginal Relevance algorithm."""
        if not documents:
            return []
        
        # Calculate relevance scores
        relevance_scores = []
        for doc in documents:
            # Simple relevance score based on similarity
            relevance_scores.append(doc.get('score', 0))
        
        # Initialize MMR results
        mmr_results = []
        remaining_docs = documents.copy()
        remaining_scores = relevance_scores.copy()
        
        # Select first document (highest relevance)
        best_idx = np.argmax(remaining_scores)
        mmr_results.append(remaining_docs[best_idx])
        remaining_docs.pop(best_idx)
        remaining_scores.pop(best_idx)
        
        # Select remaining documents using MMR
        while len(mmr_results) < top_k and remaining_docs:
            mmr_scores = []
            
            for i, doc in enumerate(remaining_docs):
                # Calculate relevance score
                relevance = remaining_scores[i]
                
                # Calculate diversity score (max similarity to already selected docs)
                max_similarity = 0
                for selected_doc in mmr_results:
                    # Simple similarity based on text overlap
                    similarity = self._calculate_text_similarity(doc['text'], selected_doc['text'])
                    max_similarity = max(max_similarity, similarity)
                
                # MMR score = relevance - diversity_threshold * max_similarity
                mmr_score = relevance - diversity_threshold * max_similarity
                mmr_scores.append(mmr_score)
            
            # Select document with highest MMR score
            best_idx = np.argmax(mmr_scores)
            mmr_results.append(remaining_docs[best_idx])
            remaining_docs.pop(best_idx)
            remaining_scores.pop(best_idx)
        
        return mmr_results
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def rerank_documents(self, query: str, documents: List[Dict]) -> List[Dict]:
        """Rerank documents using keyword-based scoring."""
        try:
            if not documents:
                return []
            
            query_words = set(query.lower().split())
            
            # Calculate relevance scores based on keyword overlap
            reranked_docs = []
            for doc in documents:
                doc_text = doc['text'].lower()
                doc_words = set(doc_text.split())
                
                # Count keyword matches
                matches = len(query_words.intersection(doc_words))
                
                # Calculate score combining original score and keyword match
                original_score = doc.get('score', 0)
                keyword_score = matches / len(query_words) if query_words else 0
                
                # Combined score (70% original, 30% keyword)
                doc['rerank_score'] = 0.7 * original_score + 0.3 * keyword_score
                reranked_docs.append(doc)
            
            # Sort by rerank score
            reranked_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return documents
    
    def contextual_compression(self, query: str, documents: List[Dict], max_length: int = 2000) -> List[Dict]:
        """Compress documents to fit within token limits."""
        try:
            compressed_docs = []
            current_length = 0
            
            for doc in documents:
                doc_text = doc['text']
                
                # If adding this document would exceed limit, truncate it
                if current_length + len(doc_text) > max_length:
                    remaining_length = max_length - current_length
                    if remaining_length > 100:  # Only add if we have meaningful space
                        truncated_text = doc_text[:remaining_length] + "..."
                        compressed_docs.append({
                            **doc,
                            'text': truncated_text,
                            'compressed': True
                        })
                    break
                else:
                    compressed_docs.append(doc)
                    current_length += len(doc_text)
            
            return compressed_docs
            
        except Exception as e:
            logger.error(f"Contextual compression failed: {e}")
            return documents
    
    def retrieve_and_rank(self, query: str, video_id: str = None, top_k: int = 6) -> List[Dict]:
        """Complete retrieval pipeline with query processing and ranking."""
        try:
            # Step 1: Process query
            processed_query = self.process_query(query)
            
            # Step 2: Generate multi-queries
            multi_queries = self.generate_multi_queries(processed_query)
            
            # Step 3: Retrieve from all queries
            all_results = []
            for q in multi_queries:
                results = self.vector_store.similarity_search(
                    query=q,
                    top_k=top_k,
                    filter_dict={"video_id": video_id} if video_id else None
                )
                all_results.extend(results)
            
            # Step 4: Apply MMR
            mmr_results = self._apply_mmr(
                query=processed_query,
                documents=all_results,
                top_k=top_k * 2,
                diversity_threshold=0.3
            )
            
            # Step 5: Rerank with cross-encoder
            reranked_results = self.rerank_documents(processed_query, mmr_results)
            
            # Step 6: Contextual compression
            compressed_results = self.contextual_compression(
                query=processed_query,
                documents=reranked_results,
                max_length=2000
            )
            
            return compressed_results[:top_k]
            
        except Exception as e:
            logger.error(f"Retrieve and rank failed: {e}")
            return []
