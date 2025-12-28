"""
User and session models for YouTube RAG System.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class User(Base):
    """User model for tracking user interactions."""
    
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # User identification
    extension_id = Column(String, unique=True, nullable=True)  # Chrome extension ID
    session_id = Column(String, nullable=True)  # Session identifier
    
    # User preferences
    language = Column(String, default='en')
    dark_mode = Column(Boolean, default=False)
    auto_process = Column(Boolean, default=False)
    show_sources = Column(Boolean, default=True)
    
    # Usage statistics
    total_questions = Column(Integer, default=0)
    total_videos_processed = Column(Integer, default=0)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, extension_id={self.extension_id})>"


class UserSession(Base):
    """User session model for tracking active sessions."""
    
    __tablename__ = 'user_sessions'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Session information
    session_token = Column(String, unique=True, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Session state
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, default=datetime.utcnow)
    
    # Current context
    current_video_id = Column(String, nullable=True)
    current_language = Column(String, default='en')
    
    # Session statistics
    questions_asked = Column(Integer, default=0)
    videos_processed = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"
