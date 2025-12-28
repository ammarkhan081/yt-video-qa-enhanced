# YouTube Video Intelligence

## Project Overview

YouTube Video Intelligence is an advanced AI-powered Chrome extension that enables users to have intelligent conversations with YouTube videos. Ask any question about a video's content and receive accurate, context-aware answers with citations and timestamps.

### What Problem Does It Solve?

- **No More Manual Scrubbing**: Find specific information in long videos instantly
- **Language Barriers**: Automatically translate and understand videos in 12+ languages
- **Information Extraction**: Get summaries, key points, and detailed explanations
- **Learning Efficiency**: Students and professionals can quickly extract knowledge from educational content

### Who Is It For?

- **Students**: Research and study from video lectures
- **Professionals**: Extract insights from conference talks and tutorials
- **Content Creators**: Analyze competitor content
- **Researchers**: Process large volumes of video content efficiently

## Features

### Unique Features
- **Real-time Streaming Responses**: Get answers as they're generated (like ChatGPT)
- **Multilingual Support**: Supports 12+ languages with automatic translation (English, Spanish, French, German, Italian, Portuguese, Russian, Chinese, Japanese, Korean, Arabic, Urdu)
- **Timestamp Citations**: Every answer includes exact video timestamps
- **Conversational Memory**: Follow-up questions with context awareness
- **Modern UI**: Beautiful dark/light mode interface integrated directly into YouTube

### Core Capabilities
- **Advanced RAG (Retrieval-Augmented Generation)**: Uses semantic search to find relevant video segments
- **Smart Chunking**: Paragraph and sentence-level segmentation for precise answers
- **MMR (Maximal Marginal Relevance)**: Diverse, non-redundant information retrieval
- **Groq LLM Integration**: Lightning-fast responses with llama-3.3-70b-versatile
- **Vector Search**: Pinecone-powered semantic search with 768-dimensional embeddings
- **Auto-Translation**: Gemini-powered translation for non-English videos
- **Citation-Backed Answers**: All responses include source transcript snippets

## Technology Stack

### Frontend
- **Chrome Extension**: Manifest V3 with modern JavaScript
- **UI Framework**: Vanilla JS with custom CSS
- **Features**: Real-time streaming, dark mode, responsive design

### Backend
- **Framework**: FastAPI (Python 3.12+)
- **Server**: Uvicorn ASGI server
- **API Design**: RESTful with Server-Sent Events (SSE) for streaming

### AI/ML Tools
- **LLM**: Groq Cloud (llama-3.3-70b-versatile) - Ultra-fast inference
- **Embeddings**: Google Gemini text-embedding-004 (768 dimensions)
- **Translation**: Google Gemini 2.5-flash for multilingual support
- **RAG Framework**: Custom implementation with MMR algorithm

### Database & Storage
- **Vector Database**: Pinecone (Serverless, AWS us-east-1)
- **Metric**: Cosine similarity
- **Index**: youtube-rag with metadata filtering

### Infrastructure & Tools
- **YouTube Processing**: yt-dlp for transcript extraction
- **Environment**: Python virtual environment (venv)
- **Configuration**: python-dotenv for environment variables
- **Monitoring**: LangSmith (optional) and RAGAS evaluation

## Prerequisites

