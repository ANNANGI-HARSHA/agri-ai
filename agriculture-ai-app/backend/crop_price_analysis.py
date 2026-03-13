"""
Crop Price Prediction & Production Analysis Engine
===================================================
Uses three CSV datasets from the backend folder:
  1. Agmarknet_prices.csv        – recent APMC market prices (daily)
  2. Crop Prediction dataset.csv – historical production data (1997-2014)
  3. crop_recommendation.csv     – climate-crop mapping

Provides:
  • Yearly / monthly production trend analysis
  • Price trend analysis (daily / monthly)
  • Linear-regression-based forecasting for production & price
  • Crop comparison across states / years
  • Market price statistics (min, max, modal, volatility)
"""

import csv
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parent           # agriculture-ai-app/backend
_DATA_DIR    = _BACKEND_DIR                              # agriculture-ai-app/backend

AGMARKNET_CSV    = _DATA_DIR / "Agmarknet_prices.csv"
PRODUCTION_CSV   = _DATA_DIR / "Crop Prediction dataset.csv"
RECOMMENDATION_CSV = _DATA_DIR / "crop_recommendation.csv"
SOIL_CSV         = _DATA_DIR / "indian_soil_dataset.csv"


# ---------------------------------------------------------------------------
# CSV loaders with caching
# ---------------------------------------------------------------------------
_cache: Dict[str, Any] = {}


