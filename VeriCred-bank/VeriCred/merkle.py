"""
Merkle Tree — turns a CSV file into one 32-byte fingerprint.
------------------------------------------------------------
This is the piece that lets you go on-chain WITHOUT uploading the CSV
itself. Every row gets hashed, then hashes are combined in pairs upward
until one "Merkle root" represents the entire file. That root is small
enough to pass as a Solidity function argument (it's exactly 32 bytes,
which is what Solidity's `bytes32` type expects) and any later change to
even one row produces a completely different root.
"""

import hashlib
import pandas as pd


def _hash_leaf(row_string: str) -> str:
    return hashlib.sha256(row_string.encode()).hexdigest()


def _hash_pair(left: str, right: str) -> str:
    return hashlib.sha256((left + right).encode()).hexdigest()


def build_merkle_tree(leaves: list) -> list:
    if not leaves:
        return [[hashlib.sha256(b"").hexdigest()]]
    levels = [leaves]
    current = leaves
    while len(current) > 1:
        if len(current) % 2 == 1:
            current = current + [current[-1]]
        next_level = [_hash_pair(current[i], current[i + 1]) for i in range(0, len(current), 2)]
        levels.append(next_level)
        current = next_level
    return levels


def merkle_root_of_csv(csv_path: str) -> str:
    """The single value you pass to the smart contract instead of the CSV itself."""
    df = pd.read_csv(csv_path)
    leaves = [
        _hash_leaf("|".join(str(v) for v in row))
        for row in df.sort_index(axis=1).itertuples(index=False)
    ]
    tree = build_merkle_tree(leaves)
    return tree[-1][0]


if __name__ == "__main__":
    import glob
    for f in sorted(glob.glob("data/applicant_1*.csv")):
        print(f, "->", merkle_root_of_csv(f))
