import os
import pickle
from pathlib import Path

import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "crop_recommendation_model.pkl"

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    if MODEL_PATH.exists():
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
    return _model


# ---------------------------------------------------------------------------
# Comprehensive crop knowledge base
# ---------------------------------------------------------------------------
CROP_DATABASE = {
    "Paddy": {
        "water_requirement": "High (1200-1800 mm)",
        "fertilizer_suggestion": "Urea 130kg, DAP 60kg, MOP 40kg per hectare",
        "season": "Kharif (June-November)",
        "ideal_temp": (22, 32),
        "ideal_rainfall": (150, 300),
        "ideal_ph": (5.0, 6.5),
        "ideal_humidity": (60, 95),
        "ideal_soils": ["clay", "clayey", "loam", "loamy"],
        "duration_days": "120-150 days",
        "avg_yield_per_hectare_kg": 4500,
        "msp_per_kg": 23.20,  # MSP 2025-26
        "avg_cost_per_hectare": 52000,
        "farming_plan": [
            "Land preparation: Plough field 2-3 times, puddle & level (Week 1-2)",
            "Nursery raising: Prepare nursery bed, sow pre-treated seeds (Week 1-3)",
            "Transplanting: Transplant 25-30 day old seedlings 2-3 per hill (Week 4)",
            "Water management: Maintain 5cm standing water during vegetative stage",
            "1st Fertilizer dose: Apply 50% N + full P + full K at transplanting",
            "2nd Fertilizer dose: Apply 25% N at tillering (30 DAT)",
            "3rd Fertilizer dose: Apply 25% N at panicle initiation (55-60 DAT)",
            "Weed management: Hand weeding or apply Butachlor at 3 DAT",
            "Pest monitoring: Watch for stem borer, BPH, blast disease",
            "Drain field 15 days before harvest, harvest at 80% grain maturity",
        ],
        "govt_schemes": [
            {"name": "PM-KISAN", "benefit": "₹6,000/year direct income support in 3 installments", "link": "https://pmkisan.gov.in"},
            {"name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)", "benefit": "Crop insurance at 2% premium for Kharif, covers natural calamities", "link": "https://pmfby.gov.in"},
            {"name": "National Food Security Mission (NFSM)", "benefit": "Subsidy on seeds, micronutrients, soil ameliorants (up to 50%)", "link": "https://nfsm.gov.in"},
            {"name": "Soil Health Card Scheme", "benefit": "Free soil testing and nutrient-based fertilizer recommendations", "link": "https://soilhealth.dac.gov.in"},
            {"name": "PM-KUSUM", "benefit": "60% subsidy on solar pump sets for irrigation", "link": "https://mnre.gov.in/solar/schemes"},
        ],
    },
    "Wheat": {
        "water_requirement": "Moderate (450-650 mm)",
        "fertilizer_suggestion": "Urea 110kg, DAP 50kg, MOP 30kg per hectare",
        "season": "Rabi (November-April)",
        "ideal_temp": (12, 25),
        "ideal_rainfall": (50, 100),
        "ideal_ph": (6.0, 7.5),
        "ideal_humidity": (40, 70),
        "ideal_soils": ["loam", "loamy", "clay", "clayey", "black"],
        "duration_days": "120-140 days",
        "avg_yield_per_hectare_kg": 4800,
        "msp_per_kg": 23.50,
        "avg_cost_per_hectare": 38000,
        "farming_plan": [
            "Land preparation: Fine-till soil 2-3 times, level with planker (Week 1)",
            "Seed treatment: Treat with Carboxin + Thiram @2g/kg against smut diseases",
            "Sowing: Drill sow at 100kg/ha, row spacing 22.5cm, depth 5cm (Nov 1-25)",
            "First irrigation (Crown Root): 20-25 DAS — critical irrigation",
            "1st Fertilizer: Apply 50% N + full P + full K at sowing",
            "Second irrigation: Tillering stage (40-45 DAS)",
            "2nd Fertilizer: Apply 25% N at first irrigation",
            "Third irrigation: Jointing stage (60-65 DAS)",
            "3rd Fertilizer: Apply remaining 25% N at tillering",
            "Fourth irrigation: Flowering (80-85 DAS), Fifth: Grain filling (100-105 DAS)",
            "Weed control: Apply Sulfosulfuron @25g/ha at 30-35 DAS",
            "Harvest at golden-yellow color, moisture 14% (April)",
        ],
        "govt_schemes": [
            {"name": "PM-KISAN", "benefit": "₹6,000/year direct income support in 3 installments", "link": "https://pmkisan.gov.in"},
            {"name": "PMFBY", "benefit": "Crop insurance at 1.5% premium for Rabi crops", "link": "https://pmfby.gov.in"},
            {"name": "National Food Security Mission", "benefit": "Subsidy on HYV seeds (up to 50%), micro-nutrients, sprinkler sets", "link": "https://nfsm.gov.in"},
            {"name": "Sub-Mission on Agricultural Mechanization (SMAM)", "benefit": "50-80% subsidy on farm machinery (rotavator, seed drill)", "link": "https://agrimachinery.nic.in"},
            {"name": "Soil Health Card Scheme", "benefit": "Free soil testing and nutrient recommendations", "link": "https://soilhealth.dac.gov.in"},
        ],
    },
    "Maize": {
        "water_requirement": "Moderate (500-800 mm)",
        "fertilizer_suggestion": "Urea 120kg, DAP 60kg, MOP 40kg per hectare",
        "season": "Kharif / Rabi / Spring",
        "ideal_temp": (21, 32),
        "ideal_rainfall": (60, 140),
        "ideal_ph": (5.5, 7.5),
        "ideal_humidity": (50, 80),
        "ideal_soils": ["loam", "loamy", "sandy", "sandy loam"],
        "duration_days": "90-120 days",
        "avg_yield_per_hectare_kg": 5500,
        "msp_per_kg": 21.82,
        "avg_cost_per_hectare": 35000,
        "farming_plan": [
            "Land preparation: Plough twice, form ridges at 60cm spacing",
            "Seed selection: Use hybrid seeds (DHM-117, HQPM-1) at 20kg/ha",
            "Sowing: Sow on ridges at 60×20cm spacing, 5cm depth (June for Kharif)",
            "Thinning: Keep one healthy plant per hill at 10-15 DAS",
            "1st Fertilizer: Apply 25% N + full P + full K at sowing",
            "2nd Fertilizer: Apply 50% N at knee-high stage (30-35 DAS)",
            "3rd Fertilizer: Apply 25% N at tasseling (55-60 DAS)",
            "Irrigation: Provide at knee-high, tasseling, and grain-filling stages",
            "Weed control: Apply Atrazine @1kg/ha pre-emergence (within 3 DAS)",
            "Pest watch: Monitor for fall armyworm, stem borer, shoot fly",
            "Harvest: Cobs dry on plant, moisture below 20% (90-120 DAS)",
        ],
        "govt_schemes": [
            {"name": "PM-KISAN", "benefit": "₹6,000/year direct income support", "link": "https://pmkisan.gov.in"},
            {"name": "PMFBY", "benefit": "Crop insurance at 2% premium", "link": "https://pmfby.gov.in"},
            {"name": "NFSM – Coarse Cereals", "benefit": "Subsidy on hybrid seeds, farm machinery, and demonstrations", "link": "https://nfsm.gov.in"},
            {"name": "Rashtriya Krishi Vikas Yojana (RKVY)", "benefit": "State-level agricultural development & infrastructure support", "link": "https://rkvy.nic.in"},
            {"name": "e-NAM", "benefit": "Online mandi platform for better price discovery and direct selling", "link": "https://enam.gov.in"},
        ],
    },
    "Cotton": {
        "water_requirement": "Moderate (700-1200 mm)",
        "fertilizer_suggestion": "Urea 100kg, SSP 150kg, MOP 50kg per hectare",
        "season": "Kharif (April-December)",
        "ideal_temp": (25, 38),
        "ideal_rainfall": (50, 100),
        "ideal_ph": (6.0, 8.0),
        "ideal_humidity": (40, 70),
        "ideal_soils": ["black", "loam", "loamy", "sandy", "sandy loam"],
        "duration_days": "150-180 days",
        "avg_yield_per_hectare_kg": 2000,
        "msp_per_kg": 70.80,
        "avg_cost_per_hectare": 45000,
        "farming_plan": [
            "Land preparation: Deep ploughing, 2-3 harrowing, form ridges and furrows",
            "Seed treatment: Treat with Imidacloprid @5ml/kg, Trichoderma @10g/kg",
            "Sowing: Dibble at 90×60cm or 120×45cm spacing (April-May)",
            "Thinning: Maintain one plant/hill at 15-20 DAS",
            "1st Fertilizer: Apply 25% N + full P + full K at sowing",
            "2nd Fertilizer: Apply 25% N at squaring (45-50 DAS)",
            "3rd Fertilizer: Apply 50% N at flowering (70-80 DAS)",
            "Irrigation: Provide at flowering, boll development stages",
            "Pest management: Monitor for bollworm (install pheromone traps), whitefly",
            "Detopping: Remove apical bud at 90-100 DAS to divert energy to bolls",
            "Harvest: Pick open bolls in 3-4 rounds when 60% bolls open",
        ],
        "govt_schemes": [
            {"name": "PM-KISAN", "benefit": "₹6,000/year direct income support", "link": "https://pmkisan.gov.in"},
            {"name": "PMFBY", "benefit": "Crop insurance at 2% premium for Kharif", "link": "https://pmfby.gov.in"},
            {"name": "Technology Mission on Cotton (TMC)", "benefit": "Subsidy on Bt cotton seeds, IPM tools, and drip irrigation", "link": "https://texmin.nic.in"},
            {"name": "Cotton Corporation of India (CCI)", "benefit": "MSP procurement support when market prices fall below MSP", "link": "https://cotcorp.org.in"},
            {"name": "MIDH", "benefit": "Subsidy on micro-irrigation (drip/sprinkler) up to 55%", "link": "https://midh.gov.in"},
        ],
    },
    "Jowar": {
        "water_requirement": "Low (400-600 mm)",
        "fertilizer_suggestion": "Urea 80kg, DAP 40kg, MOP 20kg per hectare",
        "season": "Kharif / Rabi",
        "ideal_temp": (25, 35),
        "ideal_rainfall": (60, 120),
        "ideal_ph": (6.0, 8.0),
        "ideal_humidity": (40, 70),
        "ideal_soils": ["black", "loam", "loamy", "clay", "clayey"],
        "duration_days": "100-120 days",
        "avg_yield_per_hectare_kg": 2800,
        "msp_per_kg": 33.18,
        "avg_cost_per_hectare": 25000,
        "farming_plan": [
            "Land preparation: Plough once deep + 2 harrowing, level field",
            "Seed treatment: Treat with Thiram @3g/kg against grain smut",
            "Sowing: Drill sow at 45×15cm, seed rate 8-10 kg/ha (June-July)",
            "Thinning: Maintain 15cm plant-to-plant spacing at 15 DAS",
            "Fertilizer: Apply 50% N + full P + full K at sowing, 50% N at 30 DAS",
            "Weed control: One hand weeding at 20-25 DAS + Atrazine pre-emergence",
            "Irrigation: Generally rainfed; critical irrigation at flowering if dry spell",
            "Pest watch: Shoot fly (early sowing helps avoid), stem borer",
            "Bird scaring at grain maturity",
            "Harvest at physiological maturity (black layer on grain), sun dry to 12%",
        ],
        "govt_schemes": [
            {"name": "PM-KISAN", "benefit": "₹6,000/year direct income support", "link": "https://pmkisan.gov.in"},
            {"name": "PMFBY", "benefit": "Crop insurance at 2% premium", "link": "https://pmfby.gov.in"},
            {"name": "NFSM – Nutri Cereals / Millets", "benefit": "Subsidy on improved seeds, demonstrations, up to ₹7,500/ha", "link": "https://nfsm.gov.in"},
            {"name": "International Year of Millets initiatives", "benefit": "Marketing & processing support, cluster development", "link": "https://millets.dacnet.nic.in"},
            {"name": "e-NAM", "benefit": "Online mandi for better price transparency", "link": "https://enam.gov.in"},
        ],
    },
    "Millets": {
        "water_requirement": "Very Low (300-500 mm)",
        "fertilizer_suggestion": "Urea 60kg, DAP 30kg, MOP 15kg per hectare",
        "season": "Kharif (June-October)",
        "ideal_temp": (28, 38),
        "ideal_rainfall": (30, 80),
        "ideal_ph": (5.5, 7.5),
        "ideal_humidity": (30, 65),
        "ideal_soils": ["sandy", "sandy loam", "loam", "loamy"],
        "duration_days": "70-90 days",
        "avg_yield_per_hectare_kg": 1800,
        "msp_per_kg": 25.50,
        "avg_cost_per_hectare": 18000,
        "farming_plan": [
            "Land preparation: One deep ploughing + 2 light harrowing",
            "Seed treatment: Treat with Carbendazim @2g/kg against grain smut",
            "Sowing: Line sow at 30×10cm, seed rate 4-5 kg/ha (June-July)",
            "Thinning: Maintain 10cm spacing at 10-15 DAS",
            "Fertilizer: Apply 50% N + full P + full K at sowing, 50% N at 30 DAS",
            "Weed control: One hand weeding at 15-20 DAS",
            "Irrigation: Mostly rainfed; protective irrigation at flowering if needed",
            "Pest monitoring: Shoot fly (early sowing recommended)",
            "Harvest at full grain maturity, thresh and dry to 12% moisture",
        ],
        "govt_schemes": [
            {"name": "PM-KISAN", "benefit": "₹6,000/year direct income support", "link": "https://pmkisan.gov.in"},
            {"name": "PMFBY", "benefit": "Crop insurance at 2% premium", "link": "https://pmfby.gov.in"},
            {"name": "NFSM – Nutri Cereals", "benefit": "₹7,500/ha for demonstrations, seed subsidy up to 50%", "link": "https://nfsm.gov.in"},
            {"name": "Millet Mission India", "benefit": "Processing infrastructure, marketing support, value chain development", "link": "https://millets.dacnet.nic.in"},
            {"name": "RKVY-RAFTAAR", "benefit": "Agri-entrepreneurship support for millet startups", "link": "https://rkvy.nic.in"},
        ],
    },
    "Sugarcane": {
        "water_requirement": "Very High (1500-2500 mm)",
        "fertilizer_suggestion": "Urea 175kg, SSP 200kg, MOP 80kg per hectare",
        "season": "Planted: Oct-Mar, Harvested after 12-18 months",
        "ideal_temp": (25, 38),
        "ideal_rainfall": (100, 250),
        "ideal_ph": (6.0, 8.0),
        "ideal_humidity": (60, 90),
        "ideal_soils": ["loam", "loamy", "clay", "clayey", "black"],
        "duration_days": "360-540 days",
        "avg_yield_per_hectare_kg": 75000,
        "msp_per_kg": 3.40,
        "avg_cost_per_hectare": 90000,
        "farming_plan": [
            "Land preparation: Deep ploughing, cross harrowing, open furrows at 90cm",
            "Sett preparation: Select disease-free 3-bud setts, treat with Carbendazim",
            "Planting: Place 2 setts end-to-end in furrows, cover with 5cm soil",
            "1st Irrigation: Immediately after planting, keep moist for 45 days",
            "1st Fertilizer: Apply full P + K + 1/3 N at planting",
            "Earthing up: First at 45 DAP, second at 90 DAP",
            "2nd Fertilizer: Apply 1/3 N at 45 DAP, remaining 1/3 N at 90 DAP",
            "Trash mulching: Apply cane trash between rows to conserve moisture",
            "Propping: Support tall canes with dried leaves tying at 8 months",
            "Irrigation: 10-12 irrigations across crop life (furrow or drip)",
            "Harvest: Cut at ground level when juice brix >18%, avoid topping",
        ],
        "govt_schemes": [
            {"name": "PM-KISAN", "benefit": "₹6,000/year direct income support", "link": "https://pmkisan.gov.in"},
            {"name": "Sugar FRP (Fair & Remunerative Price)", "benefit": "₹340/quintal guaranteed price from sugar mills", "link": "https://dfpd.gov.in"},
            {"name": "MIDH – Micro Irrigation", "benefit": "55% subsidy on drip irrigation for sugarcane", "link": "https://midh.gov.in"},
            {"name": "Sugar Development Fund", "benefit": "Loans for sugar mills & cane development at concessional rates", "link": "https://dfpd.gov.in"},
            {"name": "PMFBY", "benefit": "Crop insurance coverage for sugarcane", "link": "https://pmfby.gov.in"},
        ],
    },
    "Groundnut": {
        "water_requirement": "Low-Moderate (450-600 mm)",
        "fertilizer_suggestion": "Urea 25kg, SSP 250kg, Gypsum 200kg per hectare",
        "season": "Kharif (June-Oct) / Summer (Jan-May)",
        "ideal_temp": (25, 35),
        "ideal_rainfall": (50, 120),
        "ideal_ph": (5.5, 7.0),
        "ideal_humidity": (50, 80),
        "ideal_soils": ["sandy", "sandy loam", "loam", "loamy"],
        "duration_days": "100-130 days",
        "avg_yield_per_hectare_kg": 2200,
        "msp_per_kg": 62.75,
        "avg_cost_per_hectare": 40000,
        "farming_plan": [
            "Land preparation: 2 deep ploughings + leveling, add FYM @5t/ha",
            "Seed treatment: Treat with Carbendazim @2g/kg + Rhizobium culture",
            "Sowing: Sow at 30×10cm spacing, 80-100 kg/ha kernels",
            "Gypsum: Apply 200kg/ha at pegging stage (45 DAS) — critical for pod filling",
            "Fertilizer: Apply full N + P + K at sowing (groundnut is legume, fixes N)",
            "Weed control: Pendimethalin pre-emergence + one hand weeding at 25-30 DAS",
            "Earthing up at 30-35 DAS to help pegging",
            "Irrigation: At flowering and pegging stages (if summer crop)",
            "Pest/disease: Watch for tikka leaf spot, collar rot, leaf miner",
            "Harvest when 75% pods mature (shell hardening test), dry to 8% moisture",
        ],
        "govt_schemes": [
            {"name": "PM-KISAN", "benefit": "₹6,000/year direct income support", "link": "https://pmkisan.gov.in"},
            {"name": "PMFBY", "benefit": "Crop insurance at 2% premium", "link": "https://pmfby.gov.in"},
            {"name": "National Mission on Oilseeds & Oil Palm (NMOOP)", "benefit": "Subsidy on certified seeds (up to 50%), mini oil mills", "link": "https://nmoop.gov.in"},
            {"name": "RKVY", "benefit": "Infrastructure support for oilseed processing at state level", "link": "https://rkvy.nic.in"},
            {"name": "e-NAM", "benefit": "Online mandi for better price discovery", "link": "https://enam.gov.in"},
        ],
    },
}

