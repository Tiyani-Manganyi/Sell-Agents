"""
Retail Agents — Pius General Dealer
Flask backend with Gemini Free API (gemini-1.5-flash) integration
Run: python app.py  →  http://localhost:5000
"""

import os, json, sqlite3, csv, io, datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv
from functools import wraps

# ── Load environment variables ──────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")
STORE_PASSWORD  = os.getenv("STORE_PASSWORD", "pius@1")   # change in .env

# ── Password guard decorator ─────────────────────────────────────────────────
def require_password(f):
    """Decorator — checks X-Store-Password header or JSON 'password' field."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Accept from header OR JSON body
        pw_header = request.headers.get("X-Store-Password", "")
        pw_body   = (request.get_json(silent=True) or {}).get("password", "")
        provided  = pw_header or pw_body
        if provided != STORE_PASSWORD:
            return jsonify({"error": "Incorrect password", "auth": False}), 401
        return f(*args, **kwargs)
    return decorated

# ── Try to import Google Generative AI ──────────────────────────────────────
try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        GEMINI_AVAILABLE = True
        print("✅ Gemini 1.5 Flash API connected")
    else:
        GEMINI_AVAILABLE = False
        print("⚠  GEMINI_API_KEY not set — AI chat will use rule-based fallback")
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠  google-generativeai not installed — run: pip install google-generativeai")

# ── Flask app ────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static", template_folder="templates")
DB_PATH = "data/retail.db"


# ── Database setup ────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs("data", exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS products (
        sku         TEXT PRIMARY KEY,
        stock       REAL DEFAULT 0,
        lead_days   INTEGER DEFAULT 2,
        cost        REAL DEFAULT 0,
        price       REAL DEFAULT 0,
        comp_price  REAL DEFAULT 0,
        sensitivity TEXT DEFAULT 'Medium',
        hist        TEXT DEFAULT '[]'
    );

    CREATE TABLE IF NOT EXISTS suppliers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT UNIQUE,
        price_rtg   TEXT DEFAULT 'Fair',
        lead_time   TEXT DEFAULT '3 days',
        on_time     REAL DEFAULT 80,
        variability TEXT DEFAULT 'Medium'
    );

    CREATE TABLE IF NOT EXISTS customers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT UNIQUE,
        segment     TEXT DEFAULT 'Regular',
        days_since  INTEGER DEFAULT 0,
        avg_basket  REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS decisions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        agent       TEXT,
        title       TEXT,
        description TEXT,
        risk        TEXT DEFAULT 'Medium',
        status      TEXT DEFAULT 'Pending',
        cost        REAL DEFAULT 0,
        value       REAL DEFAULT 0,
        mod_note    TEXT DEFAULT '',
        created_at  TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS sales_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        sku         TEXT,
        qty         REAL,
        sell_price  REAL,
        revenue     REAL,
        profit      REAL,
        customer    TEXT DEFAULT 'Walk-in',
        sold_at     TEXT DEFAULT (datetime('now','localtime'))
    );
    """)

    # Seed sample data if tables are empty
    if not c.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        sample_products = [
            ("Maize Meal 5kg",  120, 2, 38.50, 52.00, 50.00, "Medium", json.dumps([95,102,110,108,115,112,118,120])),
            ("White Bread",      85, 1, 12.00, 18.50, 17.99, "High",   json.dumps([200,210,195,220,215,225,218,230])),
            ("Fresh Milk 2L",    60, 1, 22.00, 32.00, 31.50, "High",   json.dumps([150,148,155,160,158,162,165,168])),
            ("Sunflower Oil 2L", 60, 3, 45.00, 68.00, 65.00, "Low",    json.dumps([40,42,45,44,48,47,50,52])),
            ("Rice 2kg",         95, 4, 28.00, 42.00, 40.00, "Medium", json.dumps([70,75,72,80,78,82,85,88])),
            ("Sugar 2kg",        80, 2, 24.00, 36.00, 35.00, "Medium", json.dumps([60,65,68,70,72,75,78,80])),
            ("Eggs (6 pack)",    70, 1, 18.00, 28.00, 27.50, "High",   json.dumps([120,125,118,130,128,135,132,138])),
            ("Canned Beans 420g",55, 3,  8.50, 14.00, 13.50, "Medium", json.dumps([45,48,50,52,49,55,53,57])),
        ]
        c.executemany(
            "INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?,?,?)",
            sample_products
        )

    if not c.execute("SELECT 1 FROM suppliers LIMIT 1").fetchone():
        c.executemany(
            "INSERT OR IGNORE INTO suppliers (name,price_rtg,lead_time,on_time,variability) VALUES (?,?,?,?,?)",
            [
                ("Premier Foods",          "Good", "2 days", 92, "Low"),
                ("Tiger Brands",           "Good", "3 days", 78, "Medium"),
                ("Agri-Supply SA",         "Fair", "1 day",  94, "Low"),
                ("Local Wholesaler",       "Poor", "1 day",  65, "High"),
            ]
        )

    if not c.execute("SELECT 1 FROM customers LIMIT 1").fetchone():
        c.executemany(
            "INSERT OR IGNORE INTO customers (name,segment,days_since,avg_basket) VALUES (?,?,?,?)",
            [
                ("Thandi Mokoena",  "Loyal",    5,  320),
                ("Johan van Wyk",   "Regular",  14, 180),
                ("Lerato Dlamini",  "At-Risk",  28,  95),
                ("Sipho Nkosi",     "At-Risk",  35, 140),
                ("Nomsa Khumalo",   "Loyal",     3, 480),
            ]
        )

    conn.commit()
    conn.close()
    print("✅ Database initialised:", DB_PATH)


