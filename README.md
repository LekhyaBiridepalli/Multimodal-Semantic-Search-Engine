# 🔍 Multimodal Semantic Search Engine

An intelligent, multimodal semantic search engine that retrieves, connects, and summarizes information across **YouTube videos**, **books**, and **research papers** using **NLP**, **Temporal Knowledge Graphs (TKG)**, and **Retrieval-Augmented Generation (RAG)**.

Built with Flask, this full-stack web application provides a rich, interactive dashboard for knowledge discovery and synthesis.

---

## ✨ Features

- **Multimodal Search** — Search across YouTube videos, Google Books, and Semantic Scholar research papers simultaneously
- **Temporal Knowledge Graphs** — Build and visualize knowledge graphs that track entity relationships over time
- **RAG-Powered Summaries** — Retrieval-Augmented Generation using Google Gemini for intelligent, context-aware summaries
- **User Dashboard** — Interactive analytics, search history, favorites, and activity tracking
- **PDF Export** — Download comprehensive knowledge reports as formatted PDFs
- **User Authentication** — Secure registration, login, and profile management with Flask-Login and bcrypt
- **Responsive UI** — Modern, glassmorphism-styled frontend with dynamic animations

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Flask (Python 3.8+) |
| **Database** | PostgreSQL (via SQLAlchemy + psycopg2) |
| **LLM** | Google Gemini API |
| **APIs** | YouTube Data API v3, Google Books API, Semantic Scholar API |
| **NLP** | Sentence Transformers (`all-MiniLM-L6-v2`) |
| **Frontend** | HTML5, CSS3 (glassmorphism), JavaScript, Chart.js |
| **Auth** | Flask-Login, Flask-Bcrypt, Flask-WTF (CSRF) |
| **PDF** | ReportLab, xhtml2pdf |

---

## 📁 Project Structure

```
├── app.py                     # Flask application entry point (run this)
├── config.py                  # Configuration (reads from .env)
├── database_setup.sql         # PostgreSQL schema and seed data
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
│
├── models/
│   ├── database.py            # SQLAlchemy models (User, SearchHistory, etc.)
│   └── tkag_rag.py            # TKAG-RAG engine (knowledge graph + retrieval)
│
├── utils/
│   ├── __init__.py            # Utility exports
│   ├── helpers.py             # Helper functions (file handling, validation)
│   ├── llm_summarizer.py      # Google Gemini LLM integration
│   └── pdf_generator.py       # PDF report generation
│
├── templates/                 # Jinja2 HTML templates
│   ├── base.html              # Base layout with navigation
│   ├── index.html             # Landing page
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── dashboard.html         # User dashboard
│   ├── generate.html          # Search / knowledge generation
│   ├── result.html            # Search results with KG visualization
│   ├── history.html           # Search history
│   ├── profile.html           # User profile management
│   ├── stats.html             # User statistics and analytics
│   ├── activity.html          # Activity log
│   ├── 404.html               # Not found error page
│   └── 500.html               # Server error page
│
└── static/
    ├── css/style.css          # Main stylesheet
    └── js/main.js             # Client-side JavaScript
```

---

## 🚀 How to Run

### Prerequisites

