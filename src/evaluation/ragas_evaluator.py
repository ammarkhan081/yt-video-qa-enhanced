"""
RAGAS evaluation for RAG system quality assessment.
"""
from typing import List, Dict, Optional
import pandas as pd
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_correctness,
    answer_similarity
)
from datasets import Dataset
import logging

logger = logging.getLogger(__name__)


class RAGASEvaluator:
    """RAGAS evaluation for RAG system quality assessment."""
    
    def __init__(self):
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
            answer_similarity
        ]
    
    def evaluate_rag_system(self, 
                          questions: List[str],
                          answers: List[str],
                          contexts: List[List[str]],
                          ground_truths: List[str] = None) -> Dict:
        """Evaluate RAG system using RAGAS metrics."""
        try:
            # Prepare dataset
            dataset = self._prepare_dataset(
                questions, answers, contexts, ground_truths
            )
            
            # Run evaluation
            result = evaluate(
                dataset=dataset,
                metrics=self.metrics
            )
            
            # Format results
            evaluation_results = {
                'overall_score': result['ragas_score'],
                'metrics': {
                    'faithfulness': result['faithfulness'],
                    'answer_relevancy': result['answer_relevancy'],
                    'context_precision': result['context_precision'],
                    'context_recall': result['context_recall'],
                    'answer_correctness': result.get('answer_correctness', 0.0),
                    'answer_similarity': result.get('answer_similarity', 0.0)
                },
                'detailed_results': result
            }
            
            logger.info(f"RAGAS evaluation completed. Overall score: {result['ragas_score']}")
            return evaluation_results
            
        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            return {
                'error': str(e),
                'overall_score': 0.0,
                'metrics': {}
            }
    
    def _prepare_dataset(self, 
                        questions: List[str],
                        answers: List[str],
                        contexts: List[List[str]],
                        ground_truths: List[str] = None) -> Dataset:
        """Prepare dataset for RAGAS evaluation."""
        try:
            # Prepare data
            data = {
                'question': questions,
                'answer': answers,
                'contexts': contexts
            }
            
            if ground_truths:
                data['ground_truth'] = ground_truths
            
            # Create dataset
            dataset = Dataset.from_dict(data)
            return dataset
            
        except Exception as e:
            logger.error(f"Dataset preparation failed: {e}")
            raise
    
    def evaluate_single_qa(self, 
                          question: str,
                          answer: str,
                          context: List[str],
                          ground_truth: str = None) -> Dict:
        """Evaluate a single Q&A pair."""
        try:
            # Prepare single example
            dataset = self._prepare_dataset(
                [question], [answer], [context], [ground_truth] if ground_truth else None
            )
            
            # Run evaluation
            result = evaluate(
                dataset=dataset,
                metrics=self.metrics
            )
            
            return {
                'question': question,
                'answer': answer,
                'context': context,
                'ground_truth': ground_truth,
                'scores': {
                    'faithfulness': result['faithfulness'][0],
                    'answer_relevancy': result['answer_relevancy'][0],
                    'context_precision': result['context_precision'][0],
                    'context_recall': result['context_recall'][0],
                    'answer_correctness': result.get('answer_correctness', [0.0])[0],
                    'answer_similarity': result.get('answer_similarity', [0.0])[0]
                },
                'overall_score': result['ragas_score'][0]
            }
            
        except Exception as e:
            logger.error(f"Single QA evaluation failed: {e}")
            return {
                'question': question,
                'answer': answer,
                'error': str(e),
                'scores': {}
            }
    
    def batch_evaluate(self, qa_pairs: List[Dict]) -> Dict:
        """Evaluate multiple Q&A pairs in batch."""
        try:
            questions = [pair['question'] for pair in qa_pairs]
            answers = [pair['answer'] for pair in qa_pairs]
            contexts = [pair['context'] for pair in qa_pairs]
            ground_truths = [pair.get('ground_truth') for pair in qa_pairs]
            
            # Remove None ground truths
            ground_truths = [gt for gt in ground_truths if gt is not None]
            
            return self.evaluate_rag_system(
                questions, answers, contexts, ground_truths
            )
            
        except Exception as e:
            logger.error(f"Batch evaluation failed: {e}")
            return {'error': str(e)}
    
    def generate_evaluation_report(self, evaluation_results: Dict) -> str:
        """Generate a human-readable evaluation report."""
        try:
            report = []
            report.append("=== RAGAS Evaluation Report ===")
            report.append("")
            
            # Overall score
            overall_score = evaluation_results.get('overall_score', 0.0)
            report.append(f"Overall RAGAS Score: {overall_score:.3f}")
            report.append("")
            
            # Individual metrics
            metrics = evaluation_results.get('metrics', {})
            report.append("Individual Metrics:")
            report.append("-" * 30)
            
            for metric_name, score in metrics.items():
                report.append(f"{metric_name.replace('_', ' ').title()}: {score:.3f}")
            
            report.append("")
            
            # Interpretation
            report.append("Interpretation:")
            report.append("-" * 30)
            
            if overall_score >= 0.8:
                report.append("✅ Excellent: High-quality RAG system")
            elif overall_score >= 0.6:
                report.append("✅ Good: Decent RAG system with room for improvement")
            elif overall_score >= 0.4:
                report.append("⚠️ Fair: RAG system needs significant improvement")
            else:
                report.append("❌ Poor: RAG system requires major improvements")
            
            report.append("")
            
            # Recommendations
            report.append("Recommendations:")
            report.append("-" * 30)
            
            if metrics.get('faithfulness', 0) < 0.7:
                report.append("• Improve answer grounding and fact-checking")
            
            if metrics.get('answer_relevancy', 0) < 0.7:
                report.append("• Enhance query understanding and answer relevance")
            
            if metrics.get('context_precision', 0) < 0.7:
                report.append("• Improve retrieval precision and context filtering")
            
            if metrics.get('context_recall', 0) < 0.7:
                report.append("• Enhance retrieval recall and context coverage")
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return f"Error generating report: {e}"
