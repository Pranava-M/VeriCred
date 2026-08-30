"""
Blockchain-Verified Risk Analysis Engine
-------------------------------------------
Combines three independently-sourced signals into one Risk Meter reading
that the bank employee interprets themselves — the system never decides
approve/reject:

  1. AI Work-History Score   (from scoring_engine.py, blockchain-verified)
  2. CIBIL Score              (fixed per applicant, traditional credit bureau)
  3. Bank Balance Adequacy    (fixed current balance vs. the *requested* loan)

The Risk Meter is scaled 0-100 where HIGHER = SAFER (green), LOWER = RISKIER
(red) — it answers "how safe does this look", not "should I approve it".
Changing the requested loan amount changes the balance-adequacy component
and the EMI/DTI figures, so the whole panel recalculates live.
"""

import json
import glob
from scoring_engine import evaluate_worker
import pandas as pd


ANNUAL_INTEREST_RATE = 24.0
DEFAULT_TENURE_MONTHS = 6
MAX_AFFORDABLE_EMI_RATIO = 0.40
EXISTING_LOAN_EMI_RATE = 0.08
DEFAULT_EXPENSE_RATIO = 0.70
MAX_LOAN_CEILING_INR = 200000  # platform-wide micro-loan ceiling — this is not a personal loan desk

# Blend weights for the Risk Meter (must sum to 1.0)
W_AI = 0.55
W_CIBIL = 0.30
W_BALANCE = 0.15


def calculate_emi(principal, annual_rate=ANNUAL_INTEREST_RATE, tenure_months=DEFAULT_TENURE_MONTHS):
    if principal <= 0:
        return 0.0
    r = (annual_rate / 12) / 100
    if r == 0:
        return round(principal / tenure_months, 2)
    emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)
    return round(emi, 2)


def max_affordable_principal(max_emi, annual_rate=ANNUAL_INTEREST_RATE, tenure_months=DEFAULT_TENURE_MONTHS):
    if max_emi <= 0:
        return 0.0
    r = (annual_rate / 12) / 100
    if r == 0:
        return round(max_emi * tenure_months, 2)
    principal = max_emi * ((1 + r) ** tenure_months - 1) / (r * (1 + r) ** tenure_months)
    return round(principal, 2)


def platform_dependence(csv_path: str) -> dict:
    df = pd.read_csv(csv_path)
    completed = df[df["status"] == "completed"].copy()
    if completed.empty:
        return {"platform_dependence_pct": 0, "dominant_platform": None}
    by_platform = completed.groupby("platform")["earnings"].sum().sort_values(ascending=False)
    total = by_platform.sum()
    top_share = round((by_platform.iloc[0] / total) * 100, 1) if total else 0
    return {"platform_dependence_pct": top_share, "dominant_platform": by_platform.index[0]}


def risk_meter(ai_score: float, cibil_score: int, bank_balance: float, requested_loan: float,
                monthly_income: float, requested_emi: float) -> dict:
    """
    Returns a 0-100 'safety' reading (higher = safer = green) blending the
    three independent signals, then applies an AFFORDABILITY GUARD: if the
    EMI on the requested amount would eat an unreasonable share of the
    applicant's actual monthly income, the meter is pulled down hard,
    regardless of how strong the AI/CIBIL signals are. Without this, a
    request for an absurd amount (e.g. lakhs of crores against a ~Rs.40,000
    salary) could still show a "safe" reading, because AI+CIBIL alone
    (85% of the raw blend) don't know anything about the amount requested.
    """
    ai_component = ai_score
    cibil_component = max(0, min(100, (cibil_score - 300) / 600 * 100))

    if requested_loan > 0:
        balance_component = round(100 * bank_balance / (bank_balance + requested_loan), 1)
    else:
        balance_component = 100

    raw_blend = W_AI * ai_component + W_CIBIL * cibil_component + W_BALANCE * balance_component

    # Affordability guard: EMI-to-income ratio.
    # <=40% of income -> no penalty. >=100% of income (EMI alone exceeds
    # the applicant's entire monthly earnings) -> factor collapses to 0,
    # i.e. the request is flagged as fundamentally unpayable no matter what
    # the other signals say.
    affordability_ratio = (requested_emi / monthly_income) if monthly_income > 0 else 999
    if affordability_ratio <= 0.40:
        affordability_factor = 1.0
    elif affordability_ratio >= 1.0:
        affordability_factor = 0.0
    else:
        affordability_factor = 1 - (affordability_ratio - 0.40) / 0.60

    blended = round(raw_blend * affordability_factor, 1)
    blended = max(0, min(100, blended))

    if blended >= 75:
        band = "Low Risk"
        color = "green"
    elif blended >= 50:
        band = "Moderate Risk"
        color = "amber"
    elif blended >= 20:
        band = "High Risk"
        color = "red"
    else:
        band = "Critical Risk"
        color = "red"

    return {
        "risk_meter": blended,
        "risk_band": band,
        "risk_color": color,
        "components": {
            "ai_component": round(ai_component, 1),
            "cibil_component": round(cibil_component, 1),
            "balance_component": round(balance_component, 1),
        },
    }


