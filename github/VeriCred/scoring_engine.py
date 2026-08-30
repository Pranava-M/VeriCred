"""
Blockchain-Verified Work-History Scoring Engine
--------------------------------------------------
Reads ride-level gig-worker data, aggregates it into behavioural metrics
(day/week/month granularity), and computes a 0-100 trust score used as the
"on-chain" input for the loan risk meter.

Framework-free (pure pandas) so it can be:
  1. run standalone for testing, and
  2. imported by the Flask portal AND the oracle script that pushes the
     final score on-chain.
"""

import pandas as pd
import numpy as np
import glob
import json


# ---------------------------------------------------------------------------
# 1. Feature extraction: raw CSV -> per-worker aggregate metrics
# ---------------------------------------------------------------------------

def compute_features(df: pd.DataFrame) -> dict:
    """Turn a single worker's ride-level rows into summary + day/week/month features."""
    df = df.copy()
    df["date_parsed"] = pd.to_datetime(df["date"], format="%d-%m-%Y")

    total_rows = len(df)
    completed = df[df["status"] == "completed"].copy()
    cancelled = df[df["status"] != "completed"].copy()

    total_completed = len(completed)
    total_cancelled = len(cancelled)
    cancellation_rate = total_cancelled / total_rows if total_rows else 0

    avg_rating = completed["rating"].astype(float).mean() if total_completed else 0
    complaint_rate = (completed["customer_complaint"] == "Y").mean() if total_completed else 0

    ontime_df = completed.dropna(subset=["time_taken_mins"])
    ontime_df = ontime_df[ontime_df["time_taken_mins"] != ""]
    if len(ontime_df):
        on_time_mask = ontime_df["time_taken_mins"].astype(float) <= ontime_df["time_given_mins"].astype(float)
        on_time_rate = on_time_mask.mean()
    else:
        on_time_rate = 0

    active_days = df["date_parsed"].nunique()
    span_days = (df["date_parsed"].max() - df["date_parsed"].min()).days + 1
    active_day_pct = active_days / span_days if span_days else 0

    total_earnings = completed["earnings"].astype(float).sum()
    total_tips = completed["tip"].astype(float).sum()
    total_km = completed["km"].astype(float).sum()

    months_covered = span_days / 30.44
    weeks_covered = span_days / 7

    digital_payment_rate = (completed["payment_mode"].isin(["UPI", "Wallet"])).mean() if total_completed else 0

    daily_earnings = completed.groupby(completed["date_parsed"].dt.date)["earnings"].sum().astype(float)
    if len(daily_earnings) > 1 and daily_earnings.mean() > 0:
        earnings_cv = daily_earnings.std() / daily_earnings.mean()
        earnings_stability = max(0, 1 - min(earnings_cv, 1))
    else:
        earnings_stability = 0

    daily_cancel_avg = total_cancelled / span_days if span_days else 0
    monthly_cancel_avg = total_cancelled / months_covered if months_covered else 0

    return {
        "total_completed_rides": int(total_completed),
        "total_cancelled": int(total_cancelled),
        "avg_rides_per_day": round(total_completed / span_days, 1) if span_days else 0,
        "avg_rides_per_week": round(total_completed / weeks_covered, 1) if weeks_covered else 0,
        "avg_rides_per_month": round(total_completed / months_covered, 1) if months_covered else 0,

        "total_km": round(total_km, 1),
        "avg_km_per_day": round(total_km / span_days, 1) if span_days else 0,
        "avg_km_per_week": round(total_km / weeks_covered, 1) if weeks_covered else 0,
        "avg_km_per_month": round(total_km / months_covered, 1) if months_covered else 0,

        "avg_income_per_day": round((total_earnings + total_tips) / span_days, 2) if span_days else 0,
        "avg_income_per_week": round((total_earnings + total_tips) / weeks_covered, 2) if weeks_covered else 0,
        "avg_monthly_earnings": round((total_earnings + total_tips) / months_covered, 2) if months_covered else 0,

        "avg_cancellations_per_day": round(daily_cancel_avg, 2),
        "avg_cancellations_per_month": round(monthly_cancel_avg, 1),
        "cancellation_rate": round(cancellation_rate, 4),

        "avg_rating": round(avg_rating, 2),
        "complaint_rate": round(complaint_rate, 4),
        "on_time_rate": round(on_time_rate, 4),

        "active_days": int(active_days),
        "span_days": int(span_days),
        "active_day_pct": round(active_day_pct, 4),

        "digital_payment_rate": round(digital_payment_rate, 4),
        "earnings_stability": round(earnings_stability, 4),
    }


# ---------------------------------------------------------------------------
# 2. Scoring formula: features -> single 0-100 trust score
# ---------------------------------------------------------------------------

WEIGHTS = {
    "rating": 25,
    "cancellation": 20,
    "on_time": 20,
    "activity": 15,
    "complaint": 10,
    "payment_digital": 5,
    "earnings_stability": 5,
}
assert sum(WEIGHTS.values()) == 100


def compute_score(features: dict) -> dict:
    rating_score = features["avg_rating"] / 5.0
    cancellation_score = 1 - min(features["cancellation_rate"] / 0.25, 1)
    on_time_score = features["on_time_rate"]
    activity_score = min(features["active_day_pct"] / 0.9, 1)
    complaint_score = 1 - min(features["complaint_rate"] / 0.20, 1)
    payment_score = features["digital_payment_rate"]
    stability_score = features["earnings_stability"]

    sub_scores = {
        "rating": rating_score,
        "cancellation": cancellation_score,
        "on_time": on_time_score,
        "activity": activity_score,
        "complaint": complaint_score,
        "payment_digital": payment_score,
        "earnings_stability": stability_score,
    }

    weighted_total = sum(sub_scores[k] * WEIGHTS[k] for k in WEIGHTS)
    final_score = round(weighted_total, 2)

    return {
        "sub_scores": {k: round(v, 3) for k, v in sub_scores.items()},
        "final_score": final_score,
    }


# ---------------------------------------------------------------------------
# 3. Pipeline entry point: CSV path -> full report
# ---------------------------------------------------------------------------

def evaluate_worker(csv_path: str) -> dict:
    df = pd.read_csv(csv_path)
    worker_id = df["worker_id"].iloc[0] if "worker_id" in df.columns else "unknown"

    features = compute_features(df)
    scoring = compute_score(features)

    return {
        "worker_id": str(worker_id),
        "features": features,
        **scoring,
    }


if __name__ == "__main__":
    files = sorted(glob.glob("/mnt/user-data/outputs/applicant_1*.csv"))
    results = []
    for f in files:
        report = evaluate_worker(f)
        results.append(report)

    print(f"{'Worker':<10}{'Score':<10}{'Rides/mo':<12}{'Rating':<10}{'Cancel/mo':<12}")
    print("-" * 55)
    for r in results:
        ft = r["features"]
        print(f"{r['worker_id']:<10}{r['final_score']:<10}{ft['avg_rides_per_month']:<12}{ft['avg_rating']:<10}{ft['avg_cancellations_per_month']:<12}")

    with open("/mnt/user-data/outputs/scoring_results.json", "w") as f:
        json.dump(results, f, indent=2)
