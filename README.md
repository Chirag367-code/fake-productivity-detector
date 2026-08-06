# 🚀 Fake Productivity Detector

> **Academic Project** • Data Science & Web Technologies • Full-Stack Application

A modern web application that analyzes and classifies productivity data using a weighted scoring algorithm with optional Machine Learning classification. Features real Supabase authentication (Google OAuth + email/password), batch CSV processing, interactive Recharts visualizations, and a beautiful glassmorphism UI.

![Version](https://img.shields.io/badge/version-2.0-blue)
![React](https://img.shields.io/badge/React-18.3-61dafb)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6)
![Tailwind](https://img.shields.io/badge/Tailwind-4-38bdf8)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688)
![Supabase](https://img.shields.io/badge/Supabase-2.98-3ECF8E)
![Python](https://img.shields.io/badge/Python-3.11-3776AB)
![GitHub stars](https://img.shields.io/github/stars/Chirag367-code/-Fake-Productivity-Detector-Using-Data-Science-?style=social)
![GitHub forks](https://img.shields.io/github/forks/Chirag367-code/-Fake-Productivity-Detector-Using-Data-Science-?style=social)
![GitHub issues](https://img.shields.io/github/issues/Chirag367-code/-Fake-Productivity-Detector-Using-Data-Science-)
![License](https://img.shields.io/github/license/Chirag367-code/-Fake-Productivity-Detector-Using-Data-Science-)

---

## ✨ Features

### 🎯 Core Functionality
- **🔐 Real Authentication** — Google OAuth & email/password via Supabase Auth with email confirmation flow
- **📥 Dual Input Methods** — Manual single-entry form & CSV batch upload with drag & drop
- **🧠 Smart Scoring Algorithm** — Weighted formula (0–100) with 3-tier classification
- **🤖 ML Integration** — Optional Random Forest classifier for enhanced detection (auto-trained on startup)
- **🏷️ Category Classification** — Highly Productive / Moderately Productive / Fake Productivity
- **💡 Personalized Suggestions** — AI-powered improvement recommendations based on analysis
- **📊 Data Persistence** — Supabase PostgreSQL with Row-Level Security (RLS)
- **📤 Export Capabilities** — Download reports as CSV and TXT
- **🧹 Data Preprocessing** — Automated cleaning, validation, and normalization
- **🔍 Comprehensive Reporting** — Filterable tables with search, sort, and export
- **❤️ Health Monitoring** — API health checks, auto-healing, and comprehensive logging
- **🤖 Local Behavioral Agent** — Lightweight desktop background process capturing passive behavioral metadata (keystroke timing, mouse vectors, window titles) for daily authenticity scoring — privacy-first, raw events never leave your machine

### 🎨 User Interface
- **🪟 Glassmorphism Design** — Modern frosted glass effects with backdrop blur
- **📱 Animated Sidebar** — 7-page navigation with collapsible sidebar & mobile drawer
- **📈 Interactive Charts** — Pie, Bar, Line charts using Recharts
- **📐 Responsive Layout** — Mobile-first design supporting all screen sizes
- **✨ Smooth Animations** — Motion (React) powered transitions, micro-interactions, and page entrances
- **🔄 Loading States** — Professional skeleton loaders and animated spinners
- **📂 Drag & Drop** — Intuitive CSV upload with visual feedback
- **✅ Form Validation** — Real-time validation with live password strength check
- **🌓 Dark/Light Theme Support** — Theme switching framework (ready for toggle implementation)

### 📊 Pages

| Page | Route | Description |
|------|-------|-------------|
| 📊 **Dashboard** | `dashboard` | Overview cards, stats, Pie/Bar/Line charts |
| 📂 **Upload CSV** | `upload` | Drag & drop CSV upload with batch analysis |
| ✍️ **Manual Analysis** | `manual` | Single entry form with instant results & export |
| 📄 **Reports** | `reports` | Filterable table with stats summary & CSV export |
| 📜 **History** | `history` | Timeline view with trend chart & delete option |
| 🤖 **Agent Monitor** | `agent` | Behavioral authenticity tracking from local agent |
| 👤 **Profile** | `profile` | User info, total analyses, average & best scores |

---

## 🛠️ Tech Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.3.1 | UI framework |
| TypeScript | 5.x | Type safety |
| Vite | 6.3.5 | Build tool & dev server |
| Tailwind CSS | 4.1.12 | Utility-first CSS framework |
| Motion (React) | 12.23.24 | Animation library |
| Recharts | 2.15.2 | Data visualization |
| Lucide React | 0.487.0 | Icon library |
| @supabase/supabase-js | 2.98.0 | Supabase client (auth + DB) |
| tw-animate-css | 1.3.8 | Tailwind animation utilities |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11 | Runtime environment |
| FastAPI | 0.109.2 | Web framework |
| Uvicorn | 0.27.1 | ASGI server |
| Pydantic | 2.6.1 | Data validation |
| Supabase Client | 2.27.3 | Database & Auth |
| Pandas | 2.2.0 | Data processing |
| NumPy | 1.26.4 | Numerical computing |
| Scikit-learn | 1.4.0 | ML classification (Random Forest, Logistic Regression, Decision Tree) |
| Joblib | 1.3.2 | Model serialization |
| HTTPX | 0.26.0 | HTTP client |
| AIOHTTP | 3.9.3 | Async HTTP client |
| Python-JOSE | 3.3.0 | JWT handling |
| Python-Dotenv | 1.0.1 | Environment variables |
| pynput | 1.7.6 | Keystroke timing & mouse capture (agent) |
| pywin32 | 306 | Active window title detection (Windows agent) |

### Infrastructure

| Service | Purpose |
|---------|---------|
| **Supabase** | PostgreSQL database + Authentication (Google OAuth, email/password) |
| **Docker** | Containerized backend deployment |
| **Vercel** | Monorepo deployment (frontend + backend rewrites) |

---

## 📐 Productivity Algorithm

### Scoring Formula

```javascript
score = (taskHours × 8) + (tasksCompleted × 5)
        - (idleHours × 6) - (socialMediaHours × 7)
        - (breakFrequency × 2)

// Normalized: 0 ≤ score ≤ 100
```

### Weight Rationale

| Metric | Weight | Impact | Reason |
|--------|--------|--------|--------|
| Task Hours | **+8** | Strong positive | Core productive time |
| Tasks Completed | **+5** | Moderate positive | Output measurement |
| Idle Hours | **−6** | Strong negative | Wasted time |
| Social Media Hours | **−7** | Strongest negative | Distraction indicator |
| Break Frequency | **−2** | Mild negative | Context switching cost |

### Classification Thresholds

| Category | Score Range | Description |
|----------|-------------|-------------|
| 🏆 **Highly Productive** | 80–100 | Excellent focus and output |
| 📈 **Moderately Productive** | 50–79 | Adequate with room for improvement |
| ⚠️ **Fake Productivity** | 0–49 | Low actual output despite activity |

### Input Variables

1. **Task Hours** — Hours spent on productive work (weight: +8)
2. **Idle Hours** — Hours of unproductive downtime (weight: −6)
3. **Social Media Usage** — Time spent on social platforms (weight: −7)
4. **Break Frequency** — Number of breaks taken (weight: −2)
5. **Tasks Completed** — Number of tasks finished (weight: +5)

---

## 🤖 Machine Learning Integration

### Supported Models

| Model | Characteristics |
|-------|----------------|
| **Random Forest** 🌲 | Best overall accuracy (recommended) |
| **Logistic Regression** 📊 | Fast, interpretable baseline |
| **Decision Tree** 🌳 | Simple, explainable rules |

### Auto-Training on Startup

The backend automatically trains a Random Forest model with 1000 synthetic samples on first startup if no pre-trained model exists. No manual training needed!

### Manual Training

```bash
cd backend

# Default: Random Forest with 1000 synthetic samples
python -m app.ml.train_model

# Compare all model types
python -m app.ml.train_model --compare

# Train with custom CSV data
python -m app.ml.train_model --data path/to/training.csv

# Specific model with more samples
python -m app.ml.train_model --model logistic_regression --samples 5000
```

### Usage

- Automatically loads if `random_forest_model.joblib` exists in `app/ml/models/`
- Falls back to rule-based scoring if model unavailable
- Both rule-based and ML categories are returned in API responses

---

## 🚀 Getting Started

### Prerequisites

```bash
Node.js >= 18
npm (comes with Node.js)
Python 3.11+ (3.11 recommended)
Git
Supabase account (free tier)
```

### Quick Setup (Frontend)

```bash
# Clone the repository
git clone https://github.com/Chirag367-code/-Fake-Productivity-Detector-Using-Data-Science-.git
cd -Fake-Productivity-Detector-Using-Data-Science-

# Install frontend dependencies
npm install

# Set up environment variables
copy .env.example .env
# Edit .env with:
#   VITE_SUPABASE_URL=your_supabase_url
#   VITE_SUPABASE_ANON_KEY=your_anon_key

# Start the frontend dev server
npm run dev
# Opens at http://localhost:5173
```

### Supabase Setup

1. Create a new project at [supabase.com](https://supabase.com) (free tier)
2. Go to **SQL Editor** → **New Query** and paste the contents of `supabase/migration.sql`
3. Run the query — this creates the `users`, `productivity_records`, and `agent_authenticity_records` tables with RLS policies
4. Enable Google OAuth in **Authentication** → **Providers** → **Google** (configure with your Google Cloud Console credentials)
5. Copy your **Project URL** and **anon public key** from **Settings** → **API** into `.env`

> 📖 **Full authentication setup guide:** [AUTH_SETUP.md](AUTH_SETUP.md)

### Quick Setup (Backend)

```bash
# Option 1: Using Docker (easiest)
docker build -t fpd-backend .
docker run -p 8000:8000 --env-file backend/.env fpd-backend

# Option 2: Using Python venv (Windows)
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your Supabase credentials
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option 3: Using Conda (recommended for Windows)
conda env create -f environment.yml  # if available
conda activate fpd-env
cd backend
python -m app.main
```

### Environment Variables

**Frontend** (`.env` / `.env.example`):
```env
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_URL=http://localhost:8000  # optional, for local development
```

**Backend** (`backend/.env`):
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]

# Optional: Custom scoring weights
SCORE_TASK_HOURS_WEIGHT=8
SCORE_TASKS_COMPLETED_WEIGHT=5
SCORE_IDLE_HOURS_WEIGHT=6
SCORE_SOCIAL_MEDIA_WEIGHT=7
SCORE_BREAK_FREQUENCY_WEIGHT=2
```

### Build for Production

```bash
# Build frontend
npm run build

# Deploy to Vercel (auto-detects Vite + Python backend via vercel.json)
npx vercel --prod
```

---

## 📂 CSV Upload Guide

### Required Format

```csv
Task_Hours,Idle_Hours,Social_Media_Usage,Break_Frequency,Tasks_Completed
6,1,0.5,4,8
8,0.5,1,3,12
4,3,2,8,3
```

### Columns

| Column | Type | Description |
|--------|------|-------------|
| `Task_Hours` | float | Hours spent on productive tasks |
| `Idle_Hours` | float | Hours of unproductive time |
| `Social_Media_Usage` | float | Time spent on social platforms |
| `Break_Frequency` | int | Number of breaks taken |
| `Tasks_Completed` | int | Number of tasks finished |

### Usage

1. Click **Download Template** on the Upload CSV page
2. Edit the CSV with your data
3. Drag & drop or select the file
4. Click **Analyze CSV**
5. View results per row with color-coded categories
6. **Export Results** as CSV

> 📖 **Full CSV format guide:** [CSV_FORMAT_GUIDE.md](CSV_FORMAT_GUIDE.md)

---

## 🎓 Academic Context

### Perfect For Demonstrating:

- ✅ Data Science Algorithms (weighted scoring, ML classification)
- ✅ Full-Stack Web Development (React + FastAPI + Supabase)
- ✅ Modern UI/UX Design (glassmorphism, motion, responsive)
- ✅ RESTful API Integration (JWT auth, CRUD operations)
- ✅ CSV Data Processing (batch uploads, validation)
- ✅ Interactive Data Visualizations (Recharts Pie/Bar/Line)
- ✅ Authentication Flows (Google OAuth, email/password, email confirmation)
- ✅ Row-Level Security (Supabase RLS policies)

### Easy To Explain:

- Simple weighted scoring formula with clear input → process → output flow
- Progressive enhancement: rule-based → ML-based classification
- Real-world applicable: productivity tracking for students & professionals

---

## 📁 Project Structure

```
Fake-Productivity-Detector/
├── src/
│   ├── main.tsx                          # React entry point
│   │
│   ├── app/
│   │   ├── App.tsx                       # Root component, routing, auth guard
│   │   │
│   │   ├── components/
│   │   │   ├── ActivityInput.tsx         # Manual analysis input form
│   │   │   ├── Dashboard.tsx            # Legacy dashboard (single-page)
│   │   │   ├── LoginPage.tsx            # Auth page (Google + email/password)
│   │   │   ├── ProductivityHistory.tsx   # History timeline + trend chart
│   │   │   ├── ProductivityResults.tsx   # Analysis results w/ score ring
│   │   │   ├── ErrorBoundary.tsx        # React error boundary
│   │   │   ├── Sidebar.tsx              # Collapsible nav sidebar
│   │   │   └── pages/
│   │   │       ├── DashboardPage.tsx     # Main dashboard (stats + charts)
│   │   │       ├── UploadCSVPage.tsx     # CSV upload w/ drag & drop
│   │   │       ├── ManualAnalysisPage.tsx # Manual analysis page
│   │   │       ├── AgentMonitoringPage.tsx # Agent authenticity dashboard
│   │   │       ├── ReportsPage.tsx       # Reports w/ filters & export
│   │   │       ├── HistoryPage.tsx       # History page wrapper
│   │   │       ├── ProfilePage.tsx       # User profile + stats
│   │   │       └── CSVTemplate.tsx       # CSV template download button
│   │   │
│   │   ├── config/
│   │   │   └── api.ts                   # API config, endpoints, authFetch
│   │   │
│   │   └── context/
│   │       └── AuthContext.tsx           # Auth context provider (Supabase)
│   │
│   ├── lib/
│   │   ├── supabase.ts                  # Supabase client initialization
│   │   └── validation.ts               # Password validation utility
│   │
│   └── styles/
│       ├── index.css                     # Global styles
│       ├── tailwind.css                  # Tailwind imports
│       ├── theme.css                     # Theme variables
│       └── fonts.css                     # Font definitions
│
├── backend/
│   ├── README.md                        # Backend documentation
│   ├── requirements.txt                 # Python dependencies
│   ├── requirements-dev.txt             # Dev/testing dependencies
│   ├── .env.example                      # Backend env template
│   ├── run.bat                          # Windows run script
│   ├── test.csv                         # Sample CSV for testing
│   │
│   └── app/
│       ├── __init__.py
│       ├── main.py                      # FastAPI app entry, lifespan, health
│       ├── config.py                    # Settings (env vars, scoring weights)
│       │
│       ├── agent/                       # Local behavioral agent module
│       │   ├── __init__.py
│       │   ├── capture.py              # Keystroke/mouse/window capture
│       │   ├── feature_extraction.py   # Aggregate statistical features
│       │   ├── authenticity_scorer.py  # 0-100 authenticity scoring
│       │   ├── sync_client.py          # Daily sync to backend
│       │   └── run_agent.py            # CLI entry point
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── database.py             # Supabase CRUD operations
│       │   └── schemas.py              # Pydantic request/response models
│       │
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── agent.py                # POST /agent/sync, GET /agent/history
│       │   ├── analysis.py             # POST /analyze, GET /explain
│       │   ├── csv_upload.py           # POST /upload-csv, GET /template
│       │   ├── history.py              # GET/DELETE /history/{user_id}
│       │   └── reports.py              # GET /reports/{user_id}, /weekly
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── scoring.py              # Rule-based scoring algorithm
│       │   ├── ml_model.py             # ML classifier (Random Forest etc.)
│       │   ├── preprocessing.py        # Data cleaning & normalization
│       │   └── suggestions.py          # Improvement suggestion generator
│       │
│       ├── utils/
│       │   ├── __init__.py
│       │   └── csv_parser.py           # CSV parsing & validation
│       │
│       └── ml/
│           ├── __init__.py
│           └── train_model.py          # Model training script
│
├── supabase/
│   └── migration.sql                   # Full DB schema + RLS + triggers
│
├── index.html                           # Main HTML entry
├── package.json                         # Frontend dependencies & scripts
├── vite.config.ts                       # Vite configuration
├── tsconfig.json                        # TypeScript configuration
├── postcss.config.mjs                   # PostCSS / Tailwind config
├── Dockerfile                           # Backend Docker image
├── vercel.json                          # Vercel monorepo deployment config
├── .env.example                         # Frontend env template
├── .gitignore
├── AGENT_SETUP.md                       # Local behavioral agent setup guide
├── ATTRIBUTIONS.md                      # Third-party attributions
├── AUTH_SETUP.md                        # Detailed auth setup guide
├── CSV_FORMAT_GUIDE.md                  # CSV format reference
└── README.md                            # This file
```

---

## 🔌 API Endpoints

### Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root — welcome message |
| `GET` | `/health` | Health check |
| `GET` | `/info` | API information (version, features, scoring) |
| `POST` | `/analyze` | Analyze single entry & save to DB |
| `POST` | `/analyze/quick` | Quick score without saving |
| `GET` | `/analyze/explain` | Explain scoring formula |
| `POST` | `/upload-csv` | Upload & process CSV batch |
| `GET` | `/upload-csv/template` | Download CSV template |
| `POST` | `/upload-csv/validate` | Validate CSV structure |
| `GET` | `/history/{user_id}` | Get user analysis history |
| `DELETE` | `/history/{user_id}` | Delete user history |
| `GET` | `/history/{user_id}/stats` | Get history statistics |
| `GET` | `/history/{user_id}/trend` | Get history trend data |
| `GET` | `/reports/{user_id}` | Get comprehensive report |
| `GET` | `/reports/{user_id}/weekly` | Get weekly summary |
| `GET` | `/reports/{user_id}/comparison` | Get comparison data |
| `GET` | `/reports/{user_id}/export/csv` | Export reports as CSV |
| `POST` | `/agent/sync` | Sync daily agent authenticity score |
| `GET` | `/agent/history/{user_id}` | Get agent authenticity history |
| `GET` | `/agent/latest/{user_id}` | Get latest agent authenticity score |

### POST /analyze — Request

```json
{
  "user_id": "uuid-or-email",
  "activity_data": {
    "task_hours": 6.5,
    "tasks_completed": 8,
    "idle_hours": 1.5,
    "social_media_hours": 1.0,
    "break_frequency": 3
  },
  "use_ml_classification": true,
  "save_to_history": true
}
```

### POST /analyze — Response

```json
{
  "user_id": "user@example.com",
  "productivity_score": 78.5,
  "category_rule_based": "Moderately Productive",
  "category_ml": "Moderately Productive",
  "confidence_score": 0.87,
  "breakdown": {
    "task_hours": 6.5,
    "tasks_completed": 8,
    "idle_hours": 1.5,
    "social_media_hours": 1.0,
    "break_frequency": 3
  },
  "suggestions": [
    {
      "category": "task_hours",
      "priority": "medium",
      "suggestion": "Increase focused task time to boost productivity",
      "impact": "Could improve your score by 5-10 points"
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

> **Interactive API docs:** http://localhost:8000/docs (Swagger UI) | http://localhost:8000/redoc (ReDoc)

---

## 🗄️ Database Schema (Supabase)

### Table: `public.users`

Stores user profiles synced from Supabase Auth via trigger.

```sql
CREATE TABLE public.users (
  id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email       TEXT UNIQUE NOT NULL,
  full_name   TEXT,
  avatar_url  TEXT,
  provider    TEXT DEFAULT 'email',
  created_at  TIMESTAMPTZ DEFAULT now()
);
```

### Table: `public.productivity_records`

Stores every productivity analysis linked to a user.

```sql
CREATE TABLE public.productivity_records (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  task_hours          FLOAT NOT NULL,
  idle_hours          FLOAT NOT NULL,
  social_media_usage  FLOAT NOT NULL,
  break_frequency     INTEGER NOT NULL,
  tasks_completed     INTEGER NOT NULL,
  score               INTEGER NOT NULL,
  category            TEXT NOT NULL,
  created_at          TIMESTAMPTZ DEFAULT now()
);
```

### Table: `public.agent_authenticity_records`

Stores daily aggregated authenticity scores from the local behavioral agent.

```sql
CREATE TABLE public.agent_authenticity_records (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  date                DATE NOT NULL,
  authenticity_score  FLOAT NOT NULL CHECK (authenticity_score >= 0 AND authenticity_score <= 100),
  avg_typing_speed    FLOAT,
  avg_mouse_velocity  FLOAT,
  top_window_categories JSONB DEFAULT '[]'::jsonb,
  created_at          TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, date)
);
```

### Security

- **Row-Level Security (RLS)** enabled on all tables
- Users can only **SELECT**, **INSERT**, **UPDATE** (users), and **DELETE** their own records
- A database trigger (`handle_new_user`) automatically creates a profile row when a user signs up

> **Full migration SQL:** [`supabase/migration.sql`](supabase/migration.sql)

---

## 🎨 Design System

### Colors

```css
/* Primary palette */
Blue:     #3b82f6    /* Primary actions, links */
Purple:   #8b5cf6    /* Secondary, gradients */
Pink:     #ec4899    /* Accent */

/* Semantic colors */
Green:    #10b981    /* Highly Productive / Success */
Yellow:   #f59e0b    /* Moderately Productive / Warning */
Red:      #ef4444    /* Fake Productivity / Danger */
```

### UI Components

- **Glassmorphism cards** — `backdrop-blur-lg bg-white/70 border border-white/50 rounded-2xl shadow-xl`
- **Gradient buttons** — `bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700`
- **Color-coded badges** — Green/Yellow/Red based on productivity category
- **Animated backgrounds** — Floating blob animations with `mix-blend-multiply` and `blur-xl`

### Typography

```css
/* System fonts */
font-family: Inter, SF Pro, Segoe UI, system-ui, sans-serif;
```

- **Headings:** `text-2xl` / `text-3xl` with `font-semibold` (600 weight)
- **Body:** `text-sm` / `text-base` with `font-normal` (400 weight)
- **Numbers/Stats:** Larger displays with bold weight

### Animations

| Element | Type | Duration | Easing |
|---------|------|----------|--------|
| Page entrances | Fade + slide (y) | 300–500ms | easeOut |
| Score ring | Circle progress draw | 1.5s | easeOut |
| Sidebar items | Staggered fade + slide (x) | 50ms delay each | easeOut |
| Hover effects | Scale 1.02x + shadow | 300ms | ease |
| Background blobs | Floating morph | 7s infinite | ease-in-out |
| Loading spinner | Infinite rotation | 1s linear | linear |

---

## 🎯 Use Cases

### For Students 🎓
- Track daily study productivity
- Identify time-wasting patterns
- Improve focus and efficiency
- Generate progress reports

### For Professionals 💼
- Monitor work habits
- Optimize productivity
- Reduce distractions
- Track performance metrics

### For Teams 👥
- Batch analyze team data
- Compare productivity trends
- Identify improvement areas
- Generate team reports

---

## 🔮 Future Enhancements

### Planned Features
- [x] Real Google OAuth integration (Supabase Auth)
- [x] Machine Learning classification (Random Forest)
- [x] Local Behavioral Agent (passive authenticity scoring)
- [ ] PDF report generation
- [ ] Email notifications & summaries
- [ ] Dark mode toggle
- [ ] Multi-language support (i18n)
- [ ] Team collaboration & sharing
- [ ] Productivity goals & streaks
- [ ] Weekly/Monthly email summaries
- [ ] Mobile PWA support

---

## 🐛 Known Issues

- CSV files must use **comma** delimiters (not semicolons)
- Large CSV files (1,000+ rows) may take a few seconds to process
- Email confirmation required for email sign-up (Supabase default)
- ML model auto-training runs on backend startup (adds ~5–10s to first boot)
- Agent requires `pynput` and platform-specific window title libraries

---

## 🤝 Contributing

This is an academic project, but contributions are welcome!

### Git Workflow

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create** a feature branch:
   ```bash
   git checkout -b feature/AmazingFeature
   ```
4. **Make** your changes and commit:
   ```bash
   git add .
   git commit -m 'Add some AmazingFeature'
   ```
5. **Push** to your branch:
   ```bash
   git push origin feature/AmazingFeature
   ```
6. **Open** a Pull Request on GitHub

### Branch Naming Convention

- `feature/feature-name` — New features
- `bugfix/bug-description` — Bug fixes
- `docs/documentation-update` — Documentation changes
- `refactor/code-improvement` — Code refactoring

### Development Guidelines

- Follow the existing code style and TypeScript conventions
- Add proper error handling and loading states for new features
- Update documentation as needed
- Ensure all components handle loading, empty, and error states

---

## 📄 License

This project is for **academic purposes**. See [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Chirag Chavan** — [@Chirag367-code](https://github.com/Chirag367-code)

Academic project demonstrating Data Science & Full-Stack Web Development.

---

## 🙏 Acknowledgments

- **React team** — For the amazing UI framework
- **Tailwind CSS** — For the utility-first approach
- **FastAPI** — For the modern Python web framework
- **Supabase** — For the excellent backend infrastructure (Auth + DB)
- **Recharts** — For the composable charting library
- **Motion** — For the powerful animation primitives
- **Vercel** — For inspiration on modern UI/UX patterns

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [AGENT_SETUP.md](AGENT_SETUP.md) | Local behavioral agent setup & privacy guide |
| [AUTH_SETUP.md](AUTH_SETUP.md) | Detailed Supabase authentication setup guide |
| [CSV_FORMAT_GUIDE.md](CSV_FORMAT_GUIDE.md) | CSV structure, columns, and examples |
| [ATTRIBRIBUTIONS.md](ATTRIBUTIONS.md) | Third-party attributions and licenses |
| [backend/README.md](backend/README.md) | Backend-specific documentation |

---

## ⭐ Support

If you find this project helpful, please give it a star! ⭐

For questions or issues:
- 🐛 **Issues:** [GitHub Issues](https://github.com/Chirag367-code/-Fake-Productivity-Detector-Using-Data-Science-/issues)
- 🐙 **GitHub:** [@Chirag367-code](https://github.com/Chirag367-code)

---

**Made with ❤️ for Academic Excellence**

*Demonstrating the power of Data Science, Modern Web Technologies, and Beautiful UI/UX Design*