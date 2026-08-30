# Polygon Upgrade — What Changed

Your app works EXACTLY as before by default. Nothing breaks. Here's what
was added on top of your existing code:

## New files
- `merkle.py` — turns any applicant CSV into one 32-byte fingerprint
  (a "Merkle root"). This is what goes on-chain instead of the raw CSV.
- `blockchain_real/` — the real Polygon deployment kit:
  - `contracts/GigWorkerLoanLedger.sol` — the Solidity contract (already
    compiled and verified — it hit a real "stack too deep" compiler error
    on the first pass, which is fixed in this version)
  - `build/` — the compiled ABI + bytecode, ready to paste into Remix
  - `onchain_connector.py` — the `web3.py` script that sends real
    transactions to your deployed contract via Alchemy
  - `.env.example` — copy to `.env` and fill in your 3 values
  - `DEPLOY_GUIDE.md` — the full click-by-click MetaMask/Alchemy/Remix walkthrough

## What changed in `app.py`
`forward_to_manager()` and `decline()` now check one flag:

```python
USE_REAL_BLOCKCHAIN = os.getenv("USE_REAL_BLOCKCHAIN", "false").lower() == "true"
```

- **Flag off (default)** — behaves exactly like before: writes to the
  local simulated `blockchain.py` ledger. You don't need to do anything
  differently to keep using the app as-is.
- **Flag on** — computes the Merkle root of the applicant's CSV, then
  calls `onchain_connector.record_decision_onchain(...)`, which sends a
  REAL, signed transaction to Polygon Amoy. The success message shows a
  real transaction hash and a link to view it on amoy.polygonscan.com.
- **Flag on but `.env` not filled in yet** — fails safely with a clear
  message telling you to check `DEPLOY_GUIDE.md`. Nothing crashes, no
  data gets corrupted, the application status rolls back to "Pending
  Review" so you can just try again once your setup is complete.

## How to actually turn on real mode

1. Follow `blockchain_real/DEPLOY_GUIDE.md` start to finish (MetaMask →
   faucet → Alchemy → deploy in Remix → fill in `.env`)
2. Test the connection: `cd blockchain_real && python onchain_connector.py`
3. Once that works, run the main app with the flag on:

   ```bash
   # Mac/Linux
   USE_REAL_BLOCKCHAIN=true python app.py

   # Windows (PowerShell)
   $env:USE_REAL_BLOCKCHAIN="true"; python app.py
   ```
4. Click "Forward to Bank Manager" on any applicant — this now sends a
   real, gas-paying (free testnet MATIC) transaction to Polygon Amoy.