# Default for unknown crops
_DEFAULT_CROP = {
    "water_requirement": "Moderate",
    "fertilizer_suggestion": "Balanced NPK",
    "season": "Kharif/Rabi",
    "ideal_temp": (20, 35),
    "ideal_rainfall": (50, 150),
    "ideal_ph": (5.5, 7.5),
    "ideal_humidity": (40, 80),
    "ideal_soils": ["loam", "loamy"],
    "duration_days": "90-120 days",
    "avg_yield_per_hectare_kg": 3000,
    "msp_per_kg": 25.00,
    "avg_cost_per_hectare": 35000,
    "farming_plan": ["Follow standard agricultural practices for your region"],
    "govt_schemes": [
        {"name": "PM-KISAN", "benefit": "₹6,000/year direct income support", "link": "https://pmkisan.gov.in"},
        {"name": "PMFBY", "benefit": "Crop insurance at low premium", "link": "https://pmfby.gov.in"},
    ],
}


# ---------------------------------------------------------------------------
# Suitability scoring engine
# ---------------------------------------------------------------------------

def _score_crop(crop_name: str, temp: float, humidity: float, rainfall: float,
                soil: str, ph: float) -> float:
    """Score how suitable a crop is for given conditions (0-100)."""
    info = CROP_DATABASE.get(crop_name, _DEFAULT_CROP)
    score = 0.0
    s = (soil or "").lower()

    # Temperature score (30 pts)
    t_lo, t_hi = info["ideal_temp"]
    if t_lo <= temp <= t_hi:
        score += 30
    elif abs(temp - t_lo) <= 5 or abs(temp - t_hi) <= 5:
        score += 15
    elif abs(temp - t_lo) <= 10 or abs(temp - t_hi) <= 10:
        score += 5

    # Rainfall score (25 pts)
    r_lo, r_hi = info["ideal_rainfall"]
    if r_lo <= rainfall <= r_hi:
        score += 25
    elif abs(rainfall - r_lo) <= 30 or abs(rainfall - r_hi) <= 30:
        score += 12
    elif abs(rainfall - r_lo) <= 60 or abs(rainfall - r_hi) <= 60:
        score += 5

    # pH score (20 pts)
    if ph and ph > 0:
        p_lo, p_hi = info["ideal_ph"]
        if p_lo <= ph <= p_hi:
            score += 20
        elif abs(ph - p_lo) <= 1 or abs(ph - p_hi) <= 1:
            score += 10
        elif abs(ph - p_lo) <= 2 or abs(ph - p_hi) <= 2:
            score += 4

    # Humidity score (15 pts)
    h_lo, h_hi = info["ideal_humidity"]
    if h_lo <= humidity <= h_hi:
        score += 15
    elif abs(humidity - h_lo) <= 15 or abs(humidity - h_hi) <= 15:
        score += 7

    # Soil match (10 pts)
    if s in info.get("ideal_soils", []):
        score += 10
    elif any(word in s for word in info.get("ideal_soils", [])):
        score += 5

    return round(score, 1)


