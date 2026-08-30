"""
Bank Employee Loan Verification Portal
----------------------------------------
Employee-side portal (not a customer-facing site). Lets a bank officer:

  - see all gig-worker loan requests on a dashboard
  - open a request to see the full blockchain-verified work-history score,
    CIBIL, bank balance, and day/week/month activity breakdown
  - edit the requested loan amount and watch the Risk Meter + every
    statistic recalculate live (AJAX, no page reload)
  - forward a request to the Bank Manager for final approval, or decline
    it at their level — the system NEVER auto-approves/rejects, it only
    shows a Risk Meter reading for the officer to interpret
  - view the blockchain verification ledger
  - read the About page explaining how the scoring + blockchain layer works

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

import os
import json

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from risk_engine import evaluate_application
import blockchain as chain_module
import merkle

# --- Real Polygon integration (optional until you've deployed) -----------
# Set USE_REAL_BLOCKCHAIN=true in your environment (or blockchain_real/.env)
# once you've deployed the contract and filled in your Alchemy/MetaMask
# details. Until then, the app keeps working exactly as before, writing to
# the local simulated ledger — this import is wrapped so a missing/blank
# .env never crashes the app during development.
USE_REAL_BLOCKCHAIN = os.getenv("USE_REAL_BLOCKCHAIN", "false").lower() == "true"
onchain = None
if USE_REAL_BLOCKCHAIN:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "blockchain_real"))
    import onchain_connector as onchain

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_PATH = os.path.join(BASE_DIR, "state", "app_state.json")

app = Flask(__name__)
app.secret_key = "gig-credit-demo-secret"

ledger = chain_module.Blockchain()

WORKERS = {
    "101": os.path.join(DATA_DIR, "applicant_101.csv"),
    "102": os.path.join(DATA_DIR, "applicant_102.csv"),
    "103": os.path.join(DATA_DIR, "applicant_103.csv"),
    "104": os.path.join(DATA_DIR, "applicant_104.csv"),
}

with open(os.path.join(DATA_DIR, "applicant_kyc_profiles.json")) as f:
    KYC_PROFILES = {str(p["worker_id"]): p for p in json.load(f)}


# ---------------------------------------------------------------------------
# State store: requested loan overrides + officer workflow status
# ---------------------------------------------------------------------------

def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    state = {wid: {"requested_loan_override": None, "status": "Pending Review"} for wid in WORKERS}
    save_state(state)
    return state


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


STATE = load_state()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_application(worker_id: str, amount_override=None) -> dict:
    profile = KYC_PROFILES[worker_id]
    override = amount_override if amount_override is not None else STATE[worker_id].get("requested_loan_override")
    report = evaluate_application(WORKERS[worker_id], profile, requested_loan_override=override)
    report["workflow_status"] = STATE[worker_id]["status"]
    report["profile"] = profile

    history = ledger.get_worker_history(worker_id)
    report["blockchain_verified"] = len(history) > 0
    report["blockchain_records"] = len(history)
    report["latest_block"] = history[-1] if history else None
    return report


def build_chart_data(csv_path: str) -> dict:
    df = pd.read_csv(csv_path)
    df["date_parsed"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    completed = df[df["status"] == "completed"].copy()

    completed["month"] = completed["date_parsed"].dt.strftime("%b %Y")
    monthly = completed.groupby("month", sort=False)["earnings"].sum().round(0)
    monthly = monthly.reindex(sorted(monthly.index, key=lambda m: pd.to_datetime(m, format="%b %Y")))

    status_counts = df["status"].value_counts()
    payment_counts = completed["payment_mode"].value_counts()

    completed["weekday"] = completed["date_parsed"].dt.day_name()
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_earn = completed.groupby("weekday")["earnings"].mean().reindex(weekday_order).round(0).fillna(0)

    monthly_rides = completed.groupby("month", sort=False).size()
    monthly_rides = monthly_rides.reindex(monthly.index)

    monthly_cancel = df[df["status"] != "completed"].copy()
    monthly_cancel["month"] = monthly_cancel["date_parsed"].dt.strftime("%b %Y")
    cancel_counts = monthly_cancel.groupby("month", sort=False).size()
    cancel_counts = cancel_counts.reindex(monthly.index).fillna(0)

    return {
        "monthly_labels": list(monthly.index),
        "monthly_values": [float(v) for v in monthly.values],
        "monthly_rides_values": [int(v) if pd.notna(v) else 0 for v in monthly_rides.values],
        "monthly_cancel_values": [int(v) for v in cancel_counts.values],
        "status_labels": list(status_counts.index),
        "status_values": [int(v) for v in status_counts.values],
        "payment_labels": list(payment_counts.index),
        "payment_values": [int(v) for v in payment_counts.values],
        "weekday_labels": weekday_order,
        "weekday_values": [float(v) for v in weekday_earn.values],
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def intro():
    return render_template("intro.html")


@app.route("/portal")
def dashboard():
    applications = [get_application(wid) for wid in WORKERS]

    total = len(applications)
    forwarded = sum(1 for a in applications if a["workflow_status"] == "Forwarded to Manager")
    declined = sum(1 for a in applications if a["workflow_status"] == "Declined by Officer")
    pending = total - forwarded - declined
    avg_risk = round(sum(a["risk_meter"] for a in applications) / total, 1) if total else 0

    stats = {"total": total, "forwarded": forwarded, "declined": declined, "pending": pending, "avg_risk": avg_risk}
    return render_template("dashboard.html", applications=applications, stats=stats)


@app.route("/applicant/<worker_id>")
def applicant_detail(worker_id):
    if worker_id not in WORKERS:
        return "Applicant not found", 404
    app_data = get_application(worker_id)
    charts = build_chart_data(WORKERS[worker_id])
    return render_template("detail.html", a=app_data, charts=charts)


@app.route("/api/recalc/<worker_id>")
def api_recalc(worker_id):
    """Live preview endpoint — does NOT persist, used while the officer is typing."""
    if worker_id not in WORKERS:
        return jsonify({"error": "not found"}), 404
    try:
        amount = float(request.args.get("amount", 0))
    except ValueError:
        return jsonify({"error": "invalid amount"}), 400
    report = get_application(worker_id, amount_override=amount)
    return jsonify({
        "requested_loan_inr": report["requested_loan_inr"],
        "was_clamped": amount > report["requested_loan_inr"],
        "risk_meter": report["risk_meter"],
        "risk_band": report["risk_band"],
        "risk_color": report["risk_color"],
        "risk_components": report["risk_components"],
        "requested_loan_emi_inr": report["requested_loan_emi_inr"],
        "debt_to_income_ratio_pct": report["debt_to_income_ratio_pct"],
        "system_suggested_max_inr": report["system_suggested_max_inr"],
        "estimated_monthly_savings_inr": report["estimated_monthly_savings_inr"],
        "disposable_income_inr": report["disposable_income_inr"],
    })


@app.route("/applicant/<worker_id>/save_amount", methods=["POST"])
def save_amount(worker_id):
    from risk_engine import MAX_LOAN_CEILING_INR
    try:
        new_amount = int(float(request.form["requested_loan"]))
        if new_amount < 0:
            raise ValueError
    except (ValueError, KeyError):
        flash("Enter a valid loan amount.", "error")
        return redirect(url_for("applicant_detail", worker_id=worker_id))

    if new_amount > MAX_LOAN_CEILING_INR:
        new_amount = MAX_LOAN_CEILING_INR
        flash(f"This platform only supports micro-loans up to Rs. {MAX_LOAN_CEILING_INR:,}. Amount capped accordingly.", "error")
    else:
        flash(f"Requested amount saved at Rs. {new_amount:,}. All statistics recalculated.", "success")

    STATE[worker_id]["requested_loan_override"] = new_amount
    STATE[worker_id]["status"] = "Pending Review"
    save_state(STATE)
    return redirect(url_for("applicant_detail", worker_id=worker_id))


def build_block_data(worker_id: str, app_data: dict, action: str) -> dict:
    """
    Shared by both routes below. Computes the Merkle root of the
    applicant's CSV (their fingerprint, not the raw data) and assembles
    the record that goes into either the local simulated ledger or a real
    Polygon transaction, depending on USE_REAL_BLOCKCHAIN.
    """
    merkle_root = merkle.merkle_root_of_csv(WORKERS[worker_id])
    return {
        "worker_id": worker_id,
        "application_id": app_data["application_id"],
        "applicant_name": app_data["applicant_name"],
        "ai_score": app_data["ai_score"],
        "cibil_score": app_data["cibil_score"],
        "risk_meter": app_data["risk_meter"],
        "risk_band": app_data["risk_band"],
        "requested_amount_inr": app_data["requested_loan_inr"],
        "merkle_root": merkle_root,
        "action": action,
        "reviewed_by": "Bank Officer (Demo Session)",
    }


@app.route("/applicant/<worker_id>/forward", methods=["POST"])
def forward_to_manager(worker_id):
    app_data = get_application(worker_id)

    STATE[worker_id]["status"] = "Forwarded to Manager"
    save_state(STATE)

    data = build_block_data(worker_id, app_data, "FORWARDED_TO_MANAGER")

    if USE_REAL_BLOCKCHAIN:
        try:
            result = onchain.record_decision_onchain(
                worker_id=int(worker_id), application_id=data["application_id"],
                applicant_name=data["applicant_name"], ai_score=data["ai_score"],
                cibil_score=data["cibil_score"], risk_meter=data["risk_meter"],
                risk_band=data["risk_band"], requested_amount_inr=data["requested_amount_inr"],
                merkle_root_hex=data["merkle_root"], action=data["action"], reviewed_by=data["reviewed_by"],
            )
            flash(f"Forwarded to Bank Manager. Real Polygon tx: {result['tx_hash'][:18]}... "
                  f"View it: {result['explorer_url']}", "success")
        except Exception as e:
            flash(f"Could not write to Polygon ({e}). Check blockchain_real/.env is filled in "
                  f"(see DEPLOY_GUIDE.md). Decision was NOT recorded — try again once fixed.", "error")
            STATE[worker_id]["status"] = "Pending Review"  # roll back, since nothing was actually recorded
            save_state(STATE)
    else:
        # Local simulated ledger (unchanged from before) — used until you've
        # deployed the contract and set USE_REAL_BLOCKCHAIN=true.
        block = ledger.add_block(data)
        flash(f"Application forwarded to the Bank Manager for final approval. Reference: on-chain block #{block.index}.", "success")

    return redirect(url_for("applicant_detail", worker_id=worker_id))


@app.route("/applicant/<worker_id>/decline", methods=["POST"])
def decline(worker_id):
    app_data = get_application(worker_id)

    STATE[worker_id]["status"] = "Declined by Officer"
    save_state(STATE)

    data = build_block_data(worker_id, app_data, "DECLINED_BY_OFFICER")

    if USE_REAL_BLOCKCHAIN:
        try:
            result = onchain.record_decision_onchain(
                worker_id=int(worker_id), application_id=data["application_id"],
                applicant_name=data["applicant_name"], ai_score=data["ai_score"],
                cibil_score=data["cibil_score"], risk_meter=data["risk_meter"],
                risk_band=data["risk_band"], requested_amount_inr=data["requested_amount_inr"],
                merkle_root_hex=data["merkle_root"], action=data["action"], reviewed_by=data["reviewed_by"],
            )
            flash(f"Declined at officer level. Real Polygon tx: {result['tx_hash'][:18]}... "
                  f"View it: {result['explorer_url']}", "success")
        except Exception as e:
            flash(f"Could not write to Polygon ({e}). Check blockchain_real/.env is filled in "
                  f"(see DEPLOY_GUIDE.md). Decision was NOT recorded — try again once fixed.", "error")
            STATE[worker_id]["status"] = "Pending Review"
            save_state(STATE)
    else:
        block = ledger.add_block(data)
        flash(f"Application declined at officer level. Recorded on-chain: block #{block.index}.", "success")

    return redirect(url_for("applicant_detail", worker_id=worker_id))


@app.route("/applicant/<worker_id>/reopen", methods=["POST"])
def reopen(worker_id):
    STATE[worker_id]["status"] = "Pending Review"
    save_state(STATE)
    flash("Application reopened for review.", "success")
    return redirect(url_for("applicant_detail", worker_id=worker_id))


@app.route("/blockchain")
def blockchain_page():
    chain = ledger.get_chain()
    verification = ledger.verify_chain()
    receipts = {
        b["index"]: chain_module.fake_tx_receipt(
            chain_module.Block(b["index"], b["timestamp"], b["data"], b["previous_hash"], b["validator"])
        ) for b in chain if b["index"] != 0
    }
    return render_template("blockchain.html", chain=chain, verification=verification, receipts=receipts)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/section/accounts")
def section_accounts():
    applications = [get_application(wid) for wid in WORKERS]
    return render_template("section_accounts.html", applications=applications)


@app.route("/section/transactions")
def section_transactions():
    chain = ledger.get_chain()
    receipts = {
        b["index"]: chain_module.fake_tx_receipt(
            chain_module.Block(b["index"], b["timestamp"], b["data"], b["previous_hash"], b["validator"])
        ) for b in chain if b["index"] != 0
    }
    # Most recent first, skip the genesis block (not a real transaction)
    records = [b for b in reversed(chain) if b["index"] != 0]
    return render_template("section_transactions.html", records=records, receipts=receipts)


@app.route("/section/loan-processing")
def section_loan_processing():
    applications = [get_application(wid) for wid in WORKERS]
    pending = [a for a in applications if a["workflow_status"] == "Pending Review"]
    forwarded = [a for a in applications if a["workflow_status"] == "Forwarded to Manager"]
    declined = [a for a in applications if a["workflow_status"] == "Declined by Officer"]
    return render_template("section_loan_processing.html", pending=pending, forwarded=forwarded, declined=declined)


@app.route("/section/support")
def section_support():
    applications = [get_application(wid) for wid in WORKERS]
    # Illustrative support tickets tied to the real applicants — this
    # portal has no live ticketing backend, so these are presented plainly
    # as sample/demo tickets rather than implying real customer contact.
    ticket_templates = [
        ("Question about loan status", "Applicant asked for an update on their pending review.", "Open"),
        ("Requested amount clarification", "Applicant wants to know if they can revise their requested amount.", "Resolved"),
        ("KYC document re-verification", "Applicant's bank branch requested a KYC re-check.", "Open"),
        ("Repayment schedule query", "Applicant asked how EMI is calculated for their tier.", "Resolved"),
    ]
    tickets = []
    for i, app_data in enumerate(applications):
        subject, body, status = ticket_templates[i % len(ticket_templates)]
        tickets.append({
            "id": f"TCK-{1000 + i}",
            "applicant_name": app_data["applicant_name"],
            "worker_id": app_data["worker_id"],
            "subject": subject,
            "body": body,
            "status": status,
        })
    return render_template("section_support.html", tickets=tickets)


@app.route("/section/reports")
def section_reports():
    applications = [get_application(wid) for wid in WORKERS]
    total = len(applications)
    avg_risk = round(sum(a["risk_meter"] for a in applications) / total, 1) if total else 0
    avg_ai = round(sum(a["ai_score"] for a in applications) / total, 1) if total else 0
    forwarded = sum(1 for a in applications if a["workflow_status"] == "Forwarded to Manager")
    declined = sum(1 for a in applications if a["workflow_status"] == "Declined by Officer")
    pending = total - forwarded - declined

    chart_data = {
        "labels": [a["applicant_name"].split()[0] for a in applications],
        "risk_meters": [a["risk_meter"] for a in applications],
        "ai_scores": [a["ai_score"] for a in applications],
        "cibil_scores": [a["cibil_score"] or 0 for a in applications],
        "status_labels": ["Pending", "Forwarded", "Declined"],
        "status_values": [pending, forwarded, declined],
    }
    stats = {"total": total, "avg_risk": avg_risk, "avg_ai": avg_ai, "forwarded": forwarded, "declined": declined, "pending": pending}
    return render_template("section_reports.html", stats=stats, chart_data=chart_data)


@app.route("/section/settings")
def section_settings():
    verification = ledger.verify_chain()
    chain_length = len(ledger.get_chain())
    return render_template(
        "section_settings.html",
        use_real_blockchain=USE_REAL_BLOCKCHAIN,
        chain_verified=verification["valid"],
        chain_length=chain_length,
        total_records=max(0, chain_length - 1),
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
