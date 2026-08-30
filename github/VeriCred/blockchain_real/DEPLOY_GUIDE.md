# Deploying to Polygon Amoy — Step by Step

Everything in this folder is deployment-ready. These are the steps only
you can do (they need a real browser wallet), roughly 20 minutes total.

---

## Step 1 — Install MetaMask

1. Go to https://metamask.io, install the browser extension.
2. Create a new wallet (or use an existing one — but see the safety note below).
3. **Safety note:** create a wallet you use ONLY for this project. Never
   use a wallet holding real money for testnet experiments — there's no
   danger of losing real funds on a testnet, but it's a good habit to
   build now.

## Step 2 — Add Polygon Amoy Testnet to MetaMask

1. Open MetaMask → click the network dropdown at the top → "Add network"
2. Search for "Polygon Amoy" in the list (MetaMask has it built in), or add manually:
   - Network Name: `Polygon Amoy Testnet`
   - RPC URL: `https://rpc-amoy.polygon.technology`
   - Chain ID: `80002`
   - Currency Symbol: `MATIC`
   - Block Explorer: `https://amoy.polygonscan.com`
3. Switch to this network.

## Step 3 — Get free testnet MATIC

1. Copy your wallet address from MetaMask (click your account name).
2. Go to a Polygon Amoy faucet — search "Polygon Amoy faucet" (the official
   one is at faucet.polygon.technology, select Amoy).
3. Paste your address, request testnet MATIC. It's free, arrives in seconds.
   You only need a tiny amount — gas on testnet costs nothing real.

## Step 4 — Create an Alchemy account + app

1. Go to https://alchemy.com, sign up (free tier is enough).
2. Click "Create new app".
3. Chain: **Polygon**, Network: **Polygon Amoy**.
4. Once created, click "API Key" and copy the **HTTPS URL** — this is your `ALCHEMY_RPC_URL`.

## Step 5 — Deploy the contract using Remix (easiest option)

1. Go to https://remix.ethereum.org
2. Create a new file, paste in the contents of `contracts/GigWorkerLoanLedger.sol`
3. Go to the "Solidity Compiler" tab (left sidebar) → select compiler version `0.8.20` → click "Compile"
4. Go to the "Deploy & Run Transactions" tab
5. Under "Environment", select **"Injected Provider - MetaMask"** — this connects Remix to your MetaMask wallet
6. MetaMask will pop up asking to connect — approve it, make sure it's on Polygon Amoy
7. In the "Deploy" section, you'll see a constructor field asking for `_oracle` (address) —
   paste in your own MetaMask wallet address (this makes your wallet the authorized oracle)
8. Click **Deploy**. MetaMask will pop up asking you to confirm the transaction (small gas fee, free testnet MATIC) — confirm.
9. Once mined, Remix shows the deployed contract under "Deployed Contracts" — copy its address.
   This is your `CONTRACT_ADDRESS`.

## Step 6 — Fill in your .env file

1. In `blockchain_real/`, copy `.env.example` to `.env`
2. Fill in:
   - `ALCHEMY_RPC_URL` — from Step 4
   - `ORACLE_PRIVATE_KEY` — from MetaMask: Account menu → Account details → Show private key
     (this is the wallet you set as `_oracle` in Step 5)
   - `CONTRACT_ADDRESS` — from Step 5

## Step 7 — Test the connection

```bash
cd blockchain_real
pip install web3 python-dotenv
python onchain_connector.py
```

You should see your connection status, current block number, oracle
address, and its testnet MATIC balance.

## Step 8 — Verify a real transaction

Try recording one decision manually:

```python
from onchain_connector import record_decision_onchain

result = record_decision_onchain(
    worker_id=101,
    application_id="APP-2026-101",
    applicant_name="Arun Kumar Selvam",
    ai_score=93.85,
    cibil_score=700,
    risk_meter=86.6,
    risk_band="Low Risk",
    requested_amount_inr=20000,
    merkle_root_hex="c53e19fa7a5a9717c627e4d3a5ed0e69e4b8052e47e594e5c0dcd83da52b29c2",
    action="FORWARDED_TO_MANAGER",
    reviewed_by="Bank Officer Demo",
)
print(result)
```

If it works, `result["explorer_url"]` gives you a real link on
amoy.polygonscan.com showing your transaction — screenshot this for your
report, it's the strongest proof-of-work you can show in a viva.

## Step 9 — Switch the Flask app to use real mode (optional)

Once the above works, `app.py`'s forward/decline routes can call
`onchain_connector.record_decision_onchain(...)` instead of (or alongside)
the local simulated `blockchain.py` ledger. Ask for this wiring once
you've completed steps 1-8 and confirmed a real transaction went through.

---

## Troubleshooting

- **"insufficient funds for gas"** → you need testnet MATIC, go back to Step 3
- **"nonce too low"** → you sent two transactions too close together, wait a few seconds and retry
- **Remix doesn't show Amoy in the network list** → make sure MetaMask itself is switched to Amoy before connecting Remix
- **Alchemy app has no data / errors** → double check you selected "Polygon Amoy" not "Polygon Mainnet" when creating the app
