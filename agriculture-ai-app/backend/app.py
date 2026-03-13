import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory,
    redirect,
    url_for,
    session,
    flash,
)
from werkzeug.security import generate_password_hash, check_password_hash

from crop_recommendation import recommend_crop, recommend_crops_detailed
from crop_price_analysis import (
    get_available_filters,
    yearly_production_trend,
    market_price_analysis,
    compare_crops,
    season_wise_analysis,
    state_wise_ranking,
    get_monitoring_dashboard,
)
from disease_model import predict_disease
from drone_analysis import analyze_drone_image
from weather_agent import get_weather_by_pincode, get_weather_by_coords, build_farming_suggestion


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "database" / "agriculture.db"
UPLOAD_DIR = BASE_DIR / "uploads" / "images"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("openai_api_key") or os.getenv("OPENAI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    cur = conn.cursor()

    # Core entities
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            email TEXT,
            village TEXT,
            district TEXT,
            state TEXT,
            pincode TEXT,
            password_hash TEXT,
            is_verified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    # Backwards-compatible upgrades for existing Farmers table
    for column_def in [
        "ADD COLUMN email TEXT",
        "ADD COLUMN district TEXT",
        "ADD COLUMN state TEXT",
        "ADD COLUMN password_hash TEXT",
        "ADD COLUMN is_verified INTEGER DEFAULT 0",
        "ADD COLUMN created_at TEXT DEFAULT (datetime('now'))",
    ]:
        try:
            cur.execute(f"ALTER TABLE Farmers {column_def}")
        except sqlite3.OperationalError:
            pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER,
            name TEXT,
            area REAL,
            soil_type TEXT,
            location TEXT,
            FOREIGN KEY(farmer_id) REFERENCES Farmers(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            water_requirement TEXT,
            fertilizer_suggestion TEXT,
            season TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS YieldRecords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id INTEGER,
            crop_id INTEGER,
            season TEXT,
            year INTEGER,
            production REAL,
            profit REAL,
            expenses REAL,
            FOREIGN KEY(field_id) REFERENCES Fields(id),
            FOREIGN KEY(crop_id) REFERENCES Crops(id)
        )
        """
    )

    # Per-field, per-year economics (investment, revenue, profit)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS YearlyProduction (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER,
            field_id INTEGER,
            crop_name TEXT,
            year INTEGER,
            investment REAL,
            production_kg REAL,
            selling_price REAL,
            revenue REAL,
            profit REAL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(farmer_id) REFERENCES Farmers(id),
            FOREIGN KEY(field_id) REFERENCES Fields(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS DiseaseDetections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id INTEGER,
            image_path TEXT,
            disease TEXT,
            confidence REAL,
            suggestion TEXT,
            created_at TEXT,
            FOREIGN KEY(field_id) REFERENCES Fields(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS DroneImages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            field_id INTEGER,
            image_path TEXT,
            health_score REAL,
            stress_result TEXT,
            disease TEXT,
            created_at TEXT,
            FOREIGN KEY(field_id) REFERENCES Fields(id)
        )
        """
    )

    # Backwards-compatible schema upgrade: add disease column if missing
    try:
        cur.execute("ALTER TABLE DroneImages ADD COLUMN disease TEXT")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS WeatherLogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pincode TEXT,
            temperature REAL,
            humidity REAL,
            wind_speed REAL,
            rain REAL,
            description TEXT,
            created_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ChatbotLogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            bot_response TEXT,
            pincode TEXT,
            created_at TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS EmailOtps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id INTEGER,
            email TEXT,
            otp TEXT,
            expires_at TEXT,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(farmer_id) REFERENCES Farmers(id)
        )
        """
    )

    # Seed crop table with common Indian crops (if empty)
    cur.execute("SELECT COUNT(*) FROM Crops")
    if cur.fetchone()[0] == 0:
        crops = [
            ("Paddy", "High water", "Urea, DAP", "Kharif"),
            ("Jowar", "Moderate", "NPK mix", "Rabi/Kharif"),
            ("Millets", "Low", "Organic manure", "Kharif"),
            ("Cotton", "Moderate", "NPK, potash", "Kharif"),
            ("Maize", "Moderate", "NPK basal", "Kharif/Rabi"),
            ("Wheat", "Moderate", "DAP, urea", "Rabi"),
        ]
        cur.executemany(
            "INSERT INTO Crops (name, water_requirement, fertilizer_suggestion, season) VALUES (?, ?, ?, ?)",
            crops,
        )

    conn.commit()
    conn.close()


app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "static"),
    template_folder=str(BASE_DIR / "frontend"),
)

app.secret_key = SECRET_KEY


def get_current_farmer() -> Optional[sqlite3.Row]:
    farmer_id = session.get("farmer_id")
    if not farmer_id:
        return None
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Farmers WHERE id = ?", (farmer_id,))
    row = cur.fetchone()
    conn.close()
    return row


def login_required(view_func):  # type: ignore
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("farmer_id"):
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapper


def send_otp_email(email: str, otp: str) -> None:
    if not (SMTP_USER and SMTP_PASSWORD):
        print(f"OTP for {email}: {otp}")
        return

    import smtplib
    from email.mime.text import MIMEText

    body = f"Your PAS verification code is: {otp}\nThis code is valid for 10 minutes."
    msg = MIMEText(body)
    msg["Subject"] = "PAS Email Verification Code"
    msg["From"] = SMTP_USER
    msg["To"] = email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


def generate_otp() -> str:
    from random import randint

    return f"{randint(100000, 999999)}"


def generate_captcha() -> str:
    from random import choices
    import string

    return "".join(choices(string.ascii_uppercase + string.digits, k=5))


# ------------- Page routes -------------


@app.route("/")
def home():
    farmer = get_current_farmer()
    return render_template("index.html", farmer=farmer)


@app.route("/crop-recommendation")
def crop_recommendation_page():
    farmer = get_current_farmer()
    return render_template("crop_recommendation.html", farmer=farmer)


@app.route("/disease-detection")
def disease_detection_page():
    farmer = get_current_farmer()
    return render_template("disease_detection.html", farmer=farmer)


@app.route("/yield-dashboard")
def yield_dashboard_page():
    farmer = get_current_farmer()
    return render_template("yield_dashboard.html", farmer=farmer)


@app.route("/drone-monitoring")
def drone_monitoring_page():
    farmer = get_current_farmer()
    return render_template("drone_monitoring.html", farmer=farmer)


@app.route("/about")
def about_page():
    farmer = get_current_farmer()
    return render_template("about.html", farmer=farmer)


@app.route("/crop-monitoring")
def crop_monitoring_page():
    farmer = get_current_farmer()
    filters = get_available_filters()
    return render_template("crop_monitoring.html", farmer=farmer, filters=filters)


# ------------- API: Crop Price & Production Monitoring -------------


@app.route("/api/crop-monitoring/filters")
def api_crop_monitoring_filters():
    return jsonify(get_available_filters())


@app.route("/api/crop-monitoring/production", methods=["POST"])
def api_production_trend():
    data = request.json or {}
    crop = data.get("crop", "Rice")
    state = data.get("state") or None
    result = yearly_production_trend(crop, state)
    return jsonify(result)


@app.route("/api/crop-monitoring/prices", methods=["POST"])
def api_price_analysis():
    data = request.json or {}
    commodity = data.get("commodity") or None
    district = data.get("district") or None
    result = market_price_analysis(commodity, district)
    return jsonify(result)


@app.route("/api/crop-monitoring/compare", methods=["POST"])
def api_compare_crops():
    data = request.json or {}
    crop_list = data.get("crops", ["Rice", "Wheat", "Maize"])
    state = data.get("state") or None
    result = compare_crops(crop_list, state)
    return jsonify(result)


@app.route("/api/crop-monitoring/dashboard", methods=["POST"])
def api_monitoring_dashboard():
    data = request.json or {}
    crop = data.get("crop", "Rice")
    state = data.get("state") or None
    commodity = data.get("commodity") or None
    result = get_monitoring_dashboard(crop, state, commodity)
    return jsonify(result)


# ------------- API: Crop recommendation -------------


@app.route("/api/crop-recommendation", methods=["POST"])
def api_crop_recommendation():
    data = request.json or request.form

    temp = float(data.get("temperature", 0))
    humidity = float(data.get("humidity", 0))
    rainfall = float(data.get("rainfall", 0))
    ph = float(data.get("ph", 0) or 0)
    ec = float(data.get("ec", 0) or 0)
    carbon = float(data.get("carbon", 0) or 0)
    ca = float(data.get("ca", 0) or 0)
    mg = float(data.get("mg", 0) or 0)
    soil = data.get("soil_type", "loamy")
    location = data.get("location", "")
    area = float(data.get("area", 1) or 1)
    investment = data.get("investment")
    investment = float(investment) if investment else None

    # Get detailed multi-crop recommendation
    result = recommend_crops_detailed(
        temp, humidity, rainfall, soil, ph, ec, carbon, ca, mg,
        area_hectares=area, investment=investment,
    )

    return jsonify(result)


# ------------- API: Disease detection -------------


@app.route("/api/disease-detection", methods=["POST"])
def api_disease_detection():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    save_path = UPLOAD_DIR / file.filename
    file.save(save_path)

    result = predict_disease(str(save_path))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO DiseaseDetections (field_id, image_path, disease, confidence, suggestion, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            None,
            str(save_path),
            result["disease"],
            result["confidence"],
            result["suggestion"],
        ),
    )
    conn.commit()
    conn.close()

    return jsonify(result)


# ------------- API: Drone monitoring -------------


@app.route("/api/drone-analysis", methods=["POST"])
def api_drone_analysis():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    save_path = UPLOAD_DIR / file.filename
    file.save(save_path)

    # Analyze field health from drone image
    field_result = analyze_drone_image(str(save_path))

    # Also run disease classification on the same image
    disease_result = predict_disease(str(save_path))

    combined = {
        "health_score": field_result.get("health_score"),
        "stress_result": field_result.get("stress_result"),
        "disease": disease_result.get("disease"),
        "confidence": disease_result.get("confidence"),
        "suggestion": disease_result.get("suggestion"),
        "pesticide": disease_result.get("pesticide"),
    }

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO DroneImages (field_id, image_path, health_score, stress_result, disease, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            None,
            str(save_path),
            combined["health_score"],
            combined["stress_result"],
            combined["disease"],
        ),
    )
    conn.commit()
    conn.close()

    return jsonify(combined)


# ------------- API: Yield monitoring & field growth -------------


@app.route("/add_production", methods=["POST"])
def add_production():
    """Store yearly production + economics for a specific field.

    Expects JSON body with farmer_id, field_id, crop, year,
    investment, production, and price.
    """

    data = request.json or request.form

    try:
        farmer_id = int(data.get("farmer_id", 0))
        field_id = int(data.get("field_id", 0))
        crop = (data.get("crop") or "").strip()
        year = int(data.get("year"))
        investment = float(data.get("investment"))
        production = float(data.get("production"))
        price = float(data.get("price"))
    except (TypeError, ValueError, KeyError):
        return jsonify({"error": "Invalid or missing production fields"}), 400

    revenue = production * price
    profit = revenue - investment

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO YearlyProduction
        (farmer_id, field_id, crop_name, year, investment,
         production_kg, selling_price, revenue, profit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (farmer_id, field_id, crop, year, investment, production, price, revenue, profit),
    )
    conn.commit()
    conn.close()

    return jsonify({"message": "Production stored", "revenue": revenue, "profit": profit})


@app.route("/field_growth/<int:farmer_id>")
def field_growth(farmer_id):
    """Return yearly production and profit for a farmer's fields.

    Response is a list of objects: {year, production, investment, profit, crop}.
    """

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT year, production_kg, investment, profit, crop_name
        FROM YearlyProduction
        WHERE farmer_id = ?
        ORDER BY year
        """,
        (farmer_id,),
    )
    rows = cur.fetchall()
    conn.close()

    data = [
        {
            "year": row[0],
            "production": row[1],
            "investment": row[2],
            "profit": row[3],
            "crop": row[4],
        }
        for row in rows
    ]

    return jsonify(data)


