"""
Simulated Blockchain Ledger
-----------------------------
Implements a minimal hash-chained ledger mirroring the project's real
architecture on Polygon:

    Oracle verifies score -> pushes to smart contract -> contract stores an
    immutable record -> record is hash-linked to the previous one so any
    tampering breaks the chain.

WHY SIMULATED, NOT A LIVE TESTNET CONTRACT:
Deploying to Polygon Amoy requires a browser wallet (MetaMask), a funded
testnet account, and an RPC endpoint — none of which are available in an
automated build environment. This module implements the same *logic* a
Solidity contract would enforce (append-only records, hash linkage,
tamper-evidence, a consensus/validator label) entirely in Python, so the
end-to-end flow is fully demoable offline. State this plainly in your
report as the mock-oracle pattern standing in for a live Chainlink +
Polygon smart-contract pair.
"""

import hashlib
import json
import os
from datetime import datetime, timezone

LEDGER_PATH = os.path.join(os.path.dirname(__file__), "state", "blockchain_ledger.json")


class Block:
    def __init__(self, index, timestamp, data, previous_hash, validator="Oracle-Node-1"):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.validator = validator
        self.consensus = "Proof of Stake (simulated)"
        self.hash = self.compute_hash()

    def compute_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "validator": self.validator,
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            "validator": self.validator,
            "consensus": self.consensus,
        }


class Blockchain:
    def __init__(self):
        self.chain = []
        self._load_or_init()

    def _load_or_init(self):
        os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
        if os.path.exists(LEDGER_PATH):
            with open(LEDGER_PATH) as f:
                raw = json.load(f)
            for b in raw:
                block = Block(b["index"], b["timestamp"], b["data"], b["previous_hash"], b["validator"])
                block.hash = b["hash"]
                self.chain.append(block)
        else:
            genesis = Block(0, self._now(), {"message": "Genesis Block - Gig Worker Credit Ledger"}, "0" * 64)
            self.chain.append(genesis)
            self._save()

    def _now(self):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    def _save(self):
        with open(LEDGER_PATH, "w") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2)

    def latest_block(self):
        return self.chain[-1]

    def add_block(self, data: dict) -> Block:
        prev = self.latest_block()
        block = Block(
            index=prev.index + 1,
            timestamp=self._now(),
            data=data,
            previous_hash=prev.hash,
        )
        self.chain.append(block)
        self._save()
        return block

    def verify_chain(self) -> dict:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]
            if current.hash != current.compute_hash():
                return {"valid": False, "broken_at_block": current.index, "reason": "Hash mismatch (data tampered)"}
            if current.previous_hash != prev.hash:
                return {"valid": False, "broken_at_block": current.index, "reason": "Chain link broken"}
        return {"valid": True, "broken_at_block": None, "reason": None}

    def get_worker_history(self, worker_id):
        return [b.to_dict() for b in self.chain if str(b.data.get("worker_id")) == str(worker_id)]

    def get_chain(self):
        return [b.to_dict() for b in self.chain]


def fake_tx_receipt(block: Block) -> dict:
    import random
    random.seed(block.hash)
    return {
        "tx_hash": "0x" + block.hash[:64],
        "block_number": 4_820_000 + block.index,
        "network": "Polygon Amoy Testnet (simulated)",
        "gas_used": random.randint(45000, 90000),
        "gas_price_gwei": round(random.uniform(25, 45), 2),
        "status": "Success",
        "confirmations": random.randint(12, 40),
    }
