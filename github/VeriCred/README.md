# VeriCred — Employee-Side Loan Verification Portal for Gig Workers

An internal bank-employee portal (not a customer-facing site) for reviewing
gig-worker loan requests using a blockchain-verified work-history score,
CIBIL, and bank balance — blended into a single Risk Meter reading. The
system never auto-approves or auto-rejects: the officer reviews the meter
and forwards the request to the Bank Manager, or declines it at their level.

## What's inside

| File | Purpose |
|---|---|
| `app.py` | Flask app — dashboard, applicant detail, live recalculation API, forward/decline workflow, blockchain ledger, about page |
| `scoring_engine.py` | Reads ride-level CSVs, computes the 0–100 AI work-history score with day/week/month breakdowns |
| `risk_engine.py` | Blends AI score + CIBIL + bank balance into the Risk Meter, plus EMI/DTI/savings |
| `blockchain.py` | Hash-chained ledger simulating the Polygon smart contract + oracle layer |
| `data/` | 4 synthetic applicants: ride-level CSVs (no tier labels) + KYC/CIBIL/bank profile JSON |
| `state/` | Runtime state (requested loan overrides, workflow status, blockchain ledger) — auto-created |
| `templates/` | Dashboard, applicant detail, blockchain ledger, about/rules pages |
| `static/css/style.css` | Portal styling + animations |

## About the blockchain layer

Deploying to a live Polygon Amoy testnet contract requires a browser wallet
(MetaMask), a funded testnet account, and an RPC connection — not available
in an automated build environment. `blockchain.py` implements the same
*logic* a Solidity contract would enforce (append-only records, SHA-256
hash linkage, tamper detection, a labeled consensus/validator field) purely
in Python, so the full "forward/decline → write immutable record → verify
chain" flow works end-to-end offline.

**For your report/viva:** this is the "Option A" mock-oracle + local ledger
pattern, explicitly standing in for what a Chainlink oracle + Polygon smart
contract pair would do in production. State it plainly — this is a
legitimate, defensible scope decision for a student project.

## Setup

```bash
cd bank_portal
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Using the portal

1. **Loan Requests (dashboard)** — see all 4 requests with Risk Meter,
   CIBIL, requested amount, and bank balance.
2. **Review Request** — click into any applicant to see:
   - Full KYC profile (DOB, blood group, PAN, Aadhaar, voter ID, DL number,
     vehicle details, bank account, UPI ID — all fictional)
   - Risk Meter gauge (blended AI + CIBIL + balance, higher = safer)
   - Work-history sub-scores (rating, cancellations, on-time %, activity,
     complaints, digital payment usage, earnings stability)
   - Day / week / month activity breakdown (rides, km, income, cancellations)
   - Financial risk panel (EMI, DTI, savings, system-suggested max)
   - Earnings/ride analytics charts
3. **Edit the requested loan amount** — type a new number; the Risk Meter,
   EMI, DTI, and system-suggested max all update live (no page reload).
   Click "Save This Amount" to persist it.
4. **Forward to Bank Manager / Decline at My Level** — the officer's only
   two actions. Both write an immutable, hash-linked record to the ledger.
   Neither is an automatic approval — forwarding just moves the request to
   the next stage, matching a real bank's workflow.
5. **Blockchain Ledger** (top nav) — every block, its hash, previous-hash
   link, a simulated transaction receipt, and a live chain-integrity check.
6. **About / Rules** (top nav) — explains the scoring formula, the Risk
   Meter blend, and every system rule in plain language.

## Resetting the demo

```bash
rm state/app_state.json state/blockchain_ledger.json
```

They'll be recreated fresh the next time you run the app.

## Notes on the data

All 4 applicants and their KYC/bank/CIBIL details are entirely fictional.
CIBIL scores (700 / 620 / 598 / 470) and bank balances (₹1,00,000 /
₹75,000 / ₹50,000 / ₹75,000) are fixed per the project brief, independent
of the ride-level work-history data. The ride datasets simulate 6 months
(Jan–Jun 2026) of gig work — no "tier" label is exposed anywhere in the
data or UI, so the Risk Meter reading is the only signal the reviewing
officer sees.