def build_pros_cons(features: dict):
    pros, cons = [], []

    if features["avg_rating"] >= 4.5:
        pros.append(f"Excellent average customer rating ({features['avg_rating']}/5.0)")
    elif features["avg_rating"] < 4.0:
        cons.append(f"Below-average customer rating ({features['avg_rating']}/5.0)")

    if features["cancellation_rate"] <= 0.03:
        pros.append(f"Very low cancellation rate ({features['cancellation_rate']*100:.1f}%)")
    elif features["cancellation_rate"] >= 0.10:
        cons.append(f"High cancellation rate ({features['cancellation_rate']*100:.1f}%)")

    if features["on_time_rate"] >= 0.85:
        pros.append(f"Strong on-time completion rate ({features['on_time_rate']*100:.1f}%)")
    elif features["on_time_rate"] < 0.65:
        cons.append(f"Low on-time completion rate ({features['on_time_rate']*100:.1f}%)")

    if features["active_day_pct"] >= 0.85:
        pros.append(f"Highly consistent activity ({features['active_day_pct']*100:.1f}% of days active)")
    elif features["active_day_pct"] < 0.5:
        cons.append(f"Inconsistent activity ({features['active_day_pct']*100:.1f}% of days active)")

    if features["complaint_rate"] >= 0.08:
        cons.append(f"Elevated customer complaint rate ({features['complaint_rate']*100:.1f}%)")

    if features["digital_payment_rate"] >= 0.6:
        pros.append(f"Majority of income is digitally verifiable ({features['digital_payment_rate']*100:.1f}% UPI/Wallet)")
    elif features["digital_payment_rate"] < 0.3:
        cons.append(f"Heavy reliance on cash payments — harder to verify income")

    return pros, cons


# ---------------------------------------------------------------------------
# Main entry point used by Flask
# ---------------------------------------------------------------------------

def evaluate_application(csv_path: str, kyc_profile: dict, requested_loan_override=None) -> dict:
    ai_result = evaluate_worker(csv_path)
    features = ai_result["features"]
    dependence = platform_dependence(csv_path)

    requested_loan = requested_loan_override if requested_loan_override is not None else kyc_profile.get("requested_loan_amount_inr", 0)

    # Platform ceiling: this is a MICRO-credit product, not a personal loan
    # desk. Reject/clamp anything above a sane ceiling before it even
    # reaches the scoring formula, rather than relying on the risk meter
    # alone to react to nonsense input.
    requested_loan = max(0, min(requested_loan, MAX_LOAN_CEILING_INR))
    monthly_income = features["avg_monthly_earnings"]
    monthly_expenses = kyc_profile.get("monthly_expenses_inr") or round(monthly_income * DEFAULT_EXPENSE_RATIO, 2)
    estimated_savings = round(monthly_income - monthly_expenses, 2)

    existing_outstanding = kyc_profile.get("outstanding_balance_inr", 0) or 0
    existing_emi = round(existing_outstanding * EXISTING_LOAN_EMI_RATE, 2)

    disposable_income = max(0, estimated_savings - existing_emi)
    max_affordable_emi = round(disposable_income * MAX_AFFORDABLE_EMI_RATIO, 2)
    safe_borrowing_capacity = round(max_affordable_principal(max_affordable_emi), -2)

    requested_emi = calculate_emi(requested_loan)
    dti_ratio = round(((existing_emi + requested_emi) / monthly_income) * 100, 1) if monthly_income else 0

    cibil_score = kyc_profile.get("cibil_score")
    credit_rating = kyc_profile.get("credit_rating")
    bank_balance = kyc_profile.get("current_bank_balance_inr", 0)

    rm = risk_meter(ai_result["final_score"], cibil_score, bank_balance, requested_loan,
                     monthly_income=monthly_income, requested_emi=requested_emi)

    pros, cons = build_pros_cons(features)

    return {
        "worker_id": ai_result["worker_id"],
        "display_id": kyc_profile.get("display_id"),
        "applicant_name": kyc_profile.get("full_name"),
        "application_id": kyc_profile.get("application_id"),

        "ai_score": ai_result["final_score"],
        "ai_sub_scores": ai_result["sub_scores"],
        "features": features,

        "cibil_score": cibil_score,
        "credit_rating": credit_rating,
        "bank_balance_inr": bank_balance,

        "platform_dependence_pct": dependence["platform_dependence_pct"],
        "dominant_platform": dependence["dominant_platform"],

        "monthly_expenses_inr": monthly_expenses,
        "estimated_monthly_savings_inr": estimated_savings,
        "existing_outstanding_inr": existing_outstanding,
        "existing_emi_estimate_inr": existing_emi,
        "disposable_income_inr": disposable_income,

        "requested_loan_inr": requested_loan,
        "requested_loan_emi_inr": requested_emi,
        "debt_to_income_ratio_pct": dti_ratio,
        "system_suggested_max_inr": safe_borrowing_capacity,

        "risk_meter": rm["risk_meter"],
        "risk_band": rm["risk_band"],
        "risk_color": rm["risk_color"],
        "risk_components": rm["components"],

        "pros": pros,
        "cons": cons,
    }


if __name__ == "__main__":
    with open("/mnt/user-data/outputs/applicant_kyc_profiles.json") as f:
        profiles = {str(p["worker_id"]): p for p in json.load(f)}

    files = sorted(glob.glob("/mnt/user-data/outputs/applicant_1*.csv"))
    reports = []
    for f in files:
        wid = pd.read_csv(f, nrows=1)["worker_id"].iloc[0]
        profile = profiles[str(wid)]
        report = evaluate_application(f, profile)
        reports.append(report)

    print(f"{'Worker':<8}{'Name':<20}{'AI':<7}{'CIBIL':<7}{'Balance':<10}{'DTI%':<8}{'Risk Meter':<12}{'Band':<15}")
    print("-" * 90)
    for r in reports:
        print(f"{r['worker_id']:<8}{r['applicant_name']:<20}{r['ai_score']:<7}{r['cibil_score']:<7}"
              f"{r['bank_balance_inr']:<10}{r['debt_to_income_ratio_pct']:<8}{r['risk_meter']:<12}{r['risk_band']:<15}")

    with open("/mnt/user-data/outputs/loan_applications_full.json", "w") as f:
        json.dump(reports, f, indent=2, default=str)
