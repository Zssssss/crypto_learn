#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Blockchain (educational, single file)
Features:
- Proof-of-Work mining (configurable difficulty)
- Transactions with optional ECDSA signatures (if 'ecdsa' is installed)
- Merkle root per block
- JSON disk persistence (save/load)
- Very small Wallet helper
DISCLAIMER: This is a toy implementation for learning only (NOT secure, NOT production).
"""

from __future__ import annotations
import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Any, Dict

# Optional ECDSA (install with: pip install ecdsa)
try:
    from ecdsa import SigningKey, SECP256k1, VerifyingKey, BadSignatureError
    ECDSA_AVAILABLE = True
except Exception:
    ECDSA_AVAILABLE = False
    SigningKey = VerifyingKey = BadSignatureError = None  # type: ignore


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ripemd160_hex(data: bytes) -> str:
    h = hashlib.new("ripemd160")
    h.update(data)
    return h.hexdigest()


def merkle_root(tx_hashes: List[str]) -> str:
    """Compute a simple Merkle root from a list of hex hashes (sha256)."""
    if not tx_hashes:
        return sha256_hex(b"")
    level = tx_hashes[:]
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            next_level.append(sha256_hex(bytes.fromhex(left) + bytes.fromhex(right)))
        level = next_level
    return level[0]


def pubkey_to_address(pubkey_bytes: bytes) -> str:
    """Classic address style: RIPEMD160(SHA256(pubkey))."""
    return ripemd160_hex(hashlib.sha256(pubkey_bytes).digest())


@dataclass
class Transaction:
    sender: str  # address hex string or "COINBASE"
    recipient: str  # address hex string
    amount: int  # integer amount for simplicity
    timestamp: float = field(default_factory=lambda: time.time())
    pubkey: Optional[str] = None  # hex-encoded public key (for signed tx)
    signature: Optional[str] = None  # hex-encoded signature over tx hash (if signed)

    def to_message(self) -> bytes:
        """Bytes to be signed/hashed (exclude signature field)."""
        obj = {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": int(self.timestamp),
            "pubkey": self.pubkey,
        }
        return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()

    def txid(self) -> str:
        return sha256_hex(self.to_message())

    def sign(self, sk: Any) -> None:
        """Sign with ecdsa.SigningKey if available."""
        if not ECDSA_AVAILABLE:
            raise RuntimeError("ECDSA not available. Install with: pip install ecdsa")
        message = self.to_message()
        sig = sk.sign_deterministic(message, hashfunc=hashlib.sha256)
        self.signature = sig.hex()
        self.pubkey = sk.get_verifying_key().to_string().hex()

    def verify(self) -> bool:
        # Coinbase tx needs no signature
        if self.sender == "COINBASE":
            return True
        # If ECDSA available, enforce signature + pubkey + address linkage
        if ECDSA_AVAILABLE:
            try:
                if not self.signature or not self.pubkey:
                    return False
                vk = VerifyingKey.from_string(bytes.fromhex(self.pubkey), curve=SECP256k1)
                vk.verify(bytes.fromhex(self.signature), self.to_message(), hashfunc=hashlib.sha256)
                # Address must match pubkey-derived address
                derived_addr = pubkey_to_address(bytes.fromhex(self.pubkey))
                return derived_addr == self.sender
            except BadSignatureError:
                return False
            except Exception:
                return False
        else:
            # If no ECDSA, allow unsigned tx (toy mode) but basic sanity checks
            return all([self.sender, self.recipient, self.amount >= 0])

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = int(self.timestamp)
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Transaction":
        return Transaction(
            sender=d["sender"],
            recipient=d["recipient"],
            amount=int(d["amount"]),
            timestamp=float(d.get("timestamp", time.time())),
            pubkey=d.get("pubkey"),
            signature=d.get("signature"),
        )


@dataclass
class Block:
    index: int
    previous_hash: str
    timestamp: float
    transactions: List[Transaction]
    difficulty: int
    nonce: int = 0
    merkle_root: str = ""
    hash: str = ""

    def compute_hash(self) -> str:
        header = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": int(self.timestamp),
            "merkle_root": self.merkle_root,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
        }
        return sha256_hex(json.dumps(header, sort_keys=True, separators=(',', ':')).encode())

    def mine(self) -> None:
        prefix = "0" * self.difficulty
        # Precompute merkle root
        self.merkle_root = merkle_root([tx.txid() for tx in self.transactions])
        while True:
            self.hash = self.compute_hash()
            if self.hash.startswith(prefix):
                break
            self.nonce += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": int(self.timestamp),
            "transactions": [tx.to_dict() for tx in self.transactions],
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "merkle_root": self.merkle_root,
            "hash": self.hash,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Block":
        txs = [Transaction.from_dict(x) for x in d["transactions"]]
        return Block(
            index=int(d["index"]),
            previous_hash=d["previous_hash"],
            timestamp=float(d["timestamp"]),
            transactions=txs,
            difficulty=int(d["difficulty"]),
            nonce=int(d["nonce"]),
            merkle_root=d.get("merkle_root", ""),
            hash=d.get("hash", ""),
        )


class Blockchain:
    def __init__(self, difficulty: int = 4, mining_reward: int = 50):
        self.chain: List[Block] = []
        self.mempool: List[Transaction] = []
        self.difficulty = difficulty
        self.mining_reward = mining_reward
        if not self.chain:
            self.create_genesis_block()

    # --- Core ---
    def create_genesis_block(self) -> None:
        genesis_tx = Transaction(sender="COINBASE", recipient="GENESIS", amount=0)
        block = Block(
            index=0,
            previous_hash="0" * 64,
            timestamp=time.time(),
            transactions=[genesis_tx],
            difficulty=self.difficulty,
        )
        block.mine()
        self.chain.append(block)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, tx: Transaction) -> bool:
        if not tx.verify():
            return False
        # Simple balance check (prevent overspend)
        if tx.sender != "COINBASE":
            if self.get_balance(tx.sender) < tx.amount:
                return False
        self.mempool.append(tx)
        return True

    def mine_pending_transactions(self, miner_address: str) -> Block:
        # Add coinbase transaction
        coinbase = Transaction(sender="COINBASE", recipient=miner_address, amount=self.mining_reward)
        block_txs = [coinbase] + self.mempool
        block = Block(
            index=self.last_block.index + 1,
            previous_hash=self.last_block.hash,
            timestamp=time.time(),
            transactions=block_txs,
            difficulty=self.difficulty,
        )
        block.mine()
        # Append & clear mempool
        self.chain.append(block)
        self.mempool = []
        return block

    # --- Validation ---
    def is_valid(self) -> bool:
        prefix = "0" * self.difficulty
        for i in range(1, len(self.chain)):
            prev = self.chain[i - 1]
            curr = self.chain[i]
            # Check linkage
            if curr.previous_hash != prev.hash:
                return False
            # Verify merkle root
            calc_merkle = merkle_root([tx.txid() for tx in curr.transactions])
            if curr.merkle_root != calc_merkle:
                return False
            # Verify PoW
            if curr.compute_hash() != curr.hash or not curr.hash.startswith(prefix):
                return False
            # Verify all txs
            for tx in curr.transactions:
                if not tx.verify():
                    return False
        return True

    # --- Utility ---
    def get_balance(self, address: str) -> int:
        balance = 0
        for block in self.chain:
            for tx in block.transactions:
                if tx.sender == address:
                    balance -= tx.amount
                if tx.recipient == address:
                    balance += tx.amount
        # Mempool outgoing
        for tx in self.mempool:
            if tx.sender == address:
                balance -= tx.amount
        return balance

    # --- Persistence ---
    def to_dict(self) -> Dict[str, Any]:
        return {
            "difficulty": self.difficulty,
            "mining_reward": self.mining_reward,
            "chain": [b.to_dict() for b in self.chain],
            "mempool": [t.to_dict() for t in self.mempool],
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Blockchain":
        bc = Blockchain(difficulty=int(d["difficulty"]), mining_reward=int(d["mining_reward"]))
        bc.chain = [Block.from_dict(x) for x in d["chain"]]
        bc.mempool = [Transaction.from_dict(x) for x in d.get("mempool", [])]
        return bc

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, sort_keys=True, indent=2)

    @staticmethod
    def load(path: str) -> "Blockchain":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        bc = Blockchain.from_dict(d)
        return bc


class Wallet:
    """Very small helper around ECDSA keys (if installed)."""
    def __init__(self, priv_hex: Optional[str] = None):
        if ECDSA_AVAILABLE:
            if priv_hex:
                self.sk = SigningKey.from_string(bytes.fromhex(priv_hex), curve=SECP256k1)
            else:
                self.sk = SigningKey.generate(curve=SECP256k1)
            self.vk = self.sk.get_verifying_key()
            self._address = pubkey_to_address(self.vk.to_string())
            self._priv_hex = self.sk.to_string().hex()
            self._pub_hex = self.vk.to_string().hex()
        else:
            # Fallback "address" using random bytes (NO signatures)
            self.sk = None
            self.vk = None
            secret = os.urandom(32)
            self._address = ripemd160_hex(secret)
            self._priv_hex = secret.hex()
            self._pub_hex = ""

    @property
    def address(self) -> str:
        return self._address

    @property
    def private_key_hex(self) -> str:
        return self._priv_hex

    @property
    def public_key_hex(self) -> str:
        return self._pub_hex

    def sign_tx(self, tx: Transaction) -> None:
        if not ECDSA_AVAILABLE:
            raise RuntimeError("Cannot sign without 'ecdsa' installed.")
        tx.sign(self.sk)


# --- Demo usage ---
def demo():
    print("ECDSA available:", ECDSA_AVAILABLE)
    chain_path = "chain.json"

    if Path(chain_path).exists():
        bc = Blockchain.load(chain_path)
        print("Loaded chain. Height:", len(bc.chain)-1, "Valid:", bc.is_valid())
    else:
        bc = Blockchain(difficulty=4, mining_reward=50)
        print("Created new chain. Height:", len(bc.chain)-1, "Valid:", bc.is_valid())

    # Create wallets
    alice = Wallet()
    bob = Wallet()
    miner = Wallet()
    print("Alice:", alice.address)
    print("Bob  :", bob.address)
    print("Miner:", miner.address)

    # Create a transaction Alice -> Bob (10)
    tx = Transaction(sender=alice.address, recipient=bob.address, amount=10)
    if ECDSA_AVAILABLE:
        alice.sign_tx(tx)
    added = bc.add_transaction(tx)
    print("Added TX:", added, "TXID:", tx.txid())

    # Mine pending transactions
    print("Mining... (this may take a bit with difficulty=4)")
    block = bc.mine_pending_transactions(miner.address)
    print("Mined block:", block.index, block.hash)

    # Show balances
    print("Balances:")
    print("  Alice:", bc.get_balance(alice.address))
    print("  Bob  :", bc.get_balance(bob.address))
    print("  Miner:", bc.get_balance(miner.address))

    # Save chain
    bc.save(chain_path)
    print("Saved to", chain_path)


if __name__ == "__main__":
    demo()
