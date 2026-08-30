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

> **To add these:** save each screenshot into `docs/images/` using the
> **exact filename** shown below. Once pushed to GitHub, these will
> display automatically — no other changes needed.

### Employee Dashboard
All four loan applications with Risk Meter, CIBIL, and requested amount at a glance.

`docs/images/01-dashboard.png`

![Dashboard](docs/images/01-dashboard.png)

### Applicant Detail — Risk Meter Breakdown
Full Risk Meter gauge with all seven work-history sub-scores.

`docs/images/02-applicant-detail.png`

![Applicant Detail](docs/images/02-applicant-detail.png)

### Blockchain Ledger
Every recorded decision, hash-linked and chain-verified.

`docs/images/03-blockchain-ledger.png`

![Blockchain Ledger](docs/images/03-blockchain-ledger.png)

### Reports & Analytics
Portfolio-level charts across all applications.

`docs/images/04-reports-analytics.png`

![Reports and Analytics](docs/images/04-reports-analytics.png)

---

## Real Blockchain Deployment — Evidence

This project doesn't just simulate a blockchain — the smart contract was
genuinely deployed and tested on Polygon Amoy, a live public test network.

### Wallet connected to Polygon Amoy
MetaMask showing the active network and test MATIC balance used to pay for deployment and transactions.

`docs/images/05-metamask-polygon-amoy.png`

![MetaMask Polygon Amoy](docs/images/05-metamask-polygon-amoy.png)

### Smart contract compiled successfully
The `GigWorkerLoanLedger.sol` contract compiled with no errors in Remix IDE.

`docs/images/06-remix-compiled.png`

![Remix Compiled](docs/images/06-remix-compiled.png)

### Contract deployed on-chain
The deployed contract address, live on Polygon Amoy.

`docs/images/07-remix-deployed-contract.png`

![Remix Deployed Contract](docs/images/07-remix-deployed-contract.png)

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
