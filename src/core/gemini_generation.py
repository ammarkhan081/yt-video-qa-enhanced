"""
Groq-based generation module for YouTube RAG System.
"""

from typing import List, Dict
import logging
from groq import Groq


logger = logging.getLogger(__name__)


class GeminiGenerator:
    """Groq-based generation for RAG system (answers + summaries)."""

    def __init__(self, api_key: str, model_name: str = "llama-3.3-70b-versatile", temperature: float = 0.2):
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for GeminiGenerator")
        self.client = Groq(api_key=api_key)
        self.model_name = model_name
        self.temperature = temperature



    def generate_answer(self, question: str, context: List[Dict], video_id: str) -> Dict:
        try:
            context_text = self._prepare_context(context)
            prompt = self._answer_prompt(question, context_text, video_id)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            
            text = response.choices[0].message.content.strip()
            if not text:
                text = "I cannot find that information in the video."

            return {
                "answer": text,
                "sources": self._extract_sources(context),
                "confidence": self._estimate_confidence(text, context_text),
                "video_id": video_id,
                "model_type": "groq",
            }
        except Exception as e:
            error_str = str(e)
            logger.error(f"Groq answer generation failed: {e}", exc_info=True)
            
            # Check if it's a quota error
            if "429" in error_str or "quota" in error_str.lower():
                return {
                    "answer": "⚠️ API quota exceeded. Please wait a few minutes or check your Groq API key at https://console.groq.com/",
                    "sources": [],
                    "confidence": 0.0,
                    "video_id": video_id,
                    "error": "quota_exceeded",
                    "model_type": "groq",
                }
            
            return {
                "answer": f"I apologize, but I encountered an error: {error_str[:200]}",
                "sources": [],
                "confidence": 0.0,
                "video_id": video_id,
                "error": error_str[:200],
                "model_type": "groq",
            }

    def generate_summary(self, context: List[Dict], video_id: str) -> Dict:
        try:
            context_text = self._prepare_context(context)
            prompt = self._summary_prompt(context_text, video_id)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            
            summary = response.choices[0].message.content.strip()
            return {
                "summary": summary or "No summary available.",
                "video_id": video_id,
                "key_points": self._extract_key_points(summary),
                "model_type": "groq",
            }
        except Exception as e:
            logger.error(f"Groq summary generation failed: {e}")
            return {
                "summary": "Unable to generate summary due to an error.",
                "video_id": video_id,
                "key_points": [],
                "error": str(e),
                "model_type": "groq",
            }

    def _prepare_context(self, context: List[Dict]) -> str:
        parts: List[str] = []
        for i, doc in enumerate(context, 1):
            text = doc.get("text", "")
            md = doc.get("metadata", {})
            ts = md.get("timestamp", "")
            prefix = f"[Source {i}{' - ' + ts if ts else ''}]"
            parts.append(f"{prefix}: {text}")
        return "\n\n".join(parts)

    def _extract_sources(self, context: List[Dict]) -> List[Dict]:
        sources: List[Dict] = []
        for i, doc in enumerate(context, 1):
            md = doc.get("metadata", {})
            sources.append({
                "source_id": i,
                "text": (doc.get("text", "")[:200] + "...") if len(doc.get("text", "")) > 200 else doc.get("text", ""),
                "timestamp": md.get("timestamp", ""),
                "chunk_type": md.get("chunk_type", "paragraph"),
                "score": doc.get("score", 0.0),
            })
        return sources

    def _estimate_confidence(self, answer: str, context: str) -> float:
        if not answer:
            return 0.3
        aw = set(answer.lower().split())
        cw = set(context.lower().split())
        if not aw:
            return 0.3
        overlap = len(aw & cw)
        return min(0.9, 0.3 + (overlap / max(1, len(aw))) * 0.6)

    def _answer_prompt(self, question: str, context: str, video_id: str) -> str:
        return (
            "You are a helpful AI assistant that answers questions about YouTube videos.\n\n"
            "INSTRUCTIONS:\n"
            "1. FIRST, try to answer from the provided video transcript context below.\n"
            "2. If the transcript contains relevant information, use it and cite the sources.\n"
            "3. If the question is NOT covered in the transcript, use your general knowledge to provide a helpful answer.\n"
            "4. When using transcript info, prefix with '📺 From the video: ...'\n"
            "5. When using general knowledge, prefix with '💡 General knowledge: ...'\n"
            "6. You can combine both if helpful.\n"
            "7. Be concise, accurate, and helpful.\n\n"
            f"Video ID: {video_id}\n\n"
            f"VIDEO TRANSCRIPT CONTEXT:\n{context}\n\n"
            f"USER QUESTION: {question}\n\n"
            "ANSWER:"
        )

    def _summary_prompt(self, context: str, video_id: str) -> str:
        return (
            "Generate a comprehensive summary of the YouTube video based on the transcript."
            f"\nVideo ID: {video_id}\n\nTranscript Context:\n{context}\n\n"
            "Provide a structured summary with: 1) Main topic, 2) Key points, 3) Important details, 4) Conclusion.\n\nSummary:"
        )



    def _extract_key_points(self, summary: str) -> List[str]:
        """Extract up to 5 key points from a summary string."""
        try:
            lines = [l.strip() for l in summary.splitlines() if l.strip()]
            points: List[str] = []
            for l in lines:
                if l.startswith(('- ', '* ', '• ')):
                    points.append(l[2:].strip())
            # Fallback: split sentences and pick informative ones
            if not points:
                sentences = [s.strip() for s in summary.split('.') if s.strip()]
                for s in sentences:
                    if len(s) > 30:
                        points.append(s)
                        if len(points) >= 5:
                            break
            return points[:5]
        except Exception:
            return []

    def generate_answer_stream(self, question: str, context: List[Dict], video_id: str):
        """Generate answer with streaming support. Yields chunks of text."""
        try:
            context_text = self._prepare_context(context)
            prompt = self._answer_prompt(question, context_text, video_id)
            
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {"type": "token", "content": chunk.choices[0].delta.content}
            
            # Yield sources at the end
            yield {"type": "sources", "content": self._extract_sources(context)}
            yield {"type": "done", "content": ""}
            
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            yield {"type": "error", "content": str(e)}