def _parse_price(val: str) -> float:
    """'4,541.00' → 4541.0"""
    try:
        return float(val.replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def _normalize_key(value: Optional[str]) -> str:
    text = (value or "").strip().lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _load_agmarknet() -> List[dict]:
    key = "agmarknet"
    if key in _cache:
        return _cache[key]
    rows: List[Dict[str, Any]] = []
    if not AGMARKNET_CSV.exists():
        _cache[key] = rows
        return rows
    with open(AGMARKNET_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header_row = None
        for line in reader:
            # skip title row
            if not header_row:
                if line and line[0].strip() == "State":
                    header_row = [c.strip() for c in line]
                continue
            if len(line) < len(header_row):
                continue
            rec: Dict[str, Any] = dict(zip(header_row, [c.strip() for c in line]))
            rec["_min"]   = _parse_price(rec.get("Min Price", "0"))
            rec["_max"]   = _parse_price(rec.get("Max Price", "0"))
            rec["_modal"] = _parse_price(rec.get("Modal Price", "0"))
            # Parse date  dd-mm-yyyy
            try:
                rec["_date"] = datetime.strptime(rec.get("Price Date", ""), "%d-%m-%Y")
            except Exception:
                rec["_date"] = None
            rows.append(rec)
    _cache[key] = rows
    return rows


def _load_production() -> List[dict]:
    key = "production"
    if key in _cache:
        return _cache[key]
    rows: List[Dict[str, Any]] = []
    if not PRODUCTION_CSV.exists():
        _cache[key] = rows
        return rows
    with open(PRODUCTION_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rec: Dict[str, Any] = {}
            for k, v in r.items():
                rec[k.strip().strip('"')] = v.strip().strip('"') if v else ""
            # Normalise
            rec["_year"]       = int(rec.get("Crop_Year", "0") or "0")
            rec["_crop"]       = rec.get("Crop", "").strip()
            rec["_state"]      = rec.get("State_Name", "").strip()
            rec["_district"]   = rec.get("District_Name", "").strip()
            rec["_season"]     = rec.get("Season", "").strip()
            rec["_area"]       = float(rec.get("Area", "0") or "0")
            rec["_production"] = float(rec.get("Production", "0") or "0")
            rec["_temp"]       = float(rec.get("Temperature", "0") or "0")
            rec["_humidity"]   = float(rec.get("Humidity", "0") or "0")
            rec["_moisture"]   = float(rec.get("Soil_Moisture", "0") or "0")
            rows.append(rec)
    _cache[key] = rows
    return rows


def _load_recommendation() -> List[dict]:
    key = "recommendation"
    if key in _cache:
        return _cache[key]
    rows: List[Dict[str, Any]] = []
    if not RECOMMENDATION_CSV.exists():
        _cache[key] = rows
        return rows
    with open(RECOMMENDATION_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rec = {k.strip(): v.strip() if v else "" for k, v in r.items()}
            rows.append(rec)
    _cache[key] = rows
    return rows


def _load_soil() -> List[dict]:
    key = "soil"
    if key in _cache:
        return _cache[key]
    rows: List[Dict[str, Any]] = []
    if not SOIL_CSV.exists():
        _cache[key] = rows
        return rows
    with open(SOIL_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rec: Dict[str, Any] = {k.strip(): (v.strip() if v else "") for k, v in r.items()}
            rec["_pincode"] = rec.get("pincode", "")
            rec["_state"] = rec.get("state", "")
            rec["_state_key"] = _normalize_key(rec.get("state", ""))
            rec["_soil_type"] = rec.get("soil_type", "")
            rec["_N"] = float(rec.get("N", "0") or "0")
            rec["_P"] = float(rec.get("P", "0") or "0")
            rec["_K"] = float(rec.get("K", "0") or "0")
            rec["_ph"] = float(rec.get("ph", "0") or "0")
            rows.append(rec)
    _cache[key] = rows
    return rows


# ---------------------------------------------------------------------------
# Helper: simple linear regression  y = mx + b
# ---------------------------------------------------------------------------
def _linear_reg(xs: List[float], ys: List[float]):
    n = len(xs)
    if n < 2:
        return 0, (ys[0] if ys else 0)
    sx  = sum(xs)
    sy  = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 0, sy / n
    m = (n * sxy - sx * sy) / denom
    b = (sy - m * sx) / n
    return m, b


# ---------------------------------------------------------------------------
# 1.  Available filters  (for dropdowns)
# ---------------------------------------------------------------------------
def get_available_filters() -> dict:
    prod_data = _load_production()
    agm_data  = _load_agmarknet()

    crops_prod = sorted(set(r["_crop"] for r in prod_data if r["_crop"]))
    states     = sorted(set(r["_state"] for r in prod_data if r["_state"]))
    years      = sorted(set(r["_year"] for r in prod_data if r["_year"]))
    seasons    = sorted(set(r["_season"] for r in prod_data if r["_season"]))

    crops_price = sorted(set(r.get("Commodity", "").strip() for r in agm_data if r.get("Commodity")))
    markets     = sorted(set(r.get("Market", "").strip() for r in agm_data if r.get("Market")))
    districts   = sorted(set(r.get("District", "").strip() for r in agm_data if r.get("District")))

    return {
        "production_crops": crops_prod,
        "states": states,
        "years": years,
        "seasons": seasons,
        "price_crops": crops_price,
        "price_markets": markets,
        "price_districts": districts,
    }


# ---------------------------------------------------------------------------
# 2.  Yearly production trend for a crop (optionally filtered by state)
# ---------------------------------------------------------------------------
def yearly_production_trend(crop: str, state: Optional[str] = None) -> dict:
    data = _load_production()
    filtered = [r for r in data if r["_crop"].lower() == crop.lower()]
    if state:
        filtered = [r for r in filtered if r["_state"].lower() == state.lower()]

    if not filtered:
        return {"crop": crop, "state": state, "yearly": [], "forecast": [], "summary": {}}

    # Aggregate by year
    yearly: Dict[int, dict] = defaultdict(lambda: {"area": 0, "production": 0, "count": 0,
                                                    "temp_sum": 0, "hum_sum": 0})
    for r in filtered:
        y = r["_year"]
        yearly[y]["area"]       += r["_area"]
        yearly[y]["production"] += r["_production"]
        yearly[y]["count"]      += 1
        yearly[y]["temp_sum"]   += r["_temp"]
        yearly[y]["hum_sum"]    += r["_humidity"]

    sorted_years = sorted(yearly.keys())
    trend = []
    for y in sorted_years:
        d = yearly[y]
        count = d["count"] or 1
        productivity = (d["production"] / d["area"]) if d["area"] > 0 else 0
        trend.append({
            "year":          y,
            "total_area":    round(d["area"], 2),
            "total_production": round(d["production"], 2),
            "records":       count,
            "avg_temp":      round(d["temp_sum"] / count, 1),
            "avg_humidity":  round(d["hum_sum"] / count, 1),
            "productivity":  round(productivity, 2),
        })

    # Linear regression forecast (next 5 years)
    xs = [float(t["year"]) for t in trend]
    ys_prod = [t["total_production"] for t in trend]
    ys_area = [t["total_area"] for t in trend]
    m_p, b_p = _linear_reg(xs, ys_prod)
    m_a, b_a = _linear_reg(xs, ys_area)

    last_year = max(sorted_years) if sorted_years else 2014
    forecast = []
    for i in range(1, 6):
        fy = last_year + i
        fp = max(0, m_p * fy + b_p)
        fa = max(0, m_a * fy + b_a)
        forecast.append({
            "year": fy,
            "predicted_production": round(fp, 2),
            "predicted_area": round(fa, 2),
            "predicted_productivity": round(fp / fa, 2) if fa > 0 else 0,
        })

    # Summary stats
    prods = [t["total_production"] for t in trend]
    summary = {
        "total_years":    len(trend),
        "avg_production": round(sum(prods) / len(prods), 2) if prods else 0,
        "max_production": round(max(prods), 2) if prods else 0,
        "min_production": round(min(prods), 2) if prods else 0,
        "trend_direction": "📈 Increasing" if m_p > 0 else "📉 Decreasing",
        "growth_rate_pct": round((m_p / (b_p if abs(b_p) > 1 else 1)) * 100, 2),
    }

    return {
        "crop":     crop,
        "state":    state,
        "yearly":   trend,
        "forecast": forecast,
        "summary":  summary,
    }


# ---------------------------------------------------------------------------
# 3.  Monthly / daily market price analysis (from Agmarknet)
# ---------------------------------------------------------------------------
def market_price_analysis(commodity: Optional[str] = None,
                          district: Optional[str] = None) -> dict:
    data = _load_agmarknet()
    if not data:
        return {"commodity": commodity, "daily": [], "monthly": [], "summary": {}, "forecast": []}

    filtered = data[:]
    if commodity:
        filtered = [r for r in filtered if r.get("Commodity", "").strip().lower() == commodity.lower()]
    if district:
        filtered = [r for r in filtered if r.get("District", "").strip().lower() == district.lower()]

    if not filtered:
        return {"commodity": commodity, "district": district,
                "daily": [], "monthly": [], "summary": {}, "forecast": []}

    # Sort by date
    dated = [r for r in filtered if r["_date"]]
    dated.sort(key=lambda r: r["_date"])

    # Daily trend
    daily = []
    for r in dated:
        daily.append({
            "date":        r["_date"].strftime("%Y-%m-%d"),
            "min_price":   r["_min"],
            "max_price":   r["_max"],
            "modal_price": r["_modal"],
            "market":      r.get("Market", ""),
            "variety":     r.get("Variety", ""),
        })

    # Monthly aggregation
    monthly_agg: Dict[str, dict] = defaultdict(lambda: {
        "min_sum": 0, "max_sum": 0, "modal_sum": 0, "count": 0,
        "abs_min": float("inf"), "abs_max": 0
    })
    for r in dated:
        mkey = r["_date"].strftime("%Y-%m")
        monthly_agg[mkey]["min_sum"]   += r["_min"]
        monthly_agg[mkey]["max_sum"]   += r["_max"]
        monthly_agg[mkey]["modal_sum"] += r["_modal"]
        monthly_agg[mkey]["count"]     += 1
        monthly_agg[mkey]["abs_min"]    = min(monthly_agg[mkey]["abs_min"], r["_min"])
        monthly_agg[mkey]["abs_max"]    = max(monthly_agg[mkey]["abs_max"], r["_max"])

    monthly = []
    for mkey in sorted(monthly_agg.keys()):
        d = monthly_agg[mkey]
        c = d["count"] or 1
        monthly.append({
            "month":          mkey,
            "avg_min_price":  round(d["min_sum"] / c, 2),
            "avg_max_price":  round(d["max_sum"] / c, 2),
            "avg_modal_price": round(d["modal_sum"] / c, 2),
            "lowest_price":   d["abs_min"],
            "highest_price":  d["abs_max"],
            "data_points":    c,
        })

    # Price forecast (linear on modal prices by ordinal day)
    if len(dated) >= 2:
        base_ord = dated[0]["_date"].toordinal()
        xs_f = [float(r["_date"].toordinal() - base_ord) for r in dated]
        ys_f = [r["_modal"] for r in dated]
        m_f, b_f = _linear_reg(xs_f, ys_f)

        last_ord = dated[-1]["_date"].toordinal()
        forecast = []
        for days_ahead in [7, 14, 30, 60, 90]:
            pred = m_f * (last_ord - dated[0]["_date"].toordinal() + days_ahead) + b_f
            forecast.append({
                "days_ahead": days_ahead,
                "predicted_modal_price": round(max(0, pred), 2),
                "trend_per_day": round(m_f, 2),
            })
    else:
        forecast = []

    # Summary
    modals = [r["_modal"] for r in dated]
    if modals:
        avg_m = sum(modals) / len(modals)
        std_m = math.sqrt(sum((x - avg_m) ** 2 for x in modals) / len(modals)) if len(modals) > 1 else 0
        summary = {
            "commodity":       commodity or "All",
            "total_records":   len(dated),
            "date_range":      f"{dated[0]['_date'].strftime('%d-%b-%Y')} to {dated[-1]['_date'].strftime('%d-%b-%Y')}",
            "avg_modal_price": round(avg_m, 2),
            "min_modal_price": round(min(modals), 2),
            "max_modal_price": round(max(modals), 2),
            "price_volatility": round(std_m, 2),
            "price_trend":     "📈 Rising" if (forecast and forecast[0]["trend_per_day"] > 0) else "📉 Falling",
            "price_unit":      dated[0].get("Price Unit", "Rs./Quintal"),
        }
    else:
        summary = {}

    return {
        "commodity": commodity,
        "district":  district,
        "daily":     daily,
        "monthly":   monthly,
        "forecast":  forecast,
        "summary":   summary,
    }


# ---------------------------------------------------------------------------
# 4.  Crop comparison – compare multiple crops on production metrics
# ---------------------------------------------------------------------------
def compare_crops(crop_list: List[str], state: Optional[str] = None) -> dict:
    results = []
    for crop in crop_list:
        trend = yearly_production_trend(crop, state)
        if trend["yearly"]:
            total_prod = sum(t["total_production"] for t in trend["yearly"])
            avg_prod   = total_prod / len(trend["yearly"])
            last_prod  = trend["yearly"][-1]["total_production"]
            results.append({
                "crop":            crop,
                "years_of_data":   len(trend["yearly"]),
                "total_production": round(total_prod, 2),
                "avg_production":  round(avg_prod, 2),
                "latest_production": round(last_prod, 2),
                "trend":           trend["summary"].get("trend_direction", "N/A"),
                "growth_rate_pct": trend["summary"].get("growth_rate_pct", 0),
                "forecast_next_year": trend["forecast"][0]["predicted_production"] if trend["forecast"] else 0,
            })
    results.sort(key=lambda x: x["avg_production"], reverse=True)
    return {"state": state, "crops": results}


# ---------------------------------------------------------------------------
# 5.  Season-wise production breakdown for a crop
# ---------------------------------------------------------------------------
def season_wise_analysis(crop: str, state: Optional[str] = None) -> dict:
    data = _load_production()
    filtered = [r for r in data if r["_crop"].lower() == crop.lower()]
    if state:
        filtered = [r for r in filtered if r["_state"].lower() == state.lower()]

    season_data: Dict[str, dict] = defaultdict(lambda: {"area": 0, "production": 0, "count": 0})
    for r in filtered:
        s = r["_season"]
        season_data[s]["area"]       += r["_area"]
        season_data[s]["production"] += r["_production"]
        season_data[s]["count"]      += 1

    seasons = []
    for s, d in sorted(season_data.items()):
        c = d["count"] or 1
        seasons.append({
            "season":          s,
            "total_area":      round(d["area"], 2),
            "total_production": round(d["production"], 2),
            "avg_production":  round(d["production"] / c, 2),
            "records":         c,
            "productivity":    round(d["production"] / d["area"], 2) if d["area"] > 0 else 0,
        })

    return {"crop": crop, "state": state, "seasons": seasons}


# ---------------------------------------------------------------------------
# 6.  State-wise production ranking for a crop
# ---------------------------------------------------------------------------
def state_wise_ranking(crop: str) -> dict:
    data = _load_production()
    filtered = [r for r in data if r["_crop"].lower() == crop.lower()]

    state_data: Dict[str, dict] = defaultdict(lambda: {"area": 0, "production": 0, "count": 0})
    for r in filtered:
        st = r["_state"]
        state_data[st]["area"]       += r["_area"]
        state_data[st]["production"] += r["_production"]
        state_data[st]["count"]      += 1

    ranking = []
    for st, d in state_data.items():
        c = d["count"] or 1
        ranking.append({
            "state":           st,
            "total_area":      round(d["area"], 2),
            "total_production": round(d["production"], 2),
            "avg_production":  round(d["production"] / c, 2),
            "productivity":    round(d["production"] / d["area"], 2) if d["area"] > 0 else 0,
        })
    ranking.sort(key=lambda x: x["total_production"], reverse=True)
    for i, r in enumerate(ranking):
        r["rank"] = i + 1

    return {"crop": crop, "states": ranking}


def soil_state_overview(state: Optional[str] = None) -> dict:
    data = _load_soil()
    filtered = data[:]
    if state:
        state_key = _normalize_key(state)
        filtered = [r for r in filtered if r["_state_key"] == state_key]

    if not filtered:
        return {
            "state": state,
            "records": 0,
            "avg_ph": 0,
            "avg_n": 0,
            "avg_p": 0,
            "avg_k": 0,
            "top_soils": [],
        }

    soil_counts: Dict[str, int] = defaultdict(int)
    ph_values = []
    n_values = []
    p_values = []
    k_values = []
    states = set()

    for row in filtered:
        states.add(row["_state"])
        soil_counts[row["_soil_type"]] += 1
        ph_values.append(row["_ph"])
        n_values.append(row["_N"])
        p_values.append(row["_P"])
        k_values.append(row["_K"])

    top_soils = [
        {"soil_type": soil_type, "count": count}
        for soil_type, count in sorted(soil_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]

    return {
        "state": state,
        "records": len(filtered),
        "states_covered": sorted(states),
        "avg_ph": round(sum(ph_values) / len(ph_values), 2),
        "avg_n": round(sum(n_values) / len(n_values), 2),
        "avg_p": round(sum(p_values) / len(p_values), 2),
        "avg_k": round(sum(k_values) / len(k_values), 2),
        "top_soils": top_soils,
    }


# ---------------------------------------------------------------------------
# 7.  Combined dashboard data (single API call for the monitoring page)
# ---------------------------------------------------------------------------
def get_monitoring_dashboard(crop: str,
                             state: Optional[str] = None,
                             commodity: Optional[str] = None) -> dict:
    """Return all data the crop monitoring page needs in one call."""
    prod_trend   = yearly_production_trend(crop, state)
    price_data   = market_price_analysis(commodity or crop)
    season_data  = season_wise_analysis(crop, state)
    state_rank   = state_wise_ranking(crop)
    soil_profile = soil_state_overview(state)
    filters      = get_available_filters()

    return {
        "production":   prod_trend,
        "market_price": price_data,
        "seasons":      season_data,
        "state_ranking": state_rank,
        "soil_profile": soil_profile,
        "filters":      filters,
    }
