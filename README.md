# AI Precision Agriculture Dashboard

This is a simple Flask-based precision agriculture dashboard with:
- Rule-based crop recommendation
- Lightweight image-based disease detection (Pillow/numpy)
- Lightweight drone image analysis (Pillow/numpy)

## Setup

1. Create and activate a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   # Windows PowerShell
   .venv\\Scripts\\Activate.ps1
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Run the app

From the project root:

```bash
python backend/app.py
```

Then open the dashboard in your browser at:

- http://127.0.0.1:5000/

Use the three cards on the page to:
- Get a crop recommendation from basic weather/soil inputs
- Upload a plant image for simple disease classification
- Upload a drone/field image for simple stress analysis