# ── Helper: load all store data as dicts ─────────────────────────────────────
def load_store_data():
    conn = get_db()
    products  = [dict(r) for r in conn.execute("SELECT * FROM products").fetchall()]
    suppliers = [dict(r) for r in conn.execute("SELECT * FROM suppliers").fetchall()]
    customers = [dict(r) for r in conn.execute("SELECT * FROM customers").fetchall()]
    for p in products:
        try:    p["hist"] = json.loads(p["hist"])
        except: p["hist"] = []
    conn.close()
    return products, suppliers, customers


# ── Helper: compute reorder point ────────────────────────────────────────────
def compute_rop(product, factor=1.4):
    hist = product.get("hist", [])
    if len(hist) >= 4:
        avg = sum(hist[-4:]) / 4
    elif hist:
        avg = sum(hist) / len(hist)
    else:
        avg = 0
    daily = avg / 7
    return max(1, round(daily * product.get("lead_days", 2) * factor))


# ── Helper: forecast ─────────────────────────────────────────────────────────
def forecast(product):
    hist = product.get("hist", [0,0,0,0])
    if len(hist) < 2:
        return hist[0] if hist else 0
    avg = sum(hist[-4:]) / min(4, len(hist))
    trend = (hist[-1] - hist[0]) / max(1, len(hist) - 1)
    d = datetime.date.today().day
    payday = d >= 25 or d <= 3
    fc = avg + trend * 2
    if payday and product.get("sensitivity") == "High":
        fc *= 1.15
    return round(max(0, fc))


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "retail-agent.html")


@app.route("/api/auth", methods=["POST"])
def api_auth():
    """Verify store password — used by the dashboard before protected actions."""
    data = request.get_json(silent=True) or {}
    if data.get("password") == STORE_PASSWORD:
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Incorrect password"}), 401


@app.route("/api/data")
def api_data():
    products, suppliers, customers = load_store_data()
    conn = get_db()
    decisions = [dict(r) for r in conn.execute("SELECT * FROM decisions ORDER BY created_at DESC").fetchall()]
    conn.close()
    return jsonify({
        "products":  products,
        "suppliers": suppliers,
        "customers": customers,
        "decisions": decisions,
        "gemini":    GEMINI_AVAILABLE,
    })


