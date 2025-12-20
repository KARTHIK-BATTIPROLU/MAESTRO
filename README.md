# 📦 MAESTRO - MSME Inventory Intelligence System

> **AI-powered inventory recommendations for Micro, Small & Medium Enterprises**

![Version](https://img.shields.io/badge/version-2.0.0-cyan)
![Status](https://img.shields.io/badge/status-Production%20Ready-green)
![Agents](https://img.shields.io/badge/agents-5%20Active-blue)

---

## 🎯 Problem Statement

> "Optimizing inventory and ordering is difficult for MSMEs due to the lack of a system that can **autonomously predict optimal reorder points** by correlating **fluctuating supplier lead times**, **seasonal demand shifts**, and **warehouse capacity**."

### MAESTRO Solves This By:

| Challenge | MAESTRO Solution |
|-----------|------------------|
| When to reorder? | AI-predicted timing based on demand + supplier risk |
| How much to order? | Quantity strategy based on warehouse + cash flow |
| What are the risks? | Multi-factor risk correlation with explanations |

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           MAESTRO PRODUCTION SYSTEM                           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│   ┌─────────────┐       ┌─────────────┐       ┌──────────────────────────┐  │
│   │   FRONTEND  │       │   BACKEND   │       │     AGENT SERVICE        │  │
│   │   (React)   │ ────► │  (Node.js)  │ ────► │    (Python + AI)         │  │
│   │  Port 5173  │       │  Port 5000  │       │     Port 8000            │  │
│   └─────────────┘       └─────────────┘       └──────────────────────────┘  │
│                                                           │                  │
│                                                           ▼                  │
│                                               ┌──────────────────────────┐  │
│                                               │   5-AGENT PIPELINE       │  │
│                                               │                          │  │
│                                               │  1. Router/Intake Agent  │  │
│                                               │  2. Research/Risk Agent  │  │
│                                               │  3. Warehouse Agent      │  │
│                                               │  4. Decision Agent       │  │
│                                               │  5. Orchestrator Agent   │  │
│                                               │                          │  │
│                                               │  LLM: Google Gemini      │  │
│                                               └──────────────────────────┘  │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 5-Agent System (Production Design)

### Agent 1: Router / Intake Agent
**Goal:** Convert MSME answers into structured signals

```json
{
  "demand_variability": 0.8,
  "supplier_delay_risk": 0.7,
  "warehouse_capacity_stress": 0.6,
  "cash_flow_sensitivity": 0.7,
  "business_context": {...},
  "signals": {...}
}
```

### Agent 2: Research / External Risk Agent
**Goal:** Adjust risk using real-world signals (festivals, strikes, seasons)

```json
{
  "external_demand_risk_modifier": +0.15,
  "external_lead_time_risk_modifier": +0.20,
  "external_factors": [...],
  "market_outlook": "challenging"
}
```

### Agent 3: Warehouse Agent
**Goal:** Enforce physical feasibility

```json
{
  "warehouse_stress": 0.82,
  "feasible_order_limit": "LOW",
  "optimal_frequency": "weekly",
  "storage_strategy": "..."
}
```

### Agent 4: Inventory Decision Agent (CORE)
**Goal:** Correlate ALL risks and produce ONE clear decision

```json
{
  "reorder_timing": "EARLY",
  "order_quantity_strategy": "SPLIT_ORDERS",
  "risk_level": "HIGH",
  "composite_risk_score": 0.72,
  "decision_reasoning": "Seasonal demand + supplier delays + limited storage"
}
```

### Agent 5: Decision Orchestrator (Meta-Agent)
**Goal:** Final authority - resolve conflicts, ensure explainability

```json
{
  "final_decision": {...},
  "what_we_understood": {...},
  "detected_risks": [...],
  "recommendation": {...},
  "why_this_decision": "...",
  "immediate_actions": [...],
  "warnings": [...]
}
```

---

## 🔄 System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAESTRO FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. MSME answers 10 questions                                  │
│              │                                                   │
│              ▼                                                   │
│   2. Router Agent builds risk profile                           │
│              │                                                   │
│              ▼                                                   │
│   3. Research Agent adjusts for external factors                │
│              │                                                   │
│              ▼                                                   │
│   4. Warehouse Agent enforces capacity constraints              │
│              │                                                   │
│              ▼                                                   │
│   5. Decision Agent correlates ALL signals                      │
│              │                                                   │
│              ▼                                                   │
│   6. Orchestrator outputs ONE clear decision                    │
│              │                                                   │
│              ▼                                                   │
│   7. Dashboard displays:                                        │
│      • What We Understood                                       │
│      • Detected Risks                                           │
│      • Recommendation (When, How Much, How)                     │
│      • Why This Decision                                        │
│      • Immediate Actions                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧾 10 MSME Questions (Mandatory Intake)

| # | Question | Signal Type |
|---|----------|-------------|
| 1 | Business description (industry, products, scale) | Business Profile |
| 2 | Current reorder method | Process Maturity |
| 3 | Stockouts vs overstock history | Inventory Health |
| 4 | Supplier reliability & delays | Lead Time Risk |
| 5 | Seasonal / volatile demand | Demand Volatility |
| 6 | Reorder timing mistakes | Timing Accuracy |
| 7 | Warehouse constraints | Capacity Stress |
| 8 | Cash flow impact | Financial Sensitivity |
| 9 | Tool/system limitations | Tech Readiness |
| 10 | Desired outcome | Priority Signal |

---

## 📊 Final Dashboard Output

```
┌─────────────────────────────────────────────────────────────────┐
│                    MAESTRO RECOMMENDATION                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ⚡ REORDER EARLY          MODERATE RISK    82% Conf.   │   │
│  │  Split orders into weekly deliveries                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐   │
│  │ WHAT WE         │  │ DETECTED        │  │ WHY THIS     │   │
│  │ UNDERSTOOD      │  │ RISKS           │  │ DECISION     │   │
│  │                 │  │                 │  │              │   │
│  │ • Demand shows  │  │ • Seasonal Spike│  │ Storage      │   │
│  │   seasonal      │  │   (MODERATE)    │  │ limits bulk  │   │
│  │   variation     │  │                 │  │ orders while │   │
│  │                 │  │ • Supplier      │  │ supplier     │   │
│  │ • Suppliers     │  │   Delays        │  │ delays need  │   │
│  │   have delays   │  │   (MODERATE)    │  │ earlier      │   │
│  │                 │  │                 │  │ reordering   │   │
│  │ • Storage is    │  │ • Storage       │  │              │   │
│  │   limited       │  │   Capacity      │  │              │   │
│  │                 │  │   (HIGH)        │  │              │   │
│  └─────────────────┘  └─────────────────┘  └──────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ RECOMMENDATION                                           │   │
│  │                                                          │   │
│  │ 📅 WHEN: Reorder 7-10 days earlier than usual           │   │
│  │ 📦 HOW MUCH: 20% less per order, twice as frequently    │   │
│  │ 🚚 HOW: Weekly delivery schedule with supplier          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ IMMEDIATE ACTIONS                                        │   │
│  │                                                          │   │
│  │ 1. Calculate weekly consumption for top 5 products      │   │
│  │ 2. Contact supplier for weekly delivery schedule        │   │
│  │ 3. Set reorder alerts for 7 days before usual timing    │   │
│  │ 4. Clear slow-moving stock to free up storage           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18 + Vite + TailwindCSS | User interface |
| **Backend** | Node.js + Express | API Gateway (no business logic) |
| **Agent Service** | Python + FastAPI + CrewAI | Multi-agent intelligence |
| **LLM** | Google Gemini 1.5 Flash | Language understanding |
| **State** | In-memory (Redis-ready) | Session management |

---

## 📁 Project Structure

```
MAESTRO/
├── frontend/                    # React Application
│   └── src/
│       ├── pages/
│       │   ├── LandingPage.jsx      # Welcome page
│       │   ├── OnboardingPage.jsx   # 10-question chat
│       │   └── DashboardPage.jsx    # Results display
│       └── services/
│           └── api.js               # API client
│
├── backend/                     # Node.js API Gateway
│   └── src/
│       ├── routes/api.js            # Route definitions
│       └── server.js                # Express setup
│
├── agent-service/               # Python AI Service
│   ├── main.py                      # FastAPI server
│   ├── agents.py                    # 5 Agent definitions
│   ├── tasks.py                     # Agent task definitions
│   ├── orchestrator.py              # Pipeline execution
│   ├── questions.py                 # Question + signal mappings
│   └── config.py                    # Configuration
│
└── README.md                    # This file
```

---

## 🚀 How to Run

### Prerequisites
- Node.js 18+
- Python 3.10+
- Google Gemini API Key

### Step 1: Setup Agent Service
```bash
cd agent-service
python -m venv venv
.\venv\Scripts\activate      # Windows
pip install -r requirements.txt

# Create .env file
echo GOOGLE_API_KEY=your_key_here > .env
```

### Step 2: Install Dependencies
```bash
cd ../backend && npm install
cd ../frontend && npm install
```

### Step 3: Start All Services

**Terminal 1 - Agent Service:**
```bash
cd agent-service
.\venv\Scripts\activate
python main.py
# → Server at http://localhost:8000
```

**Terminal 2 - Backend:**
```bash
cd backend
npm run dev
# → Server at http://localhost:5000
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
# → App at http://localhost:5173
```

### Step 4: Open Browser
Navigate to **http://localhost:5173**

---

## 🔌 API Endpoints

### Agent Service (Port 8000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health |
| GET | `/questions` | Get all 10 questions |
| POST | `/start-session` | Start new session |
| POST | `/respond` | Submit answer |
| POST | `/process` | Run 5-agent pipeline |
| GET | `/session/{id}` | Get session state |

### Backend (Port 5000)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Full health check |
| POST | `/api/start-onboarding` | Start session |
| POST | `/api/send-user-response` | Submit answer |
| POST | `/api/process` | Process with agents |

---

## 📤 Final Output Format

The system outputs a structured JSON response:

```json
{
  "final_decision": {
    "reorder_timing": "EARLY | NORMAL | DELAYED",
    "order_strategy": "BULK | SPLIT_ORDERS | FREQUENT_SMALL",
    "risk_level": "LOW | MODERATE | HIGH",
    "confidence": 82
  },
  "what_we_understood": {
    "demand_situation": "Your demand shows seasonal spikes...",
    "supplier_situation": "Your suppliers have some delays...",
    "warehouse_situation": "Your storage space is limited...",
    "key_constraint": "Warehouse capacity"
  },
  "detected_risks": [
    {
      "risk": "Seasonal demand spike",
      "level": "MODERATE",
      "explanation": "Upcoming festival season may increase demand"
    }
  ],
  "recommendation": {
    "timing": "Reorder 7-10 days earlier than usual",
    "quantity": "20% less per order, twice as frequently",
    "method": "Weekly delivery schedule with supplier"
  },
  "why_this_decision": "Given your limited storage and supplier delays...",
  "immediate_actions": [
    "Calculate weekly consumption for top 5 products",
    "Contact supplier for weekly delivery schedule",
    "Set reorder alerts for 7 days before usual timing"
  ],
  "warnings": [
    "Cash flow impact: Frequent orders may affect terms"
  ]
}
```

---

## 🧠 Decision Rules

| Condition | Timing | Strategy |
|-----------|--------|----------|
| demand_risk > 0.6 AND supplier_risk > 0.6 | EARLY | Buffer stock |
| warehouse_stress > 0.7 | Any | SPLIT_ORDERS |
| cash_sensitivity > 0.7 | Any | FREQUENT_SMALL |
| All risks < 0.4 | NORMAL | BULK (efficient) |

### Risk Level Calculation
```
composite_risk = (demand + supplier + warehouse + cash) / 4

LOW:      composite < 0.4
MODERATE: 0.4 ≤ composite < 0.7
HIGH:     composite ≥ 0.7
```

---

## 🚫 Hard Constraints

- ❌ No vague AI answers
- ❌ No generic advice
- ❌ No assumptions without explanation
- ❌ No multiple conflicting outputs
- ✅ ONE clear reorder decision
- ✅ Always explain WHY
- ✅ Connect risks to recommendations

---

## 🎯 Positioning Statement

> **"MAESTRO helps MSMEs make confident inventory decisions by automatically correlating demand uncertainty, supplier delays, and warehouse constraints into clear reorder recommendations."**

---

## 📄 License

MIT License

---

<div align="center">

**Built for MSMEs who deserve better inventory decisions**

🎯 MAESTRO - Making Inventory Simple

</div>
