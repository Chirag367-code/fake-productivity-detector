# Fake Productivity Detector - Backend

## Academic Project: Fake Productivity Detector Using Data Science

Python FastAPI backend with Supabase integration and ML-based productivity classification.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Productivity Formula](#productivity-formula)
- [Machine Learning](#machine-learning)
- [Database Schema](#database-schema)
- [Configuration](#configuration)
- [Testing](#testing)
- [Deployment](#deployment)

---

## Overview

This backend provides REST APIs for the Fake Productivity Detector application. It analyzes user activity metrics (task hours, tasks completed, idle hours, social media usage, break frequency) and classifies productivity levels using both rule-based scoring and machine learning.

### Features

- ✅ Rule-based productivity scoring with configurable weights
- ✅ ML classification (Logistic Regression, Random Forest, Decision Tree)
- ✅ Single and batch (CSV) analysis endpoints
- ✅ User history management with Supabase
- ✅ Comprehensive analytics and reports
- ✅ Personalized improvement suggestions
- ✅ RESTful API with OpenAPI documentation

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Language** | Python 3.11 |
| **Framework** | FastAPI |
| **Database** | Supabase (PostgreSQL) |
| **ML Libraries** | Scikit-learn, Pandas, NumPy |
| **Validation** | Pydantic |
| **Server** | Uvicorn |

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration settings
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py      # Supabase client & CRUD
│   │   └── schemas.py       # Pydantic models
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── analysis.py      # Single analysis endpoints
│   │   ├── csv_upload.py    # CSV batch processing
│   │   ├── history.py       # History management
│   │   └── reports.py       # Analytics reports
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scoring.py       # Rule-based scoring
│   │   ├── ml_model.py      # ML classification
│   │   ├── preprocessing.py # Data preprocessing
│   │   └── suggestions.py   # Improvement suggestions
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── csv_parser.py    # CSV parsing utilities
│   │
│   └── ml/
│       ├── __init__.py
│       ├── train_model.py   # Training script
│       └── models/          # Saved models (gitignored)
│
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- pip or conda
- Supabase project (free tier works)

---

### Installation (Recommended: Conda)

**If you are on Windows and see errors about building `pandas` or `numpy`, use this method!**

1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Anaconda](https://www.anaconda.com/products/distribution).
2. In the project root, run:
  ```powershell
  conda env create -f environment.yml
  conda activate fpd-env
  cd backend
  python -m app.main
  ```

---

### Alternative: venv + pip (Windows, requires C++ Build Tools)

1. Install [Build Tools for Visual Studio](https://aka.ms/vs/17/release/vs_BuildTools.exe)
  - Select "Desktop development with C++" workload during install.
2. In the backend folder, run:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  python -m app.main
  ```

---

### Common Troubleshooting

- **Build errors for pandas/numpy/scikit-learn:**
  - Use the Conda method above for a smoother experience.
  - If you must use pip, ensure you have the Visual Studio Build Tools installed (see above).

---

### Configure environment
```powershell
cp .env.example .env
# Edit .env with your Supabase credentials
```

---

### Run the server
```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### Open API documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Train ML Model (Optional)

```powershell
# Train with synthetic data
python -m app.ml.train_model --samples 1000 --model random_forest

# Compare all models
python -m app.ml.train_model --compare

# Train with custom CSV
python -m app.ml.train_model --data path/to/training.csv
```

---

## API Reference

### Base URL

```
http://localhost:8000/api/v1
```

### Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analysis/analyze` | Analyze single entry |
| `POST` | `/analysis/analyze/quick` | Quick score without saving |
| `GET` | `/analysis/explain` | Explain scoring formula |
| `POST` | `/csv/upload-csv` | Upload and process CSV |
| `GET` | `/csv/template` | Get CSV template |
| `POST` | `/csv/validate` | Validate CSV structure |
| `GET` | `/history/{user_id}` | Get user history |
| `DELETE` | `/history/{user_id}` | Delete user history |
| `GET` | `/history/{user_id}/stats` | Get history statistics |
| `GET` | `/reports/{user_id}` | Get analytics report |
| `GET` | `/reports/{user_id}/weekly` | Get weekly report |

---

### POST /analysis/analyze

Analyze productivity data and save to database.

**Request Body:**
```json
{
  "user_id": "user@example.com",
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

**Response:**
```json
{
  "user_id": "user@example.com",
  "productivity_score": 78.5,
  "category_rule_based": "Moderately Productive",
  "category_ml": "Moderately Productive",
  "confidence_score": 0.87,
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

---

### POST /csv/upload-csv

Upload and analyze CSV file with multiple productivity entries.

**Request:**
- `file`: CSV file (multipart/form-data)
- `user_id`: User identifier

**CSV Format:**
```csv
task_hours,tasks_completed,idle_hours,social_media_hours,break_frequency
6.5,8,1.5,1.0,3
7.0,10,1.0,0.5,2
```

**Response:**
```json
{
  "user_id": "user@example.com",
  "total_records": 10,
  "processed": 10,
  "failed": 0,
  "summary": {
    "average_score": 72.5,
    "category_distribution": {
      "Highly Productive": 3,
      "Moderately Productive": 5,
      "Fake Productivity": 2
    }
  },
  "results": [...]
}
```

---

### GET /history/{user_id}

Retrieve productivity history for a user.

**Parameters:**
- `user_id`: User identifier (path)
- `limit`: Max records (query, default: 100)
- `offset`: Skip records (query, default: 0)

**Response:**
```json
{
  "user_id": "user@example.com",
  "total_records": 25,
  "history": [
    {
      "id": "uuid",
      "productivity_score": 78.5,
      "category_rule_based": "Moderately Productive",
      "task_hours": 6.5,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

### GET /reports/{user_id}

Generate comprehensive analytics report.

**Parameters:**
- `user_id`: User identifier (path)
- `days`: Days to analyze (query, default: 30)

**Response:**
```json
{
  "user_id": "user@example.com",
  "period_days": 30,
  "summary": {
    "total_analyses": 25,
    "average_score": 68.5,
    "median_score": 70.0,
    "min_score": 45.0,
    "max_score": 92.0
  },
  "category_distribution": {
    "Highly Productive": {"count": 5, "percentage": 20.0},
    "Moderately Productive": {"count": 15, "percentage": 60.0},
    "Fake Productivity": {"count": 5, "percentage": 20.0}
  },
  "trend": {
    "direction": "improving",
    "change": 5.2
  },
  "suggestions": [...]
}
```

---

## Productivity Formula

### Scoring Calculation

```
Raw Score = (Task Hours × 8) 
          + (Tasks Completed × 5) 
          - (Idle Hours × 6) 
          - (Social Media Hours × 7) 
          - (Break Frequency × 2)

Final Score = max(0, min(100, Raw Score))
```

### Weight Rationale

| Metric | Weight | Impact |
|--------|--------|--------|
| Task Hours | +8 | Strong positive: Core productive time |
| Tasks Completed | +5 | Moderate positive: Output measurement |
| Idle Hours | -6 | Strong negative: Wasted time |
| Social Media Hours | -7 | Strongest negative: Distraction indicator |
| Break Frequency | -2 | Mild negative: Context switching cost |

### Classification Thresholds

| Category | Score Range | Description |
|----------|-------------|-------------|
| **Highly Productive** | 80-100 | Excellent focus and output |
| **Moderately Productive** | 50-79 | Adequate with room for improvement |
| **Fake Productivity** | 0-49 | Low actual output despite activity |

---

## Machine Learning

### Supported Models

1. **Logistic Regression** - Fast, interpretable baseline
2. **Random Forest** - Best overall accuracy (recommended)
3. **Decision Tree** - Simple, explainable rules

### Training Pipeline

```python
# 1. Load or generate training data
data = generate_synthetic_data(n_samples=1000)

# 2. Preprocess features
preprocessor = DataPreprocessor()
processed_df = preprocessor.preprocess(data)

# 3. Train classifier
classifier = MLClassifier(model_type='random_forest')
classifier.train(X_train, y_train)

# 4. Save model
classifier.save_model('models/random_forest_model.joblib')
```

### Training Commands

```powershell
# Default: Random Forest with 1000 synthetic samples
python -m app.ml.train_model

# Compare all model types
python -m app.ml.train_model --compare

# Custom training data
python -m app.ml.train_model --data training_data.csv

# Specific model with more samples
python -m app.ml.train_model --model logistic_regression --samples 5000
```

---

## Database Schema

### Table: `productivity_analysis`

```sql
CREATE TABLE productivity_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    productivity_score FLOAT NOT NULL,
    category_rule_based TEXT NOT NULL,
    category_ml TEXT,
    confidence_score FLOAT,
    task_hours FLOAT,
    tasks_completed INTEGER,
    idle_hours FLOAT,
    social_media_hours FLOAT,
    break_frequency INTEGER,
    suggestions JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_user_id ON productivity_analysis(user_id);
CREATE INDEX idx_created_at ON productivity_analysis(created_at DESC);
```

### Supabase Setup

1. Create new Supabase project at https://supabase.com
2. Go to SQL Editor and run the schema above
3. Copy project URL and anon key to `.env`

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SUPABASE_URL` | Yes | - | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | - | Supabase anon/public key |
| `ENVIRONMENT` | No | development | Environment name |
| `DEBUG` | No | true | Enable debug mode |
| `CORS_ORIGINS` | No | localhost:* | Allowed CORS origins |
| `API_HOST` | No | 0.0.0.0 | API host binding |
| `API_PORT` | No | 8000 | API port |

### Configuration Override

Scoring weights can be customized in `.env`:

```env
SCORE_TASK_HOURS_WEIGHT=8
SCORE_TASKS_COMPLETED_WEIGHT=5
SCORE_IDLE_HOURS_WEIGHT=6
SCORE_SOCIAL_MEDIA_WEIGHT=7
SCORE_BREAK_FREQUENCY_WEIGHT=2
```

---

## Testing

### Run Tests

```powershell
# All tests
pytest

# With coverage
pytest --cov=app

# Specific test file
pytest tests/test_scoring.py

# Verbose output
pytest -v
```

### Test Structure

```
tests/
├── test_scoring.py       # Scoring service tests
├── test_ml_model.py      # ML classification tests
├── test_csv_parser.py    # CSV parsing tests
└── test_api.py           # API endpoint tests
```

---

## Deployment

### Production Checklist

1. Set `DEBUG=false`
2. Set `ENVIRONMENT=production`
3. Restrict `CORS_ORIGINS` to frontend domain
4. Use environment variables for all secrets
5. Pre-train and include ML model file
6. Set up logging and monitoring

### Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Common Deployment Platforms

- **Railway**: `railway up`
- **Render**: Connect GitHub repo
- **Heroku**: Use Procfile
- **DigitalOcean App Platform**: Auto-detect Python

---

## API Documentation

When the server is running, access interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## Support

For issues or questions related to this academic project, please refer to the project documentation or contact the project maintainer.

---

## License

MIT License - Academic Project
