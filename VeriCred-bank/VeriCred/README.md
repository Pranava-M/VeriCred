# VeriCred — AI + Blockchain Loan Verification Portal for Gig Workers

An internal bank-employee portal for reviewing gig-worker loan requests
using a blockchain-verified work-history score, CIBIL, and bank balance —
blended into a single Risk Meter reading. The system never auto-approves
or auto-rejects: the officer reviews the meter and forwards the request to
the Bank Manager, or declines it at their level.

This project includes a **real, working deployment** on the Polygon Amoy
public blockchain test network — not just a local simulation.

## Team

| Roll Number |
|---|
| CB.SC.U4CSE24730 |
| CB.SC.U4CSE24528 |

Department of Computer Science and Engineering

---

## The Problem

Gig economy workers — delivery riders, cab drivers — often earn a stable
income but cannot get a bank loan, because banks decide creditworthiness
mainly from a salary slip and a CIBIL score, and most gig workers have
neither. Meanwhile, every gig platform already tracks exactly how
reliable each worker is: completed rides, customer ratings, cancellation
rate, on-time performance. That data already exists — it just isn't being
used by banks.

## The Solution — How It Works, Step by Step

**1. Six months of ride data goes in.** Each applicant has a CSV of every
ride/delivery over six months — status, rating, cancellations, on-time
delivery, payment method, and more.

**2. The scoring engine turns this into a trust score.** Seven signals are
each scored out of 100 and combined with different weights:

| Signal | Weight |
|---|---|
| Customer Rating | 25% |
| Reliability (low cancellations) | 20% |
| On-Time Completion | 20% |
| Activity Consistency | 15% |
| Complaint-Free Rate | 10% |
| Digital Payment Usage | 5% |
| Earnings Stability | 5% |

**3. The risk engine blends this with existing financial data** — CIBIL
score and bank balance — into one final number called the **Risk Meter**
(0–100, higher = safer): 55% AI score + 30% CIBIL + 15% balance adequacy.

**4. A bank officer reviews the Risk Meter** on the dashboard and detail
page, along with every sub-score behind it, and decides to either forward
the application to the Bank Manager or decline it. The system never makes
this decision automatically.

**5. That decision is permanently recorded on the blockchain.** Every
record is linked to the one before it using a SHA-256 hash, so altering
any past record breaks the chain in a way that's immediately detectable.
Instead of storing the full six-month dataset on-chain, only a **Merkle
root** (a single fingerprint proving the dataset is untouched) is stored.

**6. This can run in two modes** — a local simulated ledger for offline
demos, or real transactions sent to an actual deployed smart contract on
Polygon Amoy. See "Blockchain Modes" below.

---

## Screenshots

### Employee Dashboard
All four loan applications with Risk Meter, CIBIL, and requested amount at a glance.

<img width="1917" height="1092" alt="Screenshot 2026-08-30 081817" src="https://github.com/user-attachments/assets/66bd44a4-a064-4e95-bccc-6c846d9b1e57" />


### Applicant Detail — Risk Meter Breakdown
Full Risk Meter gauge with all seven work-history sub-scores.

<img width="1917" height="1091" alt="Screenshot 2026-08-30 081835" src="https://github.com/user-attachments/assets/07b07a58-2951-4a4c-83a1-81798b9ca469" />
<img width="1917" height="1088" alt="Screenshot 2026-08-30 081856" src="https://github.com/user-attachments/assets/0e882018-3aae-46a4-b19c-30548c1338db" />


### Blockchain Ledger
Every recorded decision, hash-linked and chain-verified.

<img width="1917" height="1093" alt="Screenshot 2026-08-30 081945" src="https://github.com/user-attachments/assets/7aaa637d-7867-4937-8011-b59e7a0fe6ca" />


### Reports & Analytics
Portfolio-level charts across all applications.

<img width="1917" height="1092" alt="Screenshot 2026-08-30 081921" src="https://github.com/user-attachments/assets/77e2581c-5ac7-4798-a97d-9f50396fcd82" />


---

## Real Blockchain Deployment — Evidence

This project doesn't just simulate a blockchain — the smart contract was
genuinely deployed and tested on Polygon Amoy, a live public test network.

