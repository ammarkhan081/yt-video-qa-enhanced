"""
LangSmith monitoring and logging for RAG system.
"""
import os
from typing import Dict, List, Optional, Any
from langsmith import Client
from langsmith.evaluation import evaluate
from langsmith.schemas import Run, Example
import logging

logger = logging.getLogger(__name__)


class LangSmithMonitor:
    """LangSmith monitoring and logging for RAG system."""
    
    def __init__(self, api_key: str, project_name: str = "youtube-rag-system"):
        self.client = Client(api_key=api_key)
        self.project_name = project_name
        self._setup_project()
    
    def _setup_project(self):
        """Setup LangSmith project."""
        try:
            # Create or get project
            self.project = self.client.create_project(
                project_name=self.project_name,
                description="YouTube RAG System Monitoring"
            )
            logger.info(f"LangSmith project setup: {self.project_name}")
            
        except Exception as e:
            logger.error(f"LangSmith project setup failed: {e}")
            self.project = None
    
    def log_retrieval(self, 
                     query: str,
                     retrieved_docs: List[Dict],
                     video_id: str,
                     retrieval_time: float,
                     metadata: Dict = None) -> str:
        """Log retrieval operation."""
        try:
            run_data = {
                "name": "retrieval",
                "run_type": "retriever",
                "inputs": {
                    "query": query,
                    "video_id": video_id
                },
                "outputs": {
                    "retrieved_docs": retrieved_docs,
                    "num_docs": len(retrieved_docs)
                },
                "metadata": {
                    "video_id": video_id,
                    "retrieval_time": retrieval_time,
                    **(metadata or {})
                }
            }
            
            run = self.client.create_run(**run_data)
            logger.info(f"Retrieval logged: {run.id}")
            return run.id
            
        except Exception as e:
            logger.error(f"Retrieval logging failed: {e}")
            return None
    
    def log_generation(self,
                      question: str,
                      answer: str,
                      context: List[Dict],
                      video_id: str,
                      generation_time: float,
                      metadata: Dict = None) -> str:
        """Log generation operation."""
        try:
            run_data = {
                "name": "generation",
                "run_type": "llm",
                "inputs": {
                    "question": question,
                    "context": context
                },
                "outputs": {
                    "answer": answer
                },
                "metadata": {
                    "video_id": video_id,
                    "generation_time": generation_time,
                    "context_length": len(context),
                    **(metadata or {})
                }
            }
            
            run = self.client.create_run(**run_data)
            logger.info(f"Generation logged: {run.id}")
            return run.id
            
        except Exception as e:
            logger.error(f"Generation logging failed: {e}")
            return None
    
    def log_rag_pipeline(self,
                        question: str,
                        answer: str,
                        retrieved_docs: List[Dict],
                        video_id: str,
                        total_time: float,
                        metadata: Dict = None) -> str:
        """Log complete RAG pipeline."""
        try:
            run_data = {
                "name": "rag_pipeline",
                "run_type": "chain",
                "inputs": {
                    "question": question,
                    "video_id": video_id
                },
                "outputs": {
                    "answer": answer,
                    "retrieved_docs": retrieved_docs
                },
                "metadata": {
                    "video_id": video_id,
                    "total_time": total_time,
                    "num_retrieved_docs": len(retrieved_docs),
                    **(metadata or {})
                }
            }
            
            run = self.client.create_run(**run_data)
            logger.info(f"RAG pipeline logged: {run.id}")
            return run.id
            
        except Exception as e:
            logger.error(f"RAG pipeline logging failed: {e}")
            return None
    
    def create_evaluation_dataset(self, 
                                 questions: List[str],
                                 answers: List[str],
                                 contexts: List[List[Dict]],
                                 ground_truths: List[str] = None) -> str:
        """Create evaluation dataset."""
        try:
            # Prepare examples
            examples = []
            for i, (question, answer, context) in enumerate(zip(questions, answers, contexts)):
                example_data = {
                    "inputs": {
                        "question": question,
                        "context": context
                    },
                    "outputs": {
                        "answer": answer
                    }
                }
                
                if ground_truths and i < len(ground_truths):
                    example_data["outputs"]["ground_truth"] = ground_truths[i]
                
                examples.append(example_data)
            
            # Create dataset
            dataset = self.client.create_dataset(
                dataset_name=f"{self.project_name}-eval",
                description="YouTube RAG System Evaluation Dataset"
            )
            
            # Add examples
            for example_data in examples:
                self.client.create_example(
                    dataset_id=dataset.id,
                    inputs=example_data["inputs"],
                    outputs=example_data["outputs"]
                )
            
            logger.info(f"Evaluation dataset created: {dataset.id}")
            return dataset.id
            
        except Exception as e:
            logger.error(f"Evaluation dataset creation failed: {e}")
            return None
    
    def run_evaluation(self, 
                       dataset_id: str,
                       evaluator_config: Dict = None) -> str:
        """Run evaluation on dataset."""
        try:
            # Default evaluator configuration
            if not evaluator_config:
                evaluator_config = {
                    "evaluators": [
                        "qa_relevance",
                        "qa_correctness",
                        "qa_helpfulness"
                    ]
                }
            
            # Run evaluation
            evaluation = self.client.run_evaluation(
                dataset_id=dataset_id,
                evaluator_config=evaluator_config
            )
            
            logger.info(f"Evaluation started: {evaluation.id}")
            return evaluation.id
            
        except Exception as e:
            logger.error(f"Evaluation run failed: {e}")
            return None
    
    def get_evaluation_results(self, evaluation_id: str) -> Dict:
        """Get evaluation results."""
        try:
            results = self.client.read_evaluation(evaluation_id)
            return {
                "evaluation_id": evaluation_id,
                "status": results.status,
                "results": results.results,
                "summary": results.summary
            }
            
        except Exception as e:
            logger.error(f"Failed to get evaluation results: {e}")
            return {"error": str(e)}
    
    def get_project_metrics(self) -> Dict:
        """Get project metrics and statistics."""
        try:
            # Get runs for the project
            runs = self.client.list_runs(project_name=self.project_name)
            
            # Calculate metrics
            total_runs = len(list(runs))
            
            # Get recent runs
            recent_runs = self.client.list_runs(
                project_name=self.project_name,
                limit=100
            )
            
            # Calculate average times
            retrieval_times = []
            generation_times = []
            
            for run in recent_runs:
                metadata = run.metadata or {}
                if "retrieval_time" in metadata:
                    retrieval_times.append(metadata["retrieval_time"])
                if "generation_time" in metadata:
                    generation_times.append(metadata["generation_time"])
            
            metrics = {
                "total_runs": total_runs,
                "avg_retrieval_time": sum(retrieval_times) / len(retrieval_times) if retrieval_times else 0,
                "avg_generation_time": sum(generation_times) / len(generation_times) if generation_times else 0,
                "recent_runs": len(list(recent_runs))
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get project metrics: {e}")
            return {"error": str(e)}
    
    def create_alert(self, 
                    alert_name: str,
                    condition: str,
                    threshold: float,
                    notification_config: Dict = None) -> str:
        """Create monitoring alert."""
        try:
            # Create alert configuration
            alert_config = {
                "name": alert_name,
                "condition": condition,
                "threshold": threshold,
                "notification_config": notification_config or {}
            }
            
            # In a real implementation, you would create the alert
            # This is a placeholder for the alert creation logic
            logger.info(f"Alert created: {alert_name}")
            return f"alert_{alert_name}"
            
        except Exception as e:
            logger.error(f"Alert creation failed: {e}")
            return None
