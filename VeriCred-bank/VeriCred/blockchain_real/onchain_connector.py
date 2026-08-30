"""
Real Blockchain Connector — Polygon Amoy via Alchemy
--------------------------------------------------------
This is the REAL counterpart to blockchain.py's simulated ledger. Once you
have:
  1. Deployed GigWorkerLoanLedger.sol (see contracts/ and DEPLOY_GUIDE.md)
  2. An Alchemy app + RPC URL for Polygon Amoy
  3. A funded oracle wallet (private key, testnet MATIC from a faucet)

...fill in the four values below (or better, put them in a `.env` file —
see .env.example) and every function here will send REAL transactions to
your deployed contract on Polygon Amoy testnet.

NEVER commit a real private key to any file that gets shared, uploaded, or
pushed to GitHub. Use environment variables (.env, gitignored) always.
"""

import os
import json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(__file__)

# ---------------------------------------------------------------------------
# Configuration — fill these in via a .env file (see .env.example)
# ---------------------------------------------------------------------------
ALCHEMY_RPC_URL = os.getenv("ALCHEMY_RPC_URL", "")          # e.g. https://polygon-amoy.g.alchemy.com/v2/YOUR_KEY
ORACLE_PRIVATE_KEY = os.getenv("ORACLE_PRIVATE_KEY", "")     # the wallet that deployed / is authorized as oracle
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")         # filled in after you deploy

ABI_PATH = os.path.join(BASE_DIR, "build", "GigWorkerLoanLedger_abi.json")


def _load_abi():
    with open(ABI_PATH) as f:
        return json.load(f)


def get_web3() -> Web3:
    if not ALCHEMY_RPC_URL:
        raise RuntimeError("ALCHEMY_RPC_URL not set. Add it to your .env file.")
    w3 = Web3(Web3.HTTPProvider(ALCHEMY_RPC_URL))
    if not w3.is_connected():
        raise RuntimeError("Could not connect to Alchemy RPC endpoint. Check your URL / internet connection.")
    return w3


def get_contract(w3: Web3 = None):
    if not CONTRACT_ADDRESS:
        raise RuntimeError("CONTRACT_ADDRESS not set. Deploy the contract first, then add its address to .env.")
    w3 = w3 or get_web3()
    abi = _load_abi()
    return w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=abi)


def get_oracle_account(w3: Web3):
    if not ORACLE_PRIVATE_KEY:
        raise RuntimeError("ORACLE_PRIVATE_KEY not set. Add it to your .env file (never commit this).")
    return w3.eth.account.from_key(ORACLE_PRIVATE_KEY)


# ---------------------------------------------------------------------------
# Writing: record a decision on-chain (real transaction, costs testnet gas)
# ---------------------------------------------------------------------------

def scale_score(score: float) -> int:
    """Solidity has no floats — 93.85 becomes 9385, unscaled with /100 when reading back."""
    return int(round(score * 100))


def record_decision_onchain(worker_id: int, application_id: str, applicant_name: str,
                             ai_score: float, cibil_score: int, risk_meter: float,
                             risk_band: str, requested_amount_inr: int,
                             merkle_root_hex: str, action: str, reviewed_by: str) -> dict:
    """
    Sends a REAL transaction to Polygon Amoy calling recordDecision().
    Returns the transaction hash and receipt once mined (usually a few
    seconds on Amoy).
    """
    w3 = get_web3()
    contract = get_contract(w3)
    account = get_oracle_account(w3)

    merkle_root_bytes = bytes.fromhex(merkle_root_hex[:64])  # bytes32 needs exactly 32 bytes

    decision_input = (
        worker_id,
        application_id,
        applicant_name,
        scale_score(ai_score),
        cibil_score,
        scale_score(risk_meter),
        risk_band,
        requested_amount_inr,
        merkle_root_bytes,
        action,
        reviewed_by,
    )

    tx = contract.functions.recordDecision(decision_input).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gas": 250000,  # lowered from 500000 — still comfortable padding above what
                         # this call actually needs, but requires less MATIC reserved
                         # upfront for the pre-flight balance check
        "gasPrice": w3.eth.gas_price,
    })

    signed_tx = w3.eth.account.sign_transaction(tx, private_key=ORACLE_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    return {
        "tx_hash": tx_hash.hex(),
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed,
        "status": "Success" if receipt.status == 1 else "Failed",
        "explorer_url": f"https://amoy.polygonscan.com/tx/{tx_hash.hex()}",
    }


# ---------------------------------------------------------------------------
# Reading: no gas cost, just queries the contract's current state
# ---------------------------------------------------------------------------

def get_worker_history_onchain(worker_id: int) -> list:
    contract = get_contract()
    records = contract.functions.getWorkerHistory(worker_id).call()
    return [_unpack_record(r) for r in records]


def get_latest_decision_onchain(worker_id: int) -> dict:
    contract = get_contract()
    record = contract.functions.getLatestDecision(worker_id).call()
    return _unpack_record(record)


def verify_merkle_root_onchain(worker_id: int, merkle_root_hex: str) -> bool:
    contract = get_contract()
    merkle_root_bytes = bytes.fromhex(merkle_root_hex[:64])
    return contract.functions.verifyLatestMerkleRoot(worker_id, merkle_root_bytes).call()


def _unpack_record(r) -> dict:
    return {
        "worker_id": r[0],
        "application_id": r[1],
        "applicant_name": r[2],
        "ai_score": r[3] / 100,
        "cibil_score": r[4],
        "risk_meter": r[5] / 100,
        "risk_band": r[6],
        "requested_amount_inr": r[7],
        "merkle_root": r[8].hex(),
        "action": r[9],
        "reviewed_by": r[10],
        "timestamp": r[11],
    }


if __name__ == "__main__":
    print("Checking connection to Alchemy...")
    w3 = get_web3()
    print(f"Connected: {w3.is_connected()}")
    print(f"Current block number: {w3.eth.block_number}")
    print(f"Oracle account: {get_oracle_account(w3).address}")
    print(f"Oracle balance: {w3.from_wei(w3.eth.get_balance(get_oracle_account(w3).address), 'ether')} MATIC")