### Wallet connected to Polygon Amoy
MetaMask showing the active network and test MATIC balance used to pay for deployment and transactions.

<img width="471" height="687" alt="Screenshot 2026-08-30 082045" src="https://github.com/user-attachments/assets/07727ff6-0c36-468c-8e9f-732a8063b552" />


### Smart contract compiled successfully
The `GigWorkerLoanLedger.sol` contract compiled with no errors in Remix IDE.

<img width="533" height="856" alt="Screenshot 2026-08-30 082418" src="https://github.com/user-attachments/assets/4b695556-0ba2-4bdd-8c8e-f782821ab6a9" />


### Contract deployed on-chain
The deployed contract address, live on Polygon Amoy.

<img width="522" height="951" alt="Screenshot 2026-08-30 082431" src="https://github.com/user-attachments/assets/6c0f697c-2d0f-4ea2-b109-cc7223ab1dee" />


---

## Project Structure

| File / Folder | Purpose |
|---|---|
| `app.py` | Flask app — dashboard, applicant detail, forward/decline workflow, blockchain ledger, and 6 additional portal sections |
| `scoring_engine.py` | Computes the 0–100 AI work-history score from the 7 weighted signals above |
| `risk_engine.py` | Blends AI score + CIBIL + bank balance into the Risk Meter, plus EMI/DTI/savings |
| `blockchain.py` | Simulated hash-chained ledger (used when `USE_REAL_BLOCKCHAIN` is off) |
| `blockchain_real/` | Real blockchain layer — Solidity smart contract, deployment guide, `onchain_connector.py` |
| `merkle.py` | Builds the Merkle root of a ride dataset |
| `data/` | 4 synthetic applicants: ride-level CSVs + KYC/CIBIL/bank profile JSON |
| `state/` | Runtime state (auto-created, resettable) |
| `templates/` | Intro page, dashboard, applicant detail, blockchain ledger, about page, and the 6 additional portal sections |
| `static/video/` | The intro video played on first visit |
| `static/css/`, `static/js/` | Styling, intro video handler, page transition effects |
| `docs/images/` | Screenshots referenced in this README |

## Blockchain Modes

```bash
# Simulated mode (default) — no wallet or internet required
python app.py

# Real mode — sends genuine transactions to Polygon Amoy
# Windows PowerShell:
$env:USE_REAL_BLOCKCHAIN="true"; python app.py
# macOS/Linux:
USE_REAL_BLOCKCHAIN=true python app.py
```

Real mode requires your own `blockchain_real/.env` file (never committed —
see `.gitignore`), based on `.env.example`, filled in with your own
Alchemy RPC URL, wallet private key, and deployed contract address. Full
walkthrough in `blockchain_real/DEPLOY_GUIDE.md`.

## Setup

```bash
git clone <this-repo-url>
cd bank_portal_v2
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Open **http://127.0.0.1:5000**. The intro video plays once per browser
session, then takes you into the portal.

## Using the Portal

1. **Dashboard (Home)** — all 4 requests with Risk Meter, CIBIL, requested amount, and bank balance.
2. **Applicant detail** — full KYC profile, Risk Meter breakdown, all 7 sub-scores, day/week/month activity charts.
3. **Forward to Bank Manager / Decline at My Level** — the officer's only two actions, both writing a permanent record to the ledger.
4. **Blockchain Ledger** (top nav) — every block, its hash, and a live chain-integrity check.
5. **More menu** — Accounts Management, Transactions, Loan Processing, Customer Support, Reports & Analytics, Settings & Security.
6. **About** — the scoring formula and every system rule, in plain language.

## Resetting the Demo

```bash
rm state/app_state.json state/blockchain_ledger.json
```

Recreated fresh next run. (Only resets the simulated ledger — real
blockchain records are permanent by design.)

## Notes on the Data

All applicant data is entirely fictional. CIBIL scores (700 / 620 / 598 /
470) and bank balances (₹1,00,000 / ₹75,000 / ₹50,000 / ₹75,000) are fixed
per the project brief. No "tier" label is exposed anywhere in the data or
UI — the Risk Meter is the only signal the reviewing officer sees.
