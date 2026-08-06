# 🤖 Local Behavioral Agent — Setup Guide

The **Fake Productivity Detector Local Behavioral Agent** is a lightweight desktop background process that passively captures behavioral metadata to generate daily **authenticity scores** — an alternative data source alongside the existing manual-entry and CSV-upload modes.

> ⚠️ **Privacy-First Design**
> The agent captures **ONLY**:
> - Keystroke **timing** intervals (never *which* keys)
> - Mouse movement **vectors** (never click targets or on-screen content)
> - Active window **titles** only (never window content)
>
> Raw events are stored **only on your local machine** and are **never** sent over the network. Only the daily aggregated score and summary statistics are synced to the backend.

---

## 📋 Prerequisites

- **Python 3.11+** installed on your machine
- **pip** (Python package manager)
- The FPD backend running (locally or on a server)
- A Supabase-authenticated FPD account

---

## 🚀 Installation

### 1. Install Python Dependencies

From the project root, install the agent's dependencies:

```bash
cd backend
pip install -r requirements.txt
```

The agent additionally uses these optional libraries for capture:

| Library | Platform | Purpose |
|---------|----------|---------|
| `pynput` | All | Keystroke timing & mouse movement capture |
| `pywin32` | Windows only | Active window title detection |
| `pygetwindow` | Mac only | Active window title fallback |
| `python-xlib` | Linux only | Active window title via X11 |

Install them as needed:

```bash
# All platforms
pip install pynput

# Windows
pip install pywin32

# Mac
pip install pygetwindow

# Linux
pip install python-xlib
```

### 2. Configure the Agent

Create a configuration file at `~/.fpd-agent/config.json`:

```bash
mkdir -p ~/.fpd-agent
```

Example configuration:

```json
{
  "sync_interval_hours": 24,
  "backend_url": "http://localhost:8000",
  "api_key": "your-supabase-anon-key-here",
  "user_id": "your-supabase-user-uuid-here",
  "opt_out": false,
  "last_sync_date": null
}
```

| Field | Description |
|-------|-------------|
| `backend_url` | URL of the FPD backend (default: `http://localhost:8000`) |
| `api_key` | Your Supabase anon key (from Settings → API) |
| `user_id` | Your Supabase user UUID (from your profile page) |
| `sync_interval_hours` | How often to sync aggregated data (default: 24h) |
| `opt_out` | Set to `true` to disable capture entirely |

### 3. Run the Agent

#### Daemon Mode (background)

```bash
cd backend
python -m app.agent.run_agent
```

Press `Ctrl+C` to stop.

#### With Options

```bash
# Run with custom user ID and backend URL
python -m app.agent.run_agent \
    --user-id "your-uuid-here" \
    --backend-url "http://localhost:8000" \
    --api-key "your-anon-key"

# Run one-time sync and exit (useful for cron jobs)
python -m app.agent.run_agent --sync-only

# Check agent status
python -m app.agent.run_agent --status

# Opt out of telemetry capture
python -m app.agent.run_agent --opt-out
```

---

## 🧠 How It Works

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR MACHINE                          │
│                                                         │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │ Keystroke    │   │ Mouse        │   │ Window Title  │  │
│  │ Timing       │   │ Movement     │   │ Polling       │  │
│  │ (pynput)     │   │ (pynput)     │   │ (win32gui/   │  │
│  └──────┬───────┘   └──────┬───────┘   │  X11/etc.)   │  │
│         │                  │           └──────┬───────┘  │
│         └──────────────────┴──────────────────┘          │
│                            │                             │
│                    ┌───────▼────────┐                    │
│                    │  SQLite Store   │                    │
│                    │  (raw events)   │                    │
│                    └───────┬────────┘                    │
│                            │                             │
│                    ┌───────▼────────┐                    │
│                    │  Feature       │ ← runs daily       │
│                    │  Extraction    │                    │
│                    └───────┬────────┘                    │
│                            │                             │
│                    ┌───────▼────────┐                    │
│                    │  Authenticity  │                    │
│                    │  Scorer        │                    │
│                    └───────┬────────┘                    │
│                            │                             │
│                    ╔═══════╧════════╗                    │
│                    ║  ONCE DAILY:   ║                    │
│                    ║  POST summary  ║────────────────────►── FPD Backend
│                    ║  to /agent/sync║                    │
│                    ╚════════════════╝                    │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Real-time capture**: The agent listens for keystroke timing events, mouse movements, and polls the active window title every 5 seconds.
2. **Local SQLite storage**: Raw events are stored in `~/.fpd-agent/agent_events.db` — **never sent over the network**.
3. **Daily aggregation**: At the configured interval (default: every 24 hours), the agent:
   - Extracts statistical features from the raw events
   - Computes an **authenticity score** (0–100) using a weighted formula
   - Generates summary statistics (averages, variances, window time breakdown)