@app.route("/api/stats")
def api_stats():
    conn = get_db()
    today = datetime.date.today().isoformat()
    stats = {
        "pending":  conn.execute("SELECT COUNT(*) FROM decisions WHERE status='Pending'").fetchone()[0],
        "approved": conn.execute("SELECT COUNT(*) FROM decisions WHERE status IN ('Approved','Auto-approved')").fetchone()[0],
        "sales_today": conn.execute(
            "SELECT COALESCE(SUM(revenue),0) FROM sales_log WHERE date(sold_at)=?", (today,)
        ).fetchone()[0],
        "units_today": conn.execute(
            "SELECT COALESCE(SUM(qty),0) FROM sales_log WHERE date(sold_at)=?", (today,)
        ).fetchone()[0],
    }
    conn.close()
    return jsonify(stats)


@app.route("/api/import/<kind>", methods=["POST"])
@require_password
def api_import(kind):
    if kind not in ("products", "suppliers", "customers"):
        return jsonify({"error": "Unknown data type"}), 400

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    text = file.read().decode("utf-8-sig")  # strip BOM
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return jsonify({"error": "CSV is empty"}), 400

    # Normalise header names
    ALIASES = {
        "competitor_price": "comp_price", "comp": "comp_price",
        "price_rating": "price_rtg", "on_time_pct": "on_time",
        "days_since_visit": "days_since", "basket": "avg_basket",
    }
    norm_rows = []
    for row in rows:
        nr = {}
        for k, v in row.items():
            key = k.strip().lower().replace(" ", "_")
            key = ALIASES.get(key, key)
            nr[key] = v.strip()
        norm_rows.append(nr)

    conn = get_db()
    count = 0
    try:
        if kind == "products":
            conn.execute("DELETE FROM products")
            for r in norm_rows:
                sku = r.get("sku") or r.get("name", "")
                if not sku:
                    continue
                hist = [float(r.get(f"sales_w{i}", 0) or 0) for i in range(1, 9)]
                conn.execute(
                    "INSERT OR REPLACE INTO products VALUES (?,?,?,?,?,?,?,?)",
                    (sku, float(r.get("stock", 0) or 0),
                     int(r.get("lead_days", 2) or 2),
                     float(r.get("cost", 0) or 0),
                     float(r.get("price", 0) or 0),
                     float(r.get("comp_price", 0) or 0),
                     r.get("sensitivity", "Medium"),
                     json.dumps(hist))
                )
                count += 1

        elif kind == "suppliers":
            conn.execute("DELETE FROM suppliers")
            for r in norm_rows:
                name = r.get("name", "")
                if not name:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO suppliers (name,price_rtg,lead_time,on_time,variability) VALUES (?,?,?,?,?)",
                    (name, r.get("price_rtg","Fair"), r.get("lead_time","3 days"),
                     float(r.get("on_time", 80) or 80), r.get("variability","Medium"))
                )
                count += 1

        elif kind == "customers":
            conn.execute("DELETE FROM customers")
            for r in norm_rows:
                name = r.get("name", "")
                if not name:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO customers (name,segment,days_since,avg_basket) VALUES (?,?,?,?)",
                    (name, r.get("segment","Regular"),
                     int(r.get("days_since", 0) or 0),
                     float(r.get("avg_basket", 0) or 0))
                )
                count += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({"success": True, "count": count, "kind": kind})


@app.route("/api/template/<kind>")
def api_template(kind):
    templates = {
        "products":  "sku,stock,lead_days,cost,price,comp_price,sensitivity,sales_w1,sales_w2,sales_w3,sales_w4,sales_w5,sales_w6,sales_w7,sales_w8\nMaize Meal 5kg,120,2,38.50,52.00,50.00,Medium,95,102,110,108,115,112,118,120\nWhite Bread,85,1,12.00,18.50,17.99,High,200,210,195,220,215,225,218,230",
        "suppliers": "name,price_rtg,lead_time,on_time,variability\nPremier Foods,Good,2 days,92,Low\nTiger Brands,Good,3 days,78,Medium",
        "customers": "name,segment,days_since,avg_basket\nThandi Mokoena,Loyal,5,320\nLerato Dlamini,At-Risk,28,95",
    }
    if kind not in templates:
        return "Not found", 404
    from flask import Response
    return Response(
        templates[kind],
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={kind}-template.csv"}
    )


