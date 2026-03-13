# Smart Krishi AI – Agriculture Monitoring Web App

Full-stack AI-powered agriculture monitoring platform for Indian farmers, built with Flask, SQLite, HTML/CSS/JS, and optional ML models.

## Project Structure

- backend/
  - app.py – Flask app, routes, DB init
  - crop_recommendation.py – ML + rule-based crop recommendation
  - disease_model.py – ResNet50 integration with safe fallback
  - drone_analysis.py – Drone image analysis (OpenCV or Pillow)
  - weather_agent.py – OpenWeather API wrapper and farming suggestions
- models/
  - resnet50_disease_model.h5 (optional, add your trained model)
  - crop_recommendation_model.pkl (optional, sklearn model)
- frontend/
  - index.html
  - crop_recommendation.html
  - disease_detection.html
  - yield_dashboard.html
  - drone_monitoring.html
  - about.html
- static/
  - style.css
  - dashboard.js
- uploads/images/ – uploaded images
- database/
  - agriculture.db (created on first run)

## Setup

```bash
cd agriculture-ai-app
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

Set your OpenWeather API key (replace with your key):

```bash
$env:OPENWEATHER_API_KEY = "YOUR_KEY_HERE"  # PowerShell
```

## Run

```bash
cd backend
python app.py
```

Then open:

- http://127.0.0.1:5000/

## Testing Metrics

Validation run date: 2026-03-12

Scope: Crop Monitoring dataset integration and API response sanity check.

Validation command:

```bash
cd agriculture-ai-app/backend
python -c "import json; from crop_price_analysis import get_available_filters, get_monitoring_dashboard; filters = get_available_filters(); data = get_monitoring_dashboard('Rice', 'Andhra Pradesh', 'Cotton'); print(json.dumps({'production_crops': len(filters['production_crops']), 'states': len(filters['states']), 'price_crops': len(filters['price_crops']), 'soil_records': data['soil_profile']['records'], 'yearly_points': len(data['production']['yearly']), 'daily_prices': len(data['market_price']['daily'])}, indent=2))"
```

Observed metrics:

- production_crops: 80
- states: 7
- price_crops: 1
- soil_records (Andhra Pradesh): 1
- yearly_points (Rice, Andhra Pradesh): 18
- daily_prices (Cotton): 15

Notes:

- Monitoring API data is now sourced from `agriculture-ai-app/backend/` CSV files.
- Current `Agmarknet_prices.csv` sample contains only one commodity (`Cotton`), so commodity filter options are limited to that dataset.

You will see:

- Home page with navigation + floating chatbot
- Crop recommendation form
- Disease detection upload
- Yield dashboard (Chart.js, driven by SQLite)
- Drone monitoring upload
- About page

ML models are optional – if no TensorFlow/sklearn models are present, the app falls back to safe heuristic logic so it still runs end-to-end.