- **Python**: 3.11 or higher
- **Google Chrome**: Latest version
- **API Keys**:
  - Groq API Key (get free at https://console.groq.com/)
  - Google Gemini API Key (get free at https://aistudio.google.com/apikey)
  - Pinecone API Key (get free at https://app.pinecone.io)

## Setup Instructions

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/yt-video-qa-enhanced.git
cd yt-video-qa-enhanced
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
```bash
# Copy the example file
cp env.example .env

# Edit .env and add your API keys:
# GROQ_API_KEY=your_groq_api_key_here
# GOOGLE_API_KEY=your_google_api_key_here
# PINECONE_API_KEY=your_pinecone_api_key_here
```

**Get Your API Keys:**
- **Groq**: https://console.groq.com/keys (Free, 14,400 requests/day)
- **Google Gemini**: https://aistudio.google.com/apikey (Free tier available)
- **Pinecone**: https://app.pinecone.io (Free tier: 1 index, 100K vectors)

### Step 5: Start the Backend Server
```bash
# Make sure virtual environment is activated
python -m uvicorn src.api.main:app --reload --port 8000
```

You should see:
```
INFO:     Application startup complete.
INFO:     Groq model in use: llama-3.3-70b-versatile
```

### Step 6: Install Chrome Extension
1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `chrome-extension` folder from this project
5. The extension icon should appear in your toolbar

## Usage

### Using the Chrome Extension

#### 1. Open a YouTube Video
Navigate to any YouTube video, for example:
- https://www.youtube.com/watch?v=dQw4w9WgXcQ

#### 2. Open the Extension Panel
- Click the extension icon in your Chrome toolbar
- Or use the sidebar that appears on YouTube pages
- You should see "✅ Connected" status

#### 3. Process the Video
- Click the **"Process Video"** button
- Wait for the transcript to be extracted and processed (5-30 seconds depending on video length)
- You'll see: "✅ Video processed successfully!"

#### 4. Ask Questions
Type your questions in the chat input, such as:
- "What is this video about?"
- "Summarize the main points"
- "What does the speaker say about [topic]?"
- "At what timestamp does [event] happen?"

#### 5. Get Streaming Answers
- Watch the answer stream in real-time
- See source citations with timestamps
- Click timestamps to jump to that point in the video

### Example Questions
```
User: "What is this video about?"
AI: "From the video: This is a music video..."

User: "What instruments are featured?"
AI: "Based on the audio, the video features..."
```

### API Usage (For Developers)

#### Check Backend Health
```bash
curl http://localhost:8000/health
```

#### Process a Video
```bash
curl -X POST "http://localhost:8000/process_video" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "dQw4w9WgXcQ",
    "language": "en"
  }'
```

#### Ask a Question
```bash
curl -X POST "http://localhost:8000/ask_question" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this video about?",
    "video_id": "dQw4w9WgXcQ"
  }'
```

#### Get Video Summary
```bash
curl "http://localhost:8000/video/dQw4w9WgXcQ/summary"
```

### Streaming Response
The extension uses Server-Sent Events (SSE) for real-time streaming:
```
/ask_question_stream?video_id=xxx&question=yyy
```

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     YouTube Video Page                       │
│  ┌────────────────────────────────────────────────────┐     │
│  │           Chrome Extension (Frontend)              │     │
│  │  • Content Script: Chat UI injection               │     │
│  │  • Background Script: Service worker               │     │
│  │  • Popup: Settings & configuration                 │     │
│  └──────────────────┬─────────────────────────────────┘     │
└─────────────────────┼───────────────────────────────────────┘
                      │ HTTP/SSE
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (localhost:8000)                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Endpoints:                                      │   │
│  │  • /process_video - Extract & process transcripts    │   │
│  │  • /ask_question_stream - Streaming Q&A             │   │
│  │  • /video/{id}/summary - Generate summaries         │   │
│  └──────────────────┬───────────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌─────────────┐ ┌──────────┐ ┌────────────┐
│   Groq AI   │ │  Google  │ │  Pinecone  │
│  (LLM for   │ │  Gemini  │ │  (Vector   │
│  Generation)│ │  (Embed) │ │   Store)   │
└─────────────┘ └──────────┘ └────────────┘
```

### Data Flow

1. **User asks question** → Chrome Extension
2. **Extension sends** → FastAPI Backend (SSE stream)
3. **Backend retrieves** → Video embeddings from Pinecone
4. **Backend generates** → Answer using Groq LLM
5. **Backend streams** → Tokens back to extension
6. **Extension displays** → Real-time answer with citations

### Core Modules

```
yt-video-qa-enhanced/
├── chrome-extension/       # Chrome Extension (Manifest V3)
│   ├── manifest.json      # Extension configuration
│   ├── background.js      # Service worker
│   ├── content.js         # Chat UI & video interaction
│   ├── popup.js           # Settings popup
│   └── styles.css         # UI styling
│
├── src/
│   ├── api/
│   │   └── main.py        # FastAPI app with 12 endpoints
│   ├── core/
│   │   ├── document_processor.py   # YouTube transcript extraction
│   │   ├── gemini_generation.py    # Groq LLM integration
│   │   ├── retrieval.py            # MMR retrieval algorithm
│   │   └── vector_store.py         # Pinecone + Gemini embeddings
│   ├── models/            # Pydantic data models
│   └── evaluation/        # RAGAS & LangSmith monitoring
│
├── config/
│   └── settings.py        # Environment configuration
│
└── tests/                 # Test suite
    ├── test_api.py
    ├── test_core_components.py
    └── test_chrome_extension.py
```

## Configuration

### Environment Variables (.env)

```bash
# ===== API KEYS (REQUIRED) =====
# Groq API Key (for text generation)
GROQ_API_KEY=your_groq_api_key_here

# Google Gemini API Key (for embeddings)
GOOGLE_API_KEY=your_google_api_key_here

# Pinecone API Configuration
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=youtube-rag

# ===== LLM SETTINGS =====
LLM_MODEL_TYPE=groq
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.2
MAX_TOKENS=1000

# ===== VECTOR STORE =====
EMBEDDING_MODEL=models/text-embedding-004
EMBEDDING_DIMENSION=768

# ===== RETRIEVAL SETTINGS =====
TOP_K=6
SIMILARITY_THRESHOLD=0.7
MMR_DIVERSITY_THRESHOLD=0.3

# ===== TRANSLATION =====
DEFAULT_LANGUAGE=en
SUPPORTED_LANGUAGES=en,es,fr,de,it,pt,ru,zh,ja,ko,ar,ur

# ===== OPTIONAL =====
ENABLE_RAGAS=false
ENABLE_LANGSMITH=false
LANGSMITH_API_KEY=your_langsmith_key_here
```

### Extension Configuration

Edit `chrome-extension/popup.js` to change:
- Backend URL (default: `http://localhost:8000`)
- UI preferences
- Auto-analyze settings

## Testing

### Manual Testing
1. **Test Backend Health**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Test Video Processing**:
   - Use test video: https://www.youtube.com/watch?v=dQw4w9WgXcQ
   - Process via extension or API

3. **Test Q&A**:
   ```bash
   curl "http://localhost:8000/ask_question_stream?video_id=dQw4w9WgXcQ&question=What%20is%20this%20video%20about?"
   ```

### Automated Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific tests
pytest tests/test_api.py
pytest tests/test_core_components.py
```

### Common Issues

**Backend not connecting?**
- Check if port 8000 is already in use
- Ensure virtual environment is activated
- Verify all API keys are set in `.env`

**Extension not loading?**
- Make sure Developer mode is enabled in Chrome
- Check console for errors (F12 → Console)
- Reload the extension after code changes

**No answers generating?**
- Check Groq API quota (14,400 requests/day on free tier)
- Verify video is processed first
- Check backend terminal for errors

## Performance & Scalability

### Performance Metrics
- **Response Time**: < 2 seconds for most queries
- **Streaming**: Real-time token generation
- **Concurrent Users**: Supports multiple simultaneous users
- **Vector Search**: < 100ms query time with Pinecone

### Groq Speed Advantage
- **Groq LLM**: 10x faster than traditional LLM APIs
- **Throughput**: 500+ tokens/second
- **Free Tier**: 14,400 requests/day

### Scalability
- Pinecone serverless: Auto-scales with usage
- FastAPI: Async/await for high concurrency
- Stateless backend: Easy horizontal scaling

## How It Works

### RAG Pipeline

1. **Document Processing**:
   ```
   YouTube Video → yt-dlp → VTT Transcript → Translation (if needed)
   → Semantic Chunking → Gemini Embeddings → Pinecone Storage
   ```

2. **Question Answering**:
   ```
   User Question → Gemini Embedding → Pinecone Search (MMR)
   → Top-K Retrieval → Groq LLM → Streaming Response
   ```

3. **Streaming Flow**:
   ```
   FastAPI SSE Stream → Real-time Tokens → Chrome Extension
   → Incremental UI Update
   ```

## Project Structure

```
yt-video-qa-enhanced/
│
├── chrome-extension/          # Chrome Extension (Frontend)
│   ├── manifest.json         # Extension manifest (V3)
│   ├── background.js         # Service worker
│   ├── content.js            # YouTube page integration
│   ├── popup.html            # Settings popup
│   ├── popup.js              # Popup logic
│   └── styles.css            # UI styling
│
├── src/                      # Backend source code
│   ├── api/
│   │   └── main.py          # FastAPI application (12 endpoints)
│   ├── core/
│   │   ├── document_processor.py    # YouTube transcript extraction
│   │   ├── gemini_generation.py     # Groq LLM wrapper
│   │   ├── retrieval.py             # MMR retrieval
│   │   └── vector_store.py          # Pinecone + embeddings
│   ├── models/              # Data models
│   │   ├── video_models.py
│   │   ├── conversation_models.py
│   │   └── evaluation_models.py
│   └── evaluation/          # Evaluation tools
│       ├── ragas_evaluator.py
│       └── langsmith_monitor.py
│
├── config/
│   └── settings.py          # Configuration management
│
├── tests/                   # Test suite
│   ├── test_api.py
│   ├── test_core_components.py
│   └── test_chrome_extension.py
│
├── .env                     # Environment variables (create from env.example)
├── env.example              # Environment template
├── requirements.txt         # Python dependencies
├── pytest.ini              # Test configuration
└── README.md               # This file
```

## Deployment

### Local Development
Already covered in Setup Instructions above.

### Production Deployment (Optional)

**Using Docker** (if you want to containerize):
```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Cloud Deployment Options**:
- **Backend**: Deploy to Render, Railway, or Heroku
- **Database**: Pinecone serverless (already cloud-based)
- **Extension**: Publish to Chrome Web Store (optional)

### Environment-Specific Configs
- **Development**: Use `.env` with `DEBUG=true`
- **Production**: Use environment variables in your cloud platform
- **Testing**: Use separate Pinecone index for tests

## Live Demo

### Quick Demo Steps

1. **Start Backend** (takes 5 seconds):
   ```bash
   .\venv\Scripts\Activate.ps1
   python -m uvicorn src.api.main:app --reload --port 8000
   ```

2. **Install Extension** (one-time setup):
   - `chrome://extensions/` → Developer mode → Load unpacked → Select `chrome-extension` folder

3. **Try It Out**:
   - Open: https://www.youtube.com/watch?v=dQw4w9WgXcQ
   - Click extension icon
   - Click "Process Video"
   - Ask: "What is this video about?"
   - Watch the AI answer stream in real-time!

### Video Demo
*(Add your demo video link here after recording)*

### Screenshots
*(You can add screenshots of your working extension here)*

Example:
- Extension connected to YouTube
- Processing a video
- Getting streaming answers with citations

## Contributing

Contributions are welcome! Here's how:

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes** and test thoroughly
4. **Commit with clear messages**:
   ```bash
   git commit -m 'Add amazing feature: [description]'
   ```
5. **Push to your fork**:
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open a Pull Request**

### Development Guidelines
- Follow PEP 8 for Python code
- Add tests for new features
- Update documentation
- Keep commits atomic and descriptive


## Acknowledgments

### Technologies & Services
- **[Groq](https://groq.com/)** - Ultra-fast LLM inference platform
- **[Google Gemini](https://ai.google.dev/)** - Embeddings and translation
- **[Pinecone](https://www.pinecone.io/)** - Vector database for semantic search
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** - YouTube transcript extraction

### Inspirations
- Modern RAG architectures and best practices
- Chrome Extension Manifest V3 patterns
- Real-time streaming UX design

## Support & Contact

### Get Help
- **Issues**: [Create an issue](https://github.com/yourusername/yt-video-qa-enhanced/issues)
- **Documentation**: Check this README and inline code comments
- **API Reference**: Visit `http://localhost:8000/docs` when backend is running

### Project Links
- **GitHub**: https://github.com/yourusername/yt-video-qa-enhanced
- **Demo Video**: *(Add your demo link here)*
- **Documentation**: [Full docs in PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)

### API Keys & Resources
- **Groq Console**: https://console.groq.com/
- **Google AI Studio**: https://aistudio.google.com/
- **Pinecone Dashboard**: https://app.pinecone.io/

---

## Features Summary

| Feature | Description | Technology |
|---------|-------------|------------|
| **Real-time Q&A** | Ask questions about any YouTube video | Groq + RAG |
| **Streaming Responses** | ChatGPT-like streaming experience | Server-Sent Events |
| **Multilingual** | Support for 12+ languages | Gemini Translation |
| **Smart Search** | Semantic search with citations | Pinecone + MMR |
| **Chrome Integration** | Native YouTube experience | Manifest V3 |
| **Fast Inference** | Sub-2-second responses | Groq Cloud |
| **Free Tier** | 14,400 requests/day | Groq Free API |

---

<div align="center">

Made with Groq, Gemini, Pinecone, and FastAPI

</div>