4. **Sync**: POSTs **only** the aggregated score + summary stats to the backend endpoint `/api/v1/agent/sync`. Raw events remain local.
5. **Retention**: Raw events older than 14 days are automatically purged.

---

## 📊 What the Authenticity Score Measures

The authenticity scorer evaluates **six dimensions** of behavioral data:

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| Typing Variance | 25% | Consistency of typing rhythm (low variance = natural) |
| Typing Speed | 15% | Is the inter-key interval in human range? |
| Pause Ratio | 20% | Proportion of idle gaps > 2 seconds |
| Mouse Naturalness | 15% | Is mouse velocity variability human-like? |
| Window Quality | 20% | How much time is spent in productive vs distracting apps? |
| Activity Volume | 5% | How much data was captured (confidence multiplier) |

The score uses the **same category thresholds** as the main productivity scorer:

| Category | Score Range | Description |
|----------|-------------|-------------|
| 🏆 Highly Authentic | 80–100 | Natural behavioral patterns, productive app usage |
| 📈 Moderately Authentic | 50–79 | Adequate patterns with some idle/distraction |
| ⚠️ Low Authenticity | 0–49 | Erratic patterns, heavy distraction, or insufficient data |

---

## 🔐 Privacy & Security

### What the Agent Captures ✓

- **Keystroke timing** — Time between key presses (inter-key intervals in milliseconds). Never *which* key was pressed.
- **Mouse movement vectors** — X/Y coordinates at each movement event. Never click targets or on-screen element content.
- **Active window titles** — The title bar text of the foreground window (e.g., "Visual Studio Code — main.tsx"). Never the document content.

### What the Agent NEVER Captures ✗

- Screen captures, screenshots, or recordings
- Webcam or microphone access
- Actual keystroke characters or typed content
- Email content, file contents, or document text
- Passwords, credit card numbers, or personal information
- Click targets or on-screen element content
- Browser history, URLs, or page content

### Data Storage

- **Raw events**: Stored only in `~/.fpd-agent/agent_events.db` on your local machine
- **Daily aggregated data**: The only data sent to the backend — never raw events
- **Retention**: Raw events older than 14 days are automatically deleted
- **No internet required**: The agent works fully offline locally; only the daily sync needs connectivity

### Opt-Out

You can stop the agent at any time by running:

```bash
python -m app.agent.run_agent --opt-out
```

Or simply delete `~/.fpd-agent/config.json` and stop the process.

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `pynput` not installed | Run `pip install pynput` |
| Window title detection not working | Install platform-specific library (see above) |
| Sync fails with 401 | Check your `api_key` in `~/.fpd-agent/config.json` |
| Sync fails with 404 | Ensure the backend is running and the `/agent/sync` route is mounted |
| "No data to sync" | The agent needs at least some keystroke or mouse events to generate a score |
| Permission denied on Linux | You may need to run with `sudo` for global input monitoring |
| High CPU usage | The agent is designed to be lightweight (~0.1% CPU). If high, check for conflicting input monitoring software |

---

## 📝 Cron Job Setup (Alternative to Daemon Mode)

If you prefer not to run the agent as a background process, set up a cron job that runs the sync periodically:

```bash
# Run every hour (macOS/Linux)
0 * * * * cd /path/to/backend && python -m app.agent.run_agent --sync-only

# On Windows, use Task Scheduler to run:
python -m app.agent.run_agent --sync-only
```

---

## 🔄 Integration with FPD Dashboard

Once the agent has synced data, you can view it on the **Agent Monitor** page in the FPD web dashboard, which shows:

- Daily authenticity score with an animated score ring
- Window category time breakdown (pie chart)
- Authenticity score trend over time (line chart)
- Today's behavioral stats (typing speed, mouse velocity)
- Full privacy transparency notice

The data flows into the same Supabase-authenticated pipeline as the existing manual and CSV modes, enabling holistic productivity insights.