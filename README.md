# ParakeetAI Clone — Real-Time AI Interview Copilot

An open-source, real-time AI interview copilot for your phone. It captures audio from your microphone, transcribes it using Groq's Whisper API, detects questions, and streams AI-generated answers instantly using Groq's LLM.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- A [Groq API key](https://console.groq.com/keys) (free tier works)

### 1. Set up the backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Add your Groq API key

Edit `backend/.env`:
```
GROQ_API_KEY=gsk_your_key_here
```

### 3. Start the server

```bash
cd backend
python run.py
```

### 4. Open on your phone

1. Find your PC's local IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
2. On your phone browser, open: `http://<your-pc-ip>:8000`
3. Upload your resume (PDF) and job description
4. Tap "Start Interview Mode"
5. Tap the microphone button and start your interview!

> **Note**: For microphone access on phone, you may need to use Chrome and enable the flag:
> `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
> Add your server URL (e.g., `http://192.168.1.5:8000`) to the list.

## 📱 How It Works

1. **You're in an interview** (phone call, video call, or in-person)
2. **Your phone listens** via the browser microphone
3. **When the interviewer asks a question**, the app:
   - Transcribes the speech using Groq Whisper (< 500ms)
   - Detects that it's a question
   - Generates a personalized answer using your resume + job description
   - Streams the answer to your phone screen in real-time
4. **You glance at your phone** and deliver a polished answer

## 🛠 Architecture

```
Phone Browser (mic) → WebSocket → FastAPI Backend
                                    ├── Groq Whisper (ASR)
                                    ├── Question Detection
                                    ├── Context Assembly (Resume + JD)
                                    └── Groq LLM (llama-3.3-70b-versatile)
                                          │
                                    ← Streaming tokens ←
```

## 📁 Project Structure

```
parakeetai-clone/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + REST endpoints
│   │   ├── config.py            # Environment config
│   │   ├── transcription/       # Groq Whisper ASR
│   │   ├── llm/                 # Groq LLM + prompts
│   │   ├── context/             # Resume/JD management + PDF
│   │   └── ws/                  # WebSocket handler
│   ├── context_docs/            # Resume & JD files
│   ├── requirements.txt
│   └── run.py
├── phone-client/                # Mobile web app
│   ├── index.html
│   ├── css/styles.css
│   └── js/                      # Audio, WebSocket, UI modules
└── README.md
```

## ⚙️ Configuration

All config is in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (required) | Your Groq API key |
| `GROQ_LLM_MODEL` | `llama-3.3-70b-versatile` | LLM model for answers |
| `GROQ_ASR_MODEL` | `distil-whisper-large-v3-en` | ASR model for transcription |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

## 📄 License

MIT — Use freely, improve freely, share freely.
