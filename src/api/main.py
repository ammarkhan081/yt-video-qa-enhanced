"""
FastAPI backend for YouTube RAG system.
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import asyncio
import time
import logging
import json

from config.settings import settings
from src.core.document_processor import MultilingualDocumentProcessor
from src.core.vector_store import EnhancedVectorStore
from src.core.retrieval import AdvancedRetriever
from src.core.gemini_generation import GeminiGenerator
from src.evaluation.ragas_evaluator import RAGASEvaluator
from src.evaluation.langsmith_monitor import LangSmithMonitor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="YouTube RAG System API",
    description="Industry-grade RAG system for YouTube video Q&A",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components
document_processor = None
vector_store = None
retriever = None
generator = None
ragas_evaluator = None
langsmith_monitor = None
def _normalize_video_id(raw: str) -> str:
    """Return a clean YouTube video id (strip timestamps/query/fragments)."""
    try:
        s = (raw or "").strip()
        # If full URL, try to extract v param
        if s.startswith("http://") or s.startswith("https://"):
            from urllib.parse import urlparse, parse_qs
            u = urlparse(s)
            qs = parse_qs(u.query)
            if "v" in qs and qs["v"]:
                return qs["v"][0]
            # Short links like youtu.be/<id>
            if u.netloc.endswith("youtu.be") and u.path:
                return u.path.lstrip("/")
        # If contains & or ? (e.g., "aircAruvnKk&t=10s") take the first token
        s = s.split("&", 1)[0]
        s = s.split("?", 1)[0]
        return s
    except Exception:
        return raw


class VideoProcessRequest(BaseModel):
    video_id: str
    language: str = "en"
    force_reprocess: bool = False


class QuestionRequest(BaseModel):
    question: str
    video_id: str
    include_sources: bool = True


class QuestionResponse(BaseModel):
    answer: str
    sources: List[Dict]
    confidence: float
    video_id: str
    processing_time: float


class VideoStatsResponse(BaseModel):
    video_id: str
    total_chunks: int
    avg_chunk_length: float
    total_text_length: int
    processing_status: str


class EvaluationRequest(BaseModel):
    questions: List[str]
    answers: List[str]
    contexts: List[List[str]]
    ground_truths: Optional[List[str]] = None


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global document_processor, vector_store, retriever, generator, ragas_evaluator, langsmith_monitor
    
    try:
        # Initialize components
        logger.info("Initializing document processor...")
        document_processor = MultilingualDocumentProcessor()
        
        logger.info("Initializing vector store (Pinecone)...")
        vector_store = EnhancedVectorStore(
            api_key=settings.pinecone_api_key,
            environment=settings.pinecone_environment,
            index_name=settings.pinecone_index_name,
            google_api_key=settings.google_api_key
        )
        logger.info("Vector store initialized successfully")
        
        logger.info("Initializing retriever...")
        retriever = AdvancedRetriever(vector_store, settings.llm_model)
        
        logger.info("Initializing Groq generator...")
        # Use Groq for text generation
        generator = GeminiGenerator(
            api_key=settings.groq_api_key,
            model_name=getattr(settings, 'llm_model', 'llama-3.3-70b-versatile'),
            temperature=getattr(settings, 'llm_temperature', 0.2),
        )
        logger.info(f"Groq model in use: {getattr(generator, 'model_name', 'unknown')}")
        
        if settings.enable_ragas:
            ragas_evaluator = RAGASEvaluator()
        
        if settings.enable_langsmith and settings.langsmith_api_key:
            langsmith_monitor = LangSmithMonitor(
                api_key=settings.langsmith_api_key,
                project_name="youtube-rag-system"
            )
        
        logger.info("All components initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "YouTube RAG System API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    components_status = {
        "document_processor": document_processor is not None,
        "vector_store": vector_store is not None,
        "retriever": retriever is not None,
        "generator": generator is not None,
    }
    model_info = getattr(generator, 'model_name', 'unknown') if generator else 'not initialized'
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "components": components_status,
        "llm_model": model_info
    }


@app.get("/test_api")
async def test_api():
    """Test if Gemini API is working and check quota."""
    try:
        if not generator:
            return {"status": "error", "message": "Generator not initialized"}
        
        # Try a minimal API call
        response = generator.model.generate_content(
            "Say 'API working' in exactly 2 words.",
            generation_config={"temperature": 0, "max_output_tokens": 10}
        )
        return {
            "status": "success",
            "model": generator.model_name,
            "response": response.text.strip() if response.text else "No response"
        }
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "quota" in error_msg.lower():
            return {
                "status": "quota_exceeded",
                "message": "API quota exceeded. Please wait or use a new API key.",
                "error": error_msg[:200]
            }
        return {"status": "error", "message": error_msg[:200]}


@app.post("/process_video", response_model=VideoStatsResponse)
async def process_video(request: VideoProcessRequest, background_tasks: BackgroundTasks):
    """Process a YouTube video and create vector embeddings."""
    try:
        start_time = time.time()
        
        # Extract transcript
        clean_vid = _normalize_video_id(request.video_id)
        transcript_data = document_processor.extract_transcript(
            clean_vid, request.language
        )
        
        if not transcript_data:
            raise HTTPException(status_code=404, detail="Could not extract transcript")
        
        # Process transcript into chunks
        chunks = document_processor.semantic_split(transcript_data['translated_text'])
        
        # Add to vector store
        vector_store.add_documents(
            documents=chunks,
            video_id=clean_vid,
            metadata={
                'original_language': transcript_data['original_language'],
                'target_language': transcript_data['target_language'],
                'processed_at': time.time()
            }
        )
        
        # Get video stats
        stats = vector_store.get_video_stats(clean_vid)
        
        processing_time = time.time() - start_time
        
        # Log to LangSmith if enabled
        if langsmith_monitor:
            langsmith_monitor.log_retrieval(
                query="video_processing",
                retrieved_docs=chunks,
                video_id=request.video_id,
                retrieval_time=processing_time,
                metadata={"operation": "video_processing"}
            )
        
        return VideoStatsResponse(
            video_id=clean_vid,
            total_chunks=stats['total_chunks'],
            avg_chunk_length=stats['avg_chunk_length'],
            total_text_length=stats['total_text_length'],
            processing_status="completed"
        )
        
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask_question", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """Ask a question about a video."""
    try:
        start_time = time.time()
        
        clean_vid = _normalize_video_id(request.video_id)
        logger.info(f"Question request: '{request.question}' for video: {clean_vid}")
        
        # Retrieve relevant documents
        retrieved_docs = retriever.retrieve_and_rank(
            query=request.question,
            video_id=clean_vid,
            top_k=settings.top_k
        )
        
        logger.info(f"Retrieved {len(retrieved_docs)} documents")
        
        if not retrieved_docs:
            return QuestionResponse(
                answer=f"I couldn't find relevant information in the video transcript. Please make sure the video (ID: {clean_vid}) has been processed first.",
                sources=[],
                confidence=0.0,
                video_id=clean_vid,
                processing_time=time.time() - start_time
            )
        
        # Generate answer
        answer_data = generator.generate_answer(
            question=request.question,
            context=retrieved_docs,
            video_id=clean_vid
        )
        
        processing_time = time.time() - start_time
        
        # Log to LangSmith if enabled
        if langsmith_monitor:
            langsmith_monitor.log_rag_pipeline(
                question=request.question,
                answer=answer_data['answer'],
                retrieved_docs=retrieved_docs,
                video_id=clean_vid,
                total_time=processing_time,
                metadata={"include_sources": request.include_sources}
            )
        
        return QuestionResponse(
            answer=answer_data['answer'],
            sources=answer_data['sources'] if request.include_sources else [],
            confidence=answer_data['confidence'],
            video_id=clean_vid,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Question answering failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask_question_stream")
async def ask_question_stream(request: QuestionRequest):
    """Ask a question about a video with streaming response."""
    try:
        clean_vid = _normalize_video_id(request.video_id)
        logger.info(f"Streaming question request: '{request.question}' for video: {clean_vid}")
        
        # Retrieve relevant documents
        retrieved_docs = retriever.retrieve_and_rank(
            query=request.question,
            video_id=clean_vid,
            top_k=settings.top_k
        )
        
        logger.info(f"Retrieved {len(retrieved_docs)} documents for video {clean_vid}")
        
        # If no documents found, return helpful message
        if not retrieved_docs:
            def no_docs_stream():
                error_msg = {
                    'type': 'token',
                    'content': f"I couldn't find any processed content for this video (ID: {clean_vid}). Please make sure the video has been processed first by clicking 'Process Video' in the extension."
                }
                yield f"data: {json.dumps(error_msg)}\n\n"
                yield f"data: {json.dumps({'type': 'sources', 'content': []})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"
            
            return StreamingResponse(
                no_docs_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
        def generate_stream():
            """Generator for SSE streaming."""
            try:
                logger.info(f"Starting answer generation for question: '{request.question}'")
                chunk_count = 0
                for chunk in generator.generate_answer_stream(
                    question=request.question,
                    context=retrieved_docs,
                    video_id=clean_vid
                ):
                    chunk_count += 1
                    logger.debug(f"Streaming chunk {chunk_count}: {chunk.get('type', 'unknown')}")
                    yield f"data: {json.dumps(chunk)}\n\n"
                logger.info(f"Completed streaming {chunk_count} chunks")
            except Exception as e:
                logger.error(f"Error in stream generation: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming question answering failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/video/{video_id}/summary")
async def get_video_summary(video_id: str):
    """Get video summary."""
    try:
        clean_vid = _normalize_video_id(video_id)
        # Retrieve documents for summary
        retrieved_docs = retriever.retrieve_and_rank(
            query="summary main topics key points",
            video_id=clean_vid,
            top_k=10
        )
        
        # Generate summary
        summary_data = generator.generate_summary(
            context=retrieved_docs,
            video_id=clean_vid
        )
        
        return summary_data
        
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/video/{video_id}/search")
async def search_video(video_id: str, query: str, limit: int = 10):
    """Search for specific content in video."""
    try:
        # Perform search
        clean_vid = _normalize_video_id(video_id)
        results = vector_store.similarity_search(
            query=query,
            top_k=limit,
            filter_dict={"video_id": clean_vid}
        )
        
        return {
            "query": query,
            "video_id": clean_vid,
            "results": results,
            "total_found": len(results)
        }
        
    except Exception as e:
        logger.error(f"Video search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/evaluate")
async def evaluate_system(request: EvaluationRequest):
    """Evaluate system using RAGAS."""
    try:
        if not ragas_evaluator:
            raise HTTPException(status_code=503, detail="RAGAS evaluator not available")
        
        # Run evaluation
        evaluation_results = ragas_evaluator.evaluate_rag_system(
            questions=request.questions,
            answers=request.answers,
            contexts=request.contexts,
            ground_truths=request.ground_truths
        )
        
        # Generate report
        report = ragas_evaluator.generate_evaluation_report(evaluation_results)
        
        return {
            "evaluation_results": evaluation_results,
            "report": report
        }
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/video/{video_id}")
async def delete_video(video_id: str):
    """Delete video from system."""
    try:
        clean_vid = _normalize_video_id(video_id)
        vector_store.delete_video(clean_vid)
        return {"message": f"Video {clean_vid} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Video deletion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def get_metrics():
    """Get system metrics."""
    try:
        metrics = {}
        
        if langsmith_monitor:
            metrics.update(langsmith_monitor.get_project_metrics())
        
        return metrics
        
    except Exception as e:
        logger.error(f"Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