@app.route("/api/decision", methods=["POST"])
def api_decision():
    data = request.get_json()
    conn = get_db()
    if data.get("id"):
        conn.execute(
            "UPDATE decisions SET status=?, mod_note=? WHERE id=?",
            (data["status"], data.get("mod_note",""), data["id"])
        )
    else:
        conn.execute(
            "INSERT INTO decisions (agent,title,description,risk,status,cost,value) VALUES (?,?,?,?,?,?,?)",
            (data.get("agent",""), data.get("title",""), data.get("description",""),
             data.get("risk","Medium"), data.get("status","Pending"),
             data.get("cost",0), data.get("value",0))
        )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/sale", methods=["POST"])
def api_sale():
    data = request.get_json()
    sku        = data.get("sku","")
    qty        = float(data.get("qty", 1))
    sell_price = float(data.get("sell_price", 0))
    customer   = data.get("customer", "Walk-in")

    conn = get_db()
    product = conn.execute("SELECT * FROM products WHERE sku=?", (sku,)).fetchone()
    if not product:
        conn.close()
        return jsonify({"error": "Product not found"}), 404
    if product["stock"] < qty:
        conn.close()
        return jsonify({"error": f"Only {product['stock']} units in stock"}), 400

    price    = sell_price or product["price"]
    revenue  = price * qty
    profit   = (price - product["cost"]) * qty

    conn.execute("UPDATE products SET stock=stock-? WHERE sku=?", (qty, sku))
    conn.execute(
        "INSERT INTO sales_log (sku,qty,sell_price,revenue,profit,customer) VALUES (?,?,?,?,?,?)",
        (sku, qty, price, revenue, profit, customer)
    )
    conn.commit()
    new_stock = conn.execute("SELECT stock FROM products WHERE sku=?", (sku,)).fetchone()[0]
    conn.close()

    return jsonify({"success": True, "revenue": revenue, "profit": profit, "new_stock": new_stock})


@app.route("/api/sales-log")
def api_sales_log():
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM sales_log ORDER BY sold_at DESC LIMIT 200"
    ).fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/clear/<kind>", methods=["POST"])
@require_password
def api_clear(kind):
    conn = get_db()
    tables = {
        "products":  "products",
        "suppliers": "suppliers",
        "customers": "customers",
        "saleslog":  "sales_log",
        "decisions": "decisions",
    }
    if kind == "all":
        for t in tables.values():
            conn.execute(f"DELETE FROM {t}")
    elif kind in tables:
        conn.execute(f"DELETE FROM {tables[kind]}")
    else:
        conn.close()
        return jsonify({"error": "Unknown section"}), 400
    conn.commit()
    conn.close()
    return jsonify({"success": True, "cleared": kind})


@app.route("/api/table/<table>")
def api_table(table):
    allowed = {"products", "suppliers", "customers", "decisions", "sales_log"}
    if table not in allowed:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_db()
    rows = [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]
    conn.close()
    return jsonify(rows)


# ── Gemini AI Chat endpoint ───────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a smart retail assistant AI for Pius General Dealer, a general store in Limpopo, South Africa.
You help the owner-manager make good decisions about stock, pricing, suppliers, and customers.
You have access to the store's live data below. Give practical, concise answers in plain English.
Always recommend approval workflows — never tell the owner to act without reviewing.
Keep answers to 2-3 sentences unless a detailed analysis is requested.
Respond in a warm, professional tone suited to a South African retail owner.