def _estimate_economics(crop_name: str, area_hectares: float = 1.0,
                        investment_override: float = None):
    """Estimate cost, revenue, and profit for a crop."""
    info = CROP_DATABASE.get(crop_name, _DEFAULT_CROP)

    cost = investment_override if investment_override else info["avg_cost_per_hectare"] * area_hectares
    expected_yield = info["avg_yield_per_hectare_kg"] * area_hectares
    msp = info["msp_per_kg"]
    revenue = expected_yield * msp
    profit = revenue - cost

    return {
        "estimated_cost": round(cost),
        "expected_yield_kg": round(expected_yield),
        "msp_per_kg": msp,
        "estimated_revenue": round(revenue),
        "estimated_profit": round(profit),
        "roi_percent": round((profit / cost) * 100, 1) if cost > 0 else 0,
    }


# ---------------------------------------------------------------------------
# Original rule-based engine (used as primary scorer)
# ---------------------------------------------------------------------------

def _rule_based_crop(
    temp: float,
    humidity: float,
    rainfall: float,
    soil: str,
    ph: float,
    ec: float,
    carbon: float,
    ca: float,
    mg: float,
) -> str:
    s = (soil or "").lower()

    if ph and ph < 5.5 and rainfall > 150:
        return "Paddy"
    if 5.5 <= ph <= 7.5 and carbon and carbon >= 0.8 and 80 <= rainfall <= 140:
        if s in {"loam", "loamy", "black"}:
            return "Jowar"
        return "Maize"
    if s in {"sandy", "sandy loam"} and rainfall < 80:
        if temp > 30:
            return "Millets"
        return "Cotton"
    if 18 <= temp <= 24 and 50 <= rainfall <= 100 and 6.0 <= (ph or 6.0) <= 7.5:
        return "Wheat"
    if ec and ec > 1.5:
        return "Cotton"
    if s in {"clay", "clayey"} and rainfall > 150 and humidity > 70:
        return "Paddy"
    if s in {"loam", "loamy", "black"} and 60 <= rainfall <= 120 and 24 <= temp <= 32:
        return "Jowar"
    if rainfall < 60 and temp > 30:
        return "Cotton"
    if 18 <= temp <= 24 and 50 <= rainfall <= 100:
        return "Wheat"
    return "Maize"