# ------------- Auth & profile pages -------------


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        form = request.form

        name = (form.get("name") or "").strip()
        phone = (form.get("phone") or "").strip()
        email = (form.get("email") or "").strip()
        village = (form.get("village") or "").strip()
        district = (form.get("district") or "").strip()
        state = (form.get("state") or "").strip()
        pincode = (form.get("pincode") or "").strip()
        password = form.get("password") or ""
        captcha_input = (form.get("captcha") or "").strip().upper()
        expected_captcha = (session.get("captcha") or "").upper()

        if not name or not email or not password:
            flash("Name, email and password are required.", "danger")
        elif captcha_input != expected_captcha:
            flash("Captcha mismatch. Please try again.", "danger")
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM Farmers WHERE email = ?", (email,))
            if cur.fetchone():
                conn.close()
                flash("Email already registered. Please log in.", "warning")
                return redirect(url_for("login"))

            password_hash = generate_password_hash(password)
            cur.execute(
                """
                INSERT INTO Farmers (name, phone, email, village, district, state, pincode, password_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (name, phone, email, village, district, state, pincode, password_hash),
            )
            farmer_id = cur.lastrowid

            otp = generate_otp()
            expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
            cur.execute(
                """
                INSERT INTO EmailOtps (farmer_id, email, otp, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (farmer_id, email, otp, expires_at),
            )
            conn.commit()
            conn.close()

            send_otp_email(email, otp)
            flash("Signup successful. Please verify the OTP sent to your email.", "success")
            return redirect(url_for("verify_otp", email=email))

    captcha = generate_captcha()
    session["captcha"] = captcha
    return render_template("signup.html", captcha=captcha, farmer=get_current_farmer())


@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    email = request.args.get("email") or (request.form.get("email") if request.method == "POST" else "")
    if request.method == "POST":
        otp_input = (request.form.get("otp") or "").strip()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, farmer_id, otp, expires_at, used FROM EmailOtps
            WHERE email = ? ORDER BY created_at DESC LIMIT 1
            """,
            (email,),
        )
        row = cur.fetchone()
        if not row:
            conn.close()
            flash("No OTP found for this email.", "danger")
        else:
            otp_db = row[2]
            expires_at = datetime.fromisoformat(row[3]) if row[3] else None
            used = row[4]
            if used:
                flash("This OTP has already been used.", "danger")
            elif expires_at and datetime.utcnow() > expires_at:
                flash("OTP has expired. Please sign up again.", "danger")
            elif otp_input != otp_db:
                flash("Invalid OTP.", "danger")
            else:
                farmer_id = row[1]
                cur.execute("UPDATE Farmers SET is_verified = 1 WHERE id = ?", (farmer_id,))
                cur.execute("UPDATE EmailOtps SET used = 1 WHERE id = ?", (row[0],))
                conn.commit()
                conn.close()
                flash("Email verified. You can now log in.", "success")
                return redirect(url_for("login"))

    return render_template("verify_otp.html", email=email, farmer=get_current_farmer())


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        captcha_input = (request.form.get("captcha") or "").strip().upper()
        expected_captcha = (session.get("captcha") or "").upper()

        if captcha_input != expected_captcha:
            flash("Captcha mismatch. Please try again.", "danger")
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, password_hash, is_verified FROM Farmers WHERE email = ?", (email,))
            row = cur.fetchone()
            conn.close()
            if not row or not row[1] or not check_password_hash(row[1], password):
                flash("Invalid email or password.", "danger")
            elif not row[2]:
                flash("Please verify your email via OTP before logging in.", "warning")
            else:
                session["farmer_id"] = row[0]
                flash("Logged in successfully.", "success")
                next_url = request.args.get("next") or url_for("home")
                return redirect(next_url)

    captcha = generate_captcha()
    session["captcha"] = captcha
    return render_template("login.html", captcha=captcha, farmer=get_current_farmer())


@app.route("/logout")
def logout():
    session.pop("farmer_id", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route("/profile")
@login_required
def profile():
    farmer = get_current_farmer()
    if not farmer:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Fields WHERE farmer_id = ?", (farmer["id"],))
    fields = cur.fetchall()

    cur.execute(
        """SELECT year, crop_name, production_kg, investment, profit FROM YearlyProduction
        WHERE farmer_id = ? ORDER BY year""",
        (farmer["id"],),
    )
    production = cur.fetchall()

    cur.execute(
        "SELECT disease, confidence, created_at FROM DiseaseDetections ORDER BY created_at DESC LIMIT 5"
    )
    recent_disease = cur.fetchall()
    conn.close()

    return render_template(
        "profile.html",
        farmer=farmer,
        fields=fields,
        production=production,
        recent_disease=recent_disease,
    )


def _call_openai(messages: list) -> str:
    """Call OpenAI ChatCompletion (GPT-4o-mini, fast & cheap)."""
    if not OPENAI_API_KEY:
        return ""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        print(f"[OpenAI error] {exc}")
        return ""


def _call_gemini(prompt: str) -> str:
    """Call Google Gemini as fallback."""
    if not GEMINI_API_KEY:
        print("[Gemini] No API key configured")
        return ""
    import time as _time
    models = ["gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-2.0-flash"]
    base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    for model in models:
        for attempt in range(2):
            try:
                url = f"{base_url}/{model}:generateContent"
                resp = requests.post(url, headers=headers, params=params, json=payload, timeout=25)
                if resp.status_code == 429:
                    print(f"[Gemini] 429 rate-limit on {model} (attempt {attempt + 1})")
                    _time.sleep(3 * (attempt + 1))
                    continue
                resp.raise_for_status()
                data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                if text:
                    return text
            except Exception as exc:
                print(f"[Gemini error] {model}: {exc}")
                break  # try next model
    return ""


def call_llm(system_prompt: str, user_message: str) -> str:
    """Try OpenAI first, then Gemini. Returns the bot response text."""
    # 1) OpenAI (primary — reliable, no rate-limit issues on paid key)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    result = _call_openai(messages)
    if result:
        return result

    # 2) Gemini fallback
    full_prompt = system_prompt + "\n\nUser: " + user_message
    result = _call_gemini(full_prompt)
    if result:
        return result

    return "I'm sorry, I couldn't process your request right now. Both AI services are temporarily unavailable. Please try again in a moment."


# ------------- API: Chatbot + weather agent -------------

AGRI_SYSTEM_PROMPT = """You are **Krishi AI** — an expert Precision Agriculture Assistant built for Indian farmers.

Your capabilities:
• Crop advisory: recommend crops based on soil, climate, season, and region
• Disease diagnosis: help identify plant diseases from described symptoms
• Weather guidance: interpret weather data and give actionable farming advice
• Market insights: explain MSP (Minimum Support Price), mandi rates, and selling strategies
• Government schemes: inform about PM-KISAN, PMFBY, Soil Health Card, KCC, eNAM, RKVY, etc.
• Organic & sustainable farming: composting, vermicomposting, IPM, crop rotation tips
• Water & irrigation: drip vs flood, rainwater harvesting, scheduling
• Fertilizer & soil health: NPK ratios, soil testing interpretation, micronutrient management
• Post-harvest: storage, grading, cold chain, value-addition ideas

Rules:
1. Always answer in clear, simple English that a rural farmer can understand.
2. Use bullet points and short paragraphs for readability.
3. Include specific numbers (cost/kg, yield/hectare, scheme amounts) when possible.
4. If the user provides a PIN code or location, tailor advice to that region.
5. If unsure, say so honestly and suggest contacting the local KVK (Krishi Vigyan Kendra).
6. Keep answers concise — under 250 words unless the farmer asks for detail.
7. Be encouraging and supportive. Farming is hard work.
"""


@app.route("/api/chatbot", methods=["POST"])
def api_chatbot():
    data = request.json or request.form
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"response": "Please type a question or enter your village PIN code.", "weather": None})

    # Detect PIN code for weather lookup
    pincode = None
    if message.isdigit() and len(message) == 6:
        pincode = message

    weather = None
    weather_context = ""
    if pincode:
        weather = get_weather_by_pincode(pincode)
        if "error" not in weather:
            suggestion = build_farming_suggestion(weather)
            weather_context = (
                f"\n[Weather data for PIN {pincode}: "
                f"Temp {weather['temperature']}°C, Humidity {weather['humidity']}%, "
                f"Condition {weather['description']}, Rain {weather['rain']} mm, "
                f"Wind {weather['wind_speed']} m/s. "
                f"Farming suggestion: {suggestion}]\n"
            )

    user_content = (weather_context + f"Farmer's message: {message}") if weather_context else message

    bot_text = call_llm(AGRI_SYSTEM_PROMPT, user_content)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ChatbotLogs (user_message, bot_response, pincode, created_at) VALUES (?, ?, ?, datetime('now'))",
        (message, bot_text, pincode),
    )

    if weather and "error" not in weather:
        cur.execute(
            """
            INSERT INTO WeatherLogs (pincode, temperature, humidity, wind_speed, rain, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                pincode,
                weather.get("temperature"),
                weather.get("humidity"),
                weather.get("wind_speed"),
                weather.get("rain"),
                weather.get("description"),
            ),
        )

    conn.commit()
    conn.close()

    return jsonify({"response": bot_text, "weather": weather})