- **Python 3.8+** — [Download](https://www.python.org/downloads/)
- **PostgreSQL Server** — [Download](https://www.postgresql.org/download/)
- **Git** — [Download](https://git-scm.com/downloads)
- **Google API Keys** (see [API Keys](#-api-keys-required) section below)

### Step 1: Clone the Repository

```bash
git clone https://github.com/LekhyaBiridepalli/Multimodal-Semantic-Search-Engine.git
cd Multimodal-Semantic-Search-Engine
```

### Step 2: Create a Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** The project uses `psycopg2-binary` as the PostgreSQL adapter, which includes pre-compiled binaries and should install easily across operating systems.

### Step 4: Set Up Environment Variables

```bash
# Copy the example environment file
cp .env.example .env       # macOS/Linux
copy .env.example .env     # Windows
```

Open `.env` in a text editor and fill in your actual values:

```env
GOOGLE_API_KEY=your-google-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here
SECRET_KEY=any-random-secret-string
# For local development
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=postgresql
PG_DB=tkrag

# For Render deployment
# DATABASE_URL=postgresql://user:password@hostname/dbname
```

### Step 5: Set Up the Database

1. **Start PostgreSQL Server** (if not already running) and ensure `tkrag` database is created.
   ```bash
   createdb -U postgres tkrag
   ```

2. **Initialize the database and tables** by running the setup script:

```bash
python init_db.py
```

This will create the `tkrag` database with all required tables and seed data (including a default admin user).

### Step 6: Run the Application

```bash
python app.py
```

The application will start at **http://localhost:5000**

### Step 7: Log In

Use the default credentials to get started:

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Test User | `testuser` | `test123` |

Or register a new account from the registration page.

---

## 🔑 API Keys Required

You will need the following API keys (all free tier):

### Google API Key (YouTube + Books)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **YouTube Data API v3** and **Books API**
4. Go to **Credentials** → **Create Credentials** → **API Key**
5. Copy the key to `GOOGLE_API_KEY` in your `.env` file

### Google Gemini API Key (LLM)
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click **Create API Key**
3. Copy the key to `GEMINI_API_KEY` in your `.env` file

> **Note:** The Semantic Scholar API (for research papers) does not require an API key.

---

## 🗄️ Database

### PostgreSQL Setup

The application uses PostgreSQL as its primary database. The `database_setup.sql` script creates:

- **`users`** — User accounts with authentication
- **`search_history`** — Search queries, results (JSON), summaries, and PDF paths
- **`favorites`** — User-bookmarked searches
- **`knowledge_graph`** — Persistent entity and relation storage
- **`activity_logs`** — User activity tracking
- **`sessions`** — Flask session storage

### Default Connection

```
Host: localhost
Port: 5432
Database: tkrag
```

Configure these in your `.env` file.

---

## ⚙️ Models & Performance

The system uses pre-trained NLP models that are **downloaded automatically** on first run:

| Model | Purpose | Size |
|-------|---------|------|
| `sentence-transformers/all-MiniLM-L6-v2` | Semantic embeddings | ~80 MB |
| Google Gemini (API) | LLM summarization | Cloud-based |

- **First run** may take a few minutes to download models (~80 MB)
- Subsequent runs use locally cached models
- GPU acceleration is used automatically if available (via PyTorch/CUDA)

---

## 🔧 Troubleshooting

### PostgreSQL Connection Errors
- Ensure PostgreSQL server is running: `psql -U postgres`
- Verify credentials in `.env` match your PostgreSQL setup
- Check that `tkrag` database exists: `\l`

### Model Download Issues
- Check internet connection
- Verify sufficient disk space (~500 MB for models + cache)
- If behind a proxy, configure `HTTP_PROXY` / `HTTPS_PROXY` environment variables

### API Key Issues
- Verify keys are correctly set in `.env` (no extra spaces or quotes)
- Check API quotas in [Google Cloud Console](https://console.cloud.google.com/apis/dashboard)
- YouTube/Books API has a daily quota — if exceeded, the system falls back to generated content

### `psycopg2` Installation Fails
The project uses `psycopg2-binary` which comes with pre-compiled binaries. If it fails, make sure you're using a compatible Python version or try installing PostgreSQL development headers for your OS.

### Port Already in Use
```bash
# Change the port in app.py, or kill the process using port 5000:
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux:
lsof -i :5000
kill -9 <PID>
```

---

## 👤 Author

[LekhyaBiridepalli](https://github.com/LekhyaBiridepalli)

---

## 📄 License

This project is licensed under the MIT License.

---

**Last Updated**: May 2026
