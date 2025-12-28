"""
Conversation and memory models for YouTube RAG System.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class Conversation(Base):
    """Conversation model for tracking user conversations."""
    
    __tablename__ = 'conversations'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    session_id = Column(String, ForeignKey('user_sessions.id'), nullable=True)
    video_id = Column(String, ForeignKey('videos.id'), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Conversation information
    title = Column(String, nullable=True)  # Auto-generated or user-provided title
    language = Column(String, default='en')
    
    # Conversation state
    is_active = Column(Boolean, default=True)
    total_messages = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    
    # Context information
    context_summary = Column(Text, nullable=True)  # Summary of conversation context
    key_topics = Column(JSON, nullable=True)  # Extracted key topics
    
    # Quality metrics
    user_satisfaction = Column(Float, nullable=True)  # User rating 0-1
    conversation_quality = Column(Float, nullable=True)  # AI-assessed quality
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    session = relationship("UserSession", back_populates="conversations")
    video = relationship("Video", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    conversation_memory = relationship("ConversationMemory", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, video_id={self.video_id})>"


class Message(Base):
    """Message model for storing individual messages in conversations."""
    
    __tablename__ = 'messages'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey('conversations.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Message content
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_type = Column(String, default='text')  # text, image, audio, etc.
    
    # Message metadata
    is_question = Column(Boolean, default=False)
    is_answer = Column(Boolean, default=False)
    is_system_message = Column(Boolean, default=False)
    
    # Processing information
    processing_time = Column(Float, nullable=True)  # Time to process in seconds
    token_count = Column(Integer, nullable=True)  # Number of tokens used
    
    # Response quality
    confidence_score = Column(Float, nullable=True)  # AI confidence in response
    relevance_score = Column(Float, nullable=True)  # Relevance to question
    helpfulness_score = Column(Float, nullable=True)  # User-assessed helpfulness
    
    # Source information (for assistant messages)
    sources = Column(JSON, nullable=True)  # List of source documents
    source_count = Column(Integer, default=0)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"


class ConversationMemory(Base):
    """Conversation memory model for context-aware follow-ups."""
    
    __tablename__ = 'conversation_memory'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey('conversations.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Memory content
    memory_type = Column(String, nullable=False)  # fact, preference, context, entity
    content = Column(Text, nullable=False)
    importance_score = Column(Float, default=0.5)  # Importance 0-1
    
    # Memory metadata
    source_message_id = Column(String, ForeignKey('messages.id'), nullable=True)
    extraction_method = Column(String, default='automatic')  # automatic, manual, hybrid
    
    # Memory relationships
    related_entities = Column(JSON, nullable=True)  # Related entities mentioned
    related_topics = Column(JSON, nullable=True)  # Related topics
    
    # Memory state
    is_active = Column(Boolean, default=True)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="conversation_memory")
    source_message = relationship("Message")
    
    def __repr__(self):
        return f"<ConversationMemory(id={self.id}, type={self.memory_type}, conversation_id={self.conversation_id})>"