# ---------------------------------------------------------------------------
# Single crop recommendation (backward compatible)
# ---------------------------------------------------------------------------

def recommend_crop(
    temp: float, humidity: float, rainfall: float, soil: str,
    ph: float, ec: float, carbon: float, ca: float, mg: float,
) -> str:
    model = _load_model()
    ph = ph or 0.0
    ec = ec or 0.0
    carbon = carbon or 0.0
    ca = ca or 0.0
    mg = mg or 0.0

    if model is None:
        return _rule_based_crop(temp, humidity, rainfall, soil, ph, ec, carbon, ca, mg)

    features = np.array([[temp, humidity, rainfall, ph, ec, carbon, ca, mg]], dtype=float)
    n_features = getattr(model, "n_features_in_", features.shape[1])
    if features.shape[1] != n_features:
        if features.shape[1] > n_features:
            features = features[:, :n_features]
        else:
            pad_width = n_features - features.shape[1]
            features = np.pad(features, ((0, 0), (0, pad_width)), mode="constant")

    pred = model.predict(features)
    return str(pred[0])


# ---------------------------------------------------------------------------
# Multi-crop recommendation with full details
# ---------------------------------------------------------------------------

def recommend_crops_detailed(
    temp: float, humidity: float, rainfall: float, soil: str,
    ph: float, ec: float, carbon: float, ca: float, mg: float,
    area_hectares: float = 1.0, investment: float = None,
) -> dict:
    """Return top recommended crops with suitability scores, economics,
    farming plans, and government schemes."""

    ph = ph or 0.0

    # Score all crops in our database
    scored = []
    for crop_name in CROP_DATABASE:
        s = _score_crop(crop_name, temp, humidity, rainfall, soil, ph)
        scored.append((crop_name, s))

    # Sort by suitability (descending)
    scored.sort(key=lambda x: x[1], reverse=True)

    # Use rule-based primary pick and make sure it's on top
    primary = _rule_based_crop(temp, humidity, rainfall, soil, ph, ec, carbon, ca or 0, mg or 0)

    # Ensure primary crop is first
    primary_in_list = False
    for i, (c, s) in enumerate(scored):
        if c == primary:
            primary_in_list = True
            if i != 0:
                scored.pop(i)
                scored.insert(0, (primary, max(s, scored[0][1] + 5)))
            break

    if not primary_in_list:
        scored.insert(0, (primary, 90.0))

    # Build detailed results for top 4 crops
    results = []
    for idx, (crop_name, suitability) in enumerate(scored[:4]):
        info = CROP_DATABASE.get(crop_name, _DEFAULT_CROP)
        econ = _estimate_economics(crop_name, area_hectares, investment if idx == 0 else None)

        results.append({
            "rank": idx + 1,
            "crop_name": crop_name,
            "suitability_score": suitability,
            "is_primary": idx == 0,
            "water_requirement": info["water_requirement"],
            "fertilizer_suggestion": info["fertilizer_suggestion"],
            "season": info["season"],
            "duration": info["duration_days"],
            "farming_plan": info["farming_plan"],
            "economics": econ,
            "govt_schemes": info["govt_schemes"],
        })

    return {
        "primary_crop": primary,
        "crops": results,
        "input_summary": {
            "temperature": temp,
            "humidity": humidity,
            "rainfall": rainfall,
            "soil_type": soil,
            "ph": ph,
            "area_hectares": area_hectares,
            "investment": investment,
        },
    }
