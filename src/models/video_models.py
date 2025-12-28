"""
Video and metadata models for YouTube RAG System.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class Video(Base):
    """Video model for storing YouTube video information."""
    
    __tablename__ = 'videos'
    
    id = Column(String, primary_key=True)  # YouTube video ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Video information
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    channel_name = Column(String, nullable=True)
    channel_id = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    view_count = Column(Integer, nullable=True)
    like_count = Column(Integer, nullable=True)
    published_at = Column(DateTime, nullable=True)
    
    # Processing status
    is_processed = Column(Boolean, default=False)
    processing_status = Column(String, default='pending')  # pending, processing, completed, failed
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)
    
    # Language information
    original_language = Column(String, default='en')
    target_language = Column(String, default='en')
    is_translated = Column(Boolean, default=False)
    
    # Statistics
    total_chunks = Column(Integer, default=0)
    total_text_length = Column(Integer, default=0)
    avg_chunk_length = Column(Float, default=0.0)
    
    # Relationships
    video_metadata = relationship("VideoMetadata", back_populates="video", cascade="all, delete-orphan")
    processing_logs = relationship("VideoProcessing", back_populates="video", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="video", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Video(id={self.id}, title={self.title}, processed={self.is_processed})>"


class VideoMetadata(Base):
    """Video metadata model for storing additional video information."""
    
    __tablename__ = 'video_metadata'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String, ForeignKey('videos.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata fields
    category = Column(String, nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags
    thumbnail_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    
    # Transcript information
    transcript_available = Column(Boolean, default=False)
    transcript_language = Column(String, nullable=True)
    transcript_confidence = Column(Float, nullable=True)
    
    # Content analysis
    content_type = Column(String, nullable=True)  # educational, entertainment, news, etc.
    difficulty_level = Column(String, nullable=True)  # beginner, intermediate, advanced
    topics = Column(JSON, nullable=True)  # Extracted topics
    
    # Quality metrics
    audio_quality = Column(String, nullable=True)
    video_quality = Column(String, nullable=True)
    speech_clarity = Column(Float, nullable=True)
    
    # Relationships
    video = relationship("Video", back_populates="video_metadata")
    
    def __repr__(self):
        return f"<VideoMetadata(id={self.id}, video_id={self.video_id})>"


class VideoProcessing(Base):
    """Video processing log model for tracking processing steps."""
    
    __tablename__ = 'video_processing'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(String, ForeignKey('videos.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Processing information
    step_name = Column(String, nullable=False)  # transcript_extraction, translation, chunking, indexing
    status = Column(String, default='started')  # started, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Processing details
    input_data = Column(JSON, nullable=True)  # Input parameters
    output_data = Column(JSON, nullable=True)  # Output results
    error_message = Column(Text, nullable=True)
    
    # Performance metrics
    processing_time = Column(Float, nullable=True)  # Time in seconds
    memory_usage = Column(Float, nullable=True)  # Memory usage in MB
    cpu_usage = Column(Float, nullable=True)  # CPU usage percentage
    
    # Relationships
    video = relationship("Video", back_populates="processing_logs")
    
    def __repr__(self):
        return f"<VideoProcessing(id={self.id}, video_id={self.video_id}, step={self.step_name}, status={self.status})>"
