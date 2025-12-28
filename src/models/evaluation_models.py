"""
Evaluation models for YouTube RAG System.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class EvaluationRun(Base):
    """Evaluation run model for tracking evaluation sessions."""
    
    __tablename__ = 'evaluation_runs'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Evaluation information
    run_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    evaluation_type = Column(String, nullable=False)  # ragas, langsmith, custom
    
    # Evaluation configuration
    config = Column(JSON, nullable=True)  # Evaluation configuration
    dataset_size = Column(Integer, default=0)
    test_questions = Column(JSON, nullable=True)  # Test questions used
    
    # Status and results
    status = Column(String, default='pending')  # pending, running, completed, failed
    overall_score = Column(Float, nullable=True)
    total_questions = Column(Integer, default=0)
    successful_evaluations = Column(Integer, default=0)
    failed_evaluations = Column(Integer, default=0)
    
    # Performance metrics
    total_time = Column(Float, nullable=True)  # Total evaluation time in seconds
    avg_processing_time = Column(Float, nullable=True)  # Average time per question
    
    # Relationships
    evaluation_metrics = relationship("EvaluationMetric", back_populates="evaluation_run", cascade="all, delete-orphan")
    evaluation_results = relationship("EvaluationResult", back_populates="evaluation_run", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<EvaluationRun(id={self.id}, name={self.run_name}, status={self.status})>"


class EvaluationMetric(Base):
    """Evaluation metric model for storing metric definitions and results."""
    
    __tablename__ = 'evaluation_metrics'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_run_id = Column(String, ForeignKey('evaluation_runs.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Metric information
    metric_name = Column(String, nullable=False)  # faithfulness, answer_relevancy, etc.
    metric_type = Column(String, nullable=False)  # retrieval, generation, overall
    description = Column(Text, nullable=True)
    
    # Metric results
    score = Column(Float, nullable=True)  # Overall score for this metric
    min_score = Column(Float, nullable=True)
    max_score = Column(Float, nullable=True)
    avg_score = Column(Float, nullable=True)
    std_deviation = Column(Float, nullable=True)
    
    # Metric configuration
    threshold = Column(Float, nullable=True)  # Pass/fail threshold
    weight = Column(Float, default=1.0)  # Weight in overall evaluation
    
    # Relationships
    evaluation_run = relationship("EvaluationRun", back_populates="evaluation_metrics")
    
    def __repr__(self):
        return f"<EvaluationMetric(id={self.id}, name={self.metric_name}, score={self.score})>"


class EvaluationResult(Base):
    """Evaluation result model for storing individual question evaluation results."""
    
    __tablename__ = 'evaluation_results'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_run_id = Column(String, ForeignKey('evaluation_runs.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Question and response information
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)  # Retrieved context
    ground_truth = Column(Text, nullable=True)  # Ground truth answer
    
    # Evaluation results
    overall_score = Column(Float, nullable=True)
    individual_scores = Column(JSON, nullable=True)  # Scores for each metric
    
    # Processing information
    processing_time = Column(Float, nullable=True)  # Time to process this question
    token_count = Column(Integer, nullable=True)  # Tokens used
    
    # Quality indicators
    is_grounded = Column(Boolean, nullable=True)  # Is answer grounded in context
    is_relevant = Column(Boolean, nullable=True)  # Is answer relevant to question
    is_helpful = Column(Boolean, nullable=True)  # Is answer helpful
    
    # Error information
    error_message = Column(Text, nullable=True)
    error_type = Column(String, nullable=True)
    
    # Relationships
    evaluation_run = relationship("EvaluationRun", back_populates="evaluation_results")
    
    def __repr__(self):
        return f"<EvaluationResult(id={self.id}, question={self.question[:50]}..., score={self.overall_score})>"
