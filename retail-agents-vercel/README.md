# 🏪 Retail Agents — Pius General Dealer

Five AI agents that watch your stock, pricing, demand, suppliers and customers 24/7 — and only recommend. You approve, modify or reject every decision.

---

## 🚀 Quick Start (5 minutes)

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Add your FREE Gemini API key
```bash
cp .env.example .env
# Open .env and paste your key
```
Get a free key at: **https://aistudio.google.com/app/apikey**  
*(No credit card needed — 15 requests/min free)*

### 3. Run the server
```bash
python app.py
```

### 4. Open the dashboard
Go to: **http://localhost:5000**

---

## 📁 Project Structure

```
retail-project/
├── app.py                  ← Flask backend + Gemini API integration
├── retail-agent.html       ← Standalone dashboard (works without Flask too)
├── requirements.txt        ← Python dependencies
├── .env.example            ← Environment variable template
├── .env                    ← Your secrets (gitignored)
├── data/
│   └── retail.db           ← SQLite database (auto-created on first run)
└── README.md
```

---

## 🤖 Gemini AI Integration

The `/api/chat` endpoint uses **gemini-1.5-flash** (free tier):

| Feature | Details |
|---|---|
| Model | `gemini-1.5-flash` |
| Free tier | 15 requests/min, 1M tokens/day |
| Context sent | Live products, stock levels, at-risk customers, recent decisions |
| Fallback | Rule-based answers if no API key set |

**What the AI can answer:**
- "Which products are running low?"
- "Who are my at-risk customers?"
- "Which supplier is most reliable?"
- "What's driving demand this week?"
- "Should I reorder White Bread?"

---

## 🗄️ API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Serve the dashboard HTML |
| GET | `/api/data` | All products, suppliers, customers, decisions |
| GET | `/api/stats` | Today's sales, pending approvals |
| GET | `/api/signals` | Payday/weather signals |
| POST | `/api/chat` | Gemini AI chat |
| POST | `/api/import/products` | Import products CSV |
| POST | `/api/import/suppliers` | Import suppliers CSV |
| POST | `/api/import/customers` | Import customers CSV |
| GET | `/api/template/<kind>` | Download CSV template |
| POST | `/api/decision` | Approve / reject / modify a decision |
| POST | `/api/sale` | Record a sale (reduces stock) |
| GET | `/api/sales-log` | Sales transaction history |
| POST | `/api/clear/<kind>` | Clear a data section |

---

## 📊 The Five AI Agents

| Agent | Code | Function |
|---|---|---|
| Demand & Sales | DSA | Forecasts using moving average + payday/weather signals |
| Inventory | IMA | Monitors stock vs reorder points, flags overstock |
| Pricing | PRA | Compares vs competitors, suggests adjustments |
| Procurement | PCA | Ranks suppliers, flags unreliable ones |
| Customer Engagement | CEA | Tracks segments, identifies at-risk customers |

---

## 📥 Importing Your Own Data

Use the **Data & Import** tab in the dashboard, or POST directly to the API:

```bash
curl -X POST http://localhost:5000/api/import/products \
  -F "file=@products-template.csv"
```

Download the CSV templates from the dashboard or:
```bash
curl http://localhost:5000/api/template/products -o products-template.csv
```

---

## 🔧 Standalone Mode (No Flask)

`retail-agent.html` works entirely in the browser with no server:
- Just open the file in any browser
- All data is stored in JavaScript memory
- CSV import, charts, dark mode, agents — all work offline
- The Flask server adds: persistent SQLite storage + Gemini AI chat

---

## 📄 License
MIT — free to use, modify and distribute.
Built for South African township and general dealers. 🇿🇦