@app.route("/api/location-insights", methods=["POST"])
def api_location_insights():
    """Return basic location, weather and soil hints for a lat/lon from the drone map.

    This powers the Satellite Farm Monitoring panel when a user marks a field location.
    """

    data = request.get_json(force=True) or {}
    lat = float(data.get("lat", 0.0))
    lon = float(data.get("lon", 0.0))

    weather = get_weather_by_coords(lat, lon)
    if "error" in weather:
        return jsonify({"error": weather["error"]}), 400

    suggestion = build_farming_suggestion(weather)

    # Very lightweight "soil" hint based on rainfall and humidity
    r = float(weather.get("rain", 0.0))
    h = float(weather.get("humidity", 0.0))
    if r > 5 and h > 75:
        soil_hint = "Likely heavier / moisture-retentive soils; manage drainage and watch for fungal diseases."
    elif r < 1 and h < 50:
        soil_hint = "Conditions tend to be drier; drought-tolerant crops and mulching are beneficial."
    else:
        soil_hint = "Moderate moisture conditions suitable for most field crops with balanced irrigation."

    return jsonify(
        {
            "lat": lat,
            "lon": lon,
            "place": weather.get("place_name", ""),
            "weather_summary": f"{weather.get('description', '')}, {weather.get('temperature', 0)}°C, humidity {weather.get('humidity', 0)}%",
            "farming_advice": suggestion,
            "soil_hint": soil_hint,
        }
    )


# ------------- Static file route (optional) -------------


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_DIR / "static", filename)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
