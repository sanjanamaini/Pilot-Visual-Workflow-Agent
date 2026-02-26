# 🧭 Pilot — The Universal Visual Workflow Agent

> **AI agent that watches your screen, understands your intent, and executes multi-step workflows across any web application — using only visual understanding.**

[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Ready-4285F4?logo=google-cloud)](https://cloud.google.com)
[![Gemini](https://img.shields.io/badge/Gemini%203.1%20Pro-Powered-8E75B2?logo=google)](https://ai.google.dev)
[![Chrome Extension](https://img.shields.io/badge/Chrome-Extension-4285F4?logo=google-chrome)](https://developer.chrome.com/docs/extensions/)

---

## 🎯 What is Pilot?

Knowledge workers lose 3–5 hours daily to repetitive, cross-application busywork. Pilot fixes this.

> *"Move this lead to 'Proposal Sent' in our CRM, draft a follow-up email, and add a task to follow up in 3 days."*

One sentence. Pilot does all three. Across three different apps. **No API keys. No integrations. No setup.** Just vision + action.

---

## 🏗️ Architecture

```
┌─────────────────────────────┐
│     Chrome Extension        │
│  (React Side Panel)         │
│                             │
│  ┌──────────┐ ┌───────────┐ │
│  │ Command  │ │  Action   │ │
│  │   Bar    │ │   Feed    │ │    Screenshots     Actions
│  └──────────┘ └───────────┘ │◄──────────────────────────────┐
│                             │                                │
│  ┌──────────────────────┐   │     WebSocket                  │
│  │ Background Worker    │───┼────────────────┐               │
│  │ (Screenshot+Execute) │   │                │               │
│  └──────────────────────┘   │                ▼               │
└─────────────────────────────┘     ┌──────────────────────┐   │
                                    │   FastAPI Backend     │   │
                                    │                      │   │
                                    │  ┌────────────────┐  │   │
                                    │  │  Interpreter   │  │   │
                                    │  │  (Gemini 3.1)  │  │   │
                                    │  └───────┬────────┘  │   │
                                    │          ▼           │   │
                                    │  ┌────────────────┐  │   │
                                    │  │    Planner     │  │   │
                                    │  └───────┬────────┘  │   │
                                    │          ▼           │   │
                                    │  ┌────────────────┐  │   │
                                    │  │  Action Agent  │──┼───┘
                                    │  └───────┬────────┘  │
                                    │          ▼           │
                                    │  ┌────────────────┐  │
                                    │  │   Verifier     │  │
                                    │  └───────┬────────┘  │
                                    │          ▼           │
                                    │  ┌────────────────┐  │
                                    │  │   Narrator     │  │
                                    │  └────────────────┘  │
                                    └──────────────────────┘
```

---

## ⚡ Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Google Chrome**
- **Gemini API Key** → [Get one free](https://aistudio.google.com/apikey)

### 1. Backend Setup

```bash
cd pilot/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set your API key
set GOOGLE_API_KEY=your_key_here       # Windows
# export GOOGLE_API_KEY=your_key_here  # macOS/Linux

# Start the server
python main.py
```

The backend will start on **http://localhost:8000**. Verify:
```bash
curl http://localhost:8000/health
```

### 2. Extension Setup

```bash
cd pilot/extension

# Install dependencies
npm install

# Build the extension
npm run build
```

### 3. Load in Chrome

1. Open **chrome://extensions/**
2. Enable **Developer Mode** (top right)
3. Click **"Load unpacked"** → select `pilot/extension/dist/`
4. Click the **Pilot icon** in your toolbar to open the side panel
5. The green dot means you're connected to the backend

### 4. Try It!

1. Open any web page (start with something simple like Google)
2. Type a command: *"Click the search button"*
3. Watch Pilot analyze the screen, create a plan, and execute it

---

## 🧪 Demo Ideas

| Command | App |
|---|---|
| *"Search for 'AI agents' and click the first result"* | Google |
| *"Create a new document called 'Meeting Notes'"* | Google Docs |
| *"Move this card to the 'Done' column"* | Trello |
| *"Update the lead status to 'Qualified'"* | Salesforce |

---

## 📁 Project Structure

```
pilot/
├── backend/                    # Python FastAPI server
│   ├── main.py                 # WebSocket + REST endpoints
│   ├── gemini_client.py        # Gemini 3.1 Pro wrapper
│   ├── session_manager.py      # Session state management
│   ├── agents/
│   │   ├── screen_interpreter.py
│   │   ├── planner.py
│   │   ├── action_agent.py
│   │   ├── verifier.py
│   │   └── narrator.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── extension/                  # Chrome Extension (React)
│   ├── public/manifest.json
│   ├── src/
│   │   ├── App.jsx
│   │   ├── background.js
│   │   ├── index.css
│   │   └── components/
│   │       ├── CommandBar.jsx
│   │       └── ActionFeed.jsx
│   ├── sidepanel.html
│   ├── package.json
│   └── vite.config.js
│
├── infra/                      # Cloud deployment
│   ├── terraform/
│   ├── cloudbuild.yaml
│   └── deploy.sh
│
└── README.md
```

---

## ☁️ Cloud Deployment

```bash
# One-command deploy (requires gcloud CLI)
cd pilot/infra
chmod +x deploy.sh
./deploy.sh YOUR_PROJECT_ID us-central1
```

Or using Terraform:
```bash
cd pilot/infra/terraform
terraform init
terraform plan -var="project_id=YOUR_PROJECT" -var="gemini_api_key=YOUR_KEY"
terraform apply
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Frontend** | React 18, Vite 5, Chrome Extension Manifest V3 |
| **Backend** | Python 3.11, FastAPI, WebSockets |
| **AI Model** | Gemini 3.1 Pro (multimodal vision + text) |
| **Cloud** | Cloud Run, Firestore, Cloud Storage, Artifact Registry |
| **IaC** | Terraform, Cloud Build |

---

## 📄 License

MIT