STORE DATA:
{store_data}
"""

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"reply": "Please ask me something about your store."}), 400

    # Build context from live DB
    products, suppliers, customers = load_store_data()
    conn = get_db()
    decisions = [dict(r) for r in conn.execute(
        "SELECT title,status,risk FROM decisions ORDER BY created_at DESC LIMIT 10"
    ).fetchall()]
    conn.close()

    low_stock = [p for p in products if p["stock"] <= compute_rop(p)]
    at_risk   = [c for c in customers if c["segment"] == "At-Risk" or c["days_since"] > 21]

    store_summary = f"""
Products: {len(products)} items. Low stock / reorder needed: {[p['sku'] for p in low_stock]}.
Suppliers: {len(suppliers)}. Unreliable (on-time < 75%): {[s['name'] for s in suppliers if s['on_time'] < 75]}.
Customers: {len(customers)}. At-risk: {[c['name'] for c in at_risk]}.
Recent decisions: {[f"{d['title']} ({d['status']})" for d in decisions[:5]]}.
"""

    if GEMINI_AVAILABLE:
        try:
            prompt = SYSTEM_PROMPT.format(store_data=store_summary) + f"\n\nOwner asks: {user_msg}"
            response = gemini_model.generate_content(prompt)
            reply = response.text.strip()
        except Exception as e:
            reply = f"Gemini API error: {str(e)}. Falling back to built-in analysis."
            GEMINI_AVAILABLE_local = False
    else:
        # Rule-based fallback when no Gemini key
        reply = rule_based_reply(user_msg, products, suppliers, customers, low_stock, at_risk)

    return jsonify({"reply": reply, "gemini": GEMINI_AVAILABLE})


def rule_based_reply(msg, products, suppliers, customers, low_stock, at_risk):
    q = msg.lower()
    if any(w in q for w in ["stock","reorder","low"]):
        if low_stock:
            return f"You have {len(low_stock)} items below reorder point: {', '.join(p['sku'] for p in low_stock[:3])}. Consider raising a purchase order."
        return "All products are above their reorder points. Stock levels look healthy."
    if any(w in q for w in ["demand","forecast","sell"]):
        top = sorted(products, key=lambda p: forecast(p), reverse=True)[:3]
        return "Top demand items this week: " + ", ".join(f"{p['sku']} ({forecast(p)} units)" for p in top) + "."
    if "supplier" in q:
        bad = [s for s in suppliers if s["on_time"] < 75]
        return f"You have {len(suppliers)} suppliers. Unreliable (on-time < 75%): {', '.join(s['name'] for s in bad) or 'none'}."
    if any(w in q for w in ["customer","churn","risk"]):
        return f"{len(at_risk)} at-risk customers: {', '.join(c['name'] for c in at_risk[:3]) or 'none'}. Consider sending a promo."
    if any(w in q for w in ["price","margin","profit"]):
        avg_margin = sum((p["price"]-p["cost"])/p["price"]*100 for p in products if p["price"] > 0) / max(1, len(products))
        return f"Average gross margin: {avg_margin:.1f}%. Set GEMINI_API_KEY in .env for smarter pricing analysis."
    return f"You have {len(products)} products, {len(suppliers)} suppliers and {len(customers)} customers. Add your GEMINI_API_KEY to .env for AI-powered answers."


# ── Signals endpoint (weather + payday) ──────────────────────────────────────
@app.route("/api/signals")
def api_signals():
    d = datetime.date.today()
    payday = d.day >= 25 or d.day <= 3
    return jsonify({
        "payday":  payday,
        "date":    d.isoformat(),
        "weekday": d.strftime("%A"),
        "weather": "Sunny, 28°C",   # wire to Open-Meteo if desired
        "notes":   "Payday window active — expect +15% uplift on staples" if payday else "Normal demand period",
    })


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    print(f"\n🏪 Retail Agents — Pius General Dealer")
    print(f"   Running on http://localhost:{port}")
    print(f"   Gemini AI: {'✅ Connected' if GEMINI_AVAILABLE else '⚠  Not configured (set GEMINI_API_KEY in .env)'}\n")
    app.run(debug=debug, port=port, host="0.0.0.0")
