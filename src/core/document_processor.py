""" Enhanced document processing with multilingual support using Gemini. """
import re
import tempfile
import os
import shutil
import glob
from typing import List, Dict, Optional
import yt_dlp
import google.generativeai as genai
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultilingualDocumentProcessor:
    """Process YouTube videos with multilingual support using Gemini for translation."""
    
    def __init__(self, google_api_key: str = None):
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY")
        if self.google_api_key:
            genai.configure(api_key=self.google_api_key)
            self.translation_model = self._get_translation_model()
        else:
            self.translation_model = None
        logger.info("MultilingualDocumentProcessor initialized (using Gemini for translation)")
    
    def _get_translation_model(self):
        """Get available Gemini model for translation."""
        try:
            # Prefer 2.5 models (newer, separate quota from 2.0)
            preferred = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash-lite", "gemini-2.0-flash"]
            available = []
            for m in genai.list_models():
                if "generateContent" in (m.supported_generation_methods or []):
                    name = m.name.replace("models/", "")
                    available.append(name)
            
            for pref in preferred:
                if pref in available:
                    logger.info(f"Using model for translation: {pref}")
                    return genai.GenerativeModel(pref)
            
            # Fallback to first available
            for m in genai.list_models():
                if "generateContent" in (m.supported_generation_methods or []):
                    model_name = m.name.replace("models/", "")
                    if "exp" not in model_name.lower():
                        logger.info(f"Using model for translation: {model_name}")
                        return genai.GenerativeModel(model_name)
        except Exception as e:
            logger.error(f"Error getting translation model: {e}")
        return None

    def _translate_with_gemini(self, text: str, source_lang: str) -> str:
        """Translate text to English using Gemini."""
        if not self.translation_model or source_lang == "en":
            return text
        
        try:
            prompt = f"""Translate the following text from {source_lang} to English. 
Only output the translation, nothing else.

Text to translate:
{text}"""
            
            response = self.translation_model.generate_content(prompt)
            translated = response.text.strip() if response.text else text
            return translated
        except Exception as e:
            logger.warning(f"Gemini translation failed: {e}. Returning original text.")
            return text

    def extract_transcript(self, video_id: str, language: str = "en") -> Optional[Dict]:
        """
        Extract transcript using yt-dlp native API with automatic language detection.
        Falls back through: requested language -> auto-captions -> manual captions -> English
        """
        tmpdir = tempfile.mkdtemp(prefix="yt_trans_")
        try:
            out_template = os.path.join(tmpdir, "temp_transcript.%(ext)s")
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # First, get video info to check available subtitles
            info_opts = {
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
            
            available_subs = info.get('subtitles', {})
            available_auto = info.get('automatic_captions', {})
            
            # Determine best language to use
            detected_language = None
            use_auto = False
            
            # Priority: 1) Manual subs in requested lang, 2) Auto subs in requested lang,
            # 3) Manual English, 4) Auto English, 5) Any available
            if language in available_subs:
                detected_language = language
                use_auto = False
            elif language in available_auto:
                detected_language = language
                use_auto = True
            elif 'en' in available_subs:
                detected_language = 'en'
                use_auto = False
            elif 'en' in available_auto:
                detected_language = 'en'
                use_auto = True
            elif available_subs:
                detected_language = list(available_subs.keys())[0]
                use_auto = False
            elif available_auto:
                detected_language = list(available_auto.keys())[0]
                use_auto = True
            else:
                logger.error(f"No subtitles found for video {video_id} (ID: {info.get('id')}, Title: {info.get('title')})")
                return {"error": "No subtitles found"}
            
            # Normalize language code
            detected_language = detected_language.split('-')[0]
            
            logger.info(f"Using {detected_language} {'auto' if use_auto else 'manual'} captions for video {video_id}")
            
            # Download subtitles
            download_opts = {
                'skip_download': True,
                'writesubtitles': not use_auto,
                'writeautomaticsub': use_auto,
                'subtitleslangs': [detected_language],
                'subtitlesformat': 'vtt',
                'outtmpl': out_template,
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(download_opts) as ydl:
                ydl.download([video_url])
            
            # Find downloaded VTT file
            vtt_files = glob.glob(os.path.join(tmpdir, "*.vtt"))
            if not vtt_files:
                logger.error(f"Failed to download subtitles for video {video_id} (ID: {info.get('id')}, Title: {info.get('title')}). Available subs: {list(available_subs.keys())}, Available auto: {list(available_auto.keys())}")
                return {"error": "No subtitles found"}
            
            # Read and parse VTT
            with open(vtt_files[0], 'r', encoding='utf-8', errors='ignore') as f:
                vtt_content = f.read()
            
            transcript_data = self._parse_vtt(vtt_content)
            cleaned_text = self._clean_transcript(transcript_data)
            
            # Translate if needed using Gemini
            translated_text = cleaned_text
            if detected_language != 'en':
                translated_text = self._translate_with_gemini(cleaned_text, detected_language)
                if translated_text != cleaned_text:
                    logger.info(f"Translated transcript from {detected_language} to English using Gemini")
            
            return {
                'original_text': cleaned_text,
                'translated_text': translated_text,
                'original_language': detected_language,
                'target_language': 'en',
                'video_id': video_id
            }
            
        except Exception as e:
            logger.exception(f"Failed to extract transcript for {video_id}: {e}")
            return {"error": f"Failed to extract transcript: {str(e)}"}
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    def _parse_vtt(self, vtt_content: str) -> List[Dict]:
        """
        Parse VTT content into transcript format.
        Handles various VTT formats and timestamp patterns.
        """
        lines = vtt_content.splitlines()
        cues = []
        current_cue = []
        
        for raw in lines:
            line = raw.strip()
            if not line:
                # Blank line separates cues
                if current_cue:
                    text = " ".join(current_cue).strip()
                    if text:
                        cues.append({'text': re.sub(r'\s+', ' ', text)})
                    current_cue = []
                continue
            
            # Skip headers/metadata
            if line.startswith("WEBVTT") or line.startswith("NOTE") or \
               line.startswith("Kind:") or line.startswith("Language:"):
                continue
            
            # Skip cue index lines (just a number)
            if re.match(r'^\d+$', line):
                continue
            
            # Skip timestamp lines (various formats)
            if "-->" in line or \
               re.match(r'^\d{1,2}:\d{2}:\d{2}', line) or \
               re.match(r'^\d{1,2}:\d{2}\.\d{3}', line) or \
               re.match(r'^0:\d{2}:\d{2}', line):
                continue
            
            # Clean HTML tags and bracketed notes
            cleaned = re.sub(r'<[^>]+>', '', line)
            cleaned = re.sub(r'\[.*?\]', '', cleaned)
            cleaned = cleaned.strip()
            
            if cleaned and len(cleaned) > 2:
                current_cue.append(cleaned)
        
        # Push final cue
        if current_cue:
            text = " ".join(current_cue).strip()
            if text:
                cues.append({'text': re.sub(r'\s+', ' ', text)})
        
        return cues

    def _clean_transcript(self, transcript_data: List[Dict]) -> str:
        """Clean transcript data by removing noise and normalizing text."""
        text_parts = []
        for entry in transcript_data:
            text = entry.get('text', '').strip()
            if not text:
                continue
            
            # Remove speaker labels and timestamps
            text = re.sub(r'^\[.*?\]', '', text)
            text = re.sub(r'^\d+:\d+', '', text)
            text = re.sub(r'^[A-Z\s0-9\-]{1,30}:', '', text)
            text = text.strip()
            
            if text:
                text_parts.append(text)
        
        # Join text
        full_text = ' '.join(text_parts)
        
        # Remove common noise patterns
        noise_patterns = [
            r'subscribe to.*?channel',
            r'like.*?video',
            r'hit.*?bell',
            r'thanks for watching',
            r'don\'t forget to',
            r'notification bell',
            r'patreon',
            r'sponsor',
        ]
        
        for pattern in noise_patterns:
            full_text = re.sub(pattern, ' ', full_text, flags=re.IGNORECASE)
        
        # Normalize whitespace
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        return full_text

    def semantic_split(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
        """Semantic-aware text splitting with paragraph and sentence boundaries."""
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append({
                        'text': current_chunk.strip(),
                        'type': 'paragraph',
                        'length': len(current_chunk)
                    })
                current_chunk = paragraph + "\n\n"
        
        # Add remaining chunk
        if current_chunk:
            chunks.append({
                'text': current_chunk.strip(),
                'type': 'paragraph',
                'length': len(current_chunk)
            })
        
        # Further split large chunks by sentences
        final_chunks = []
        for chunk in chunks:
            if chunk['length'] > chunk_size:
                sentences = re.split(r'(?<=[.!?])\s+', chunk['text'])
                current_sentence_chunk = ""
                
                for sentence in sentences:
                    if len(current_sentence_chunk) + len(sentence) <= chunk_size:
                        current_sentence_chunk += sentence + " "
                    else:
                        if current_sentence_chunk:
                            final_chunks.append({
                                'text': current_sentence_chunk.strip(),
                                'type': 'sentence',
                                'length': len(current_sentence_chunk)
                            })
                        current_sentence_chunk = sentence + " "
                
                if current_sentence_chunk:
                    final_chunks.append({
                        'text': current_sentence_chunk.strip(),
                        'type': 'sentence',
                        'length': len(current_sentence_chunk)
                    })
            else:
                final_chunks.append(chunk)
        
        return final_chunks