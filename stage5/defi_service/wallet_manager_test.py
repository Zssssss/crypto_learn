#!/usr/bin/env python3
"""
wallet_manager.py
工具：批量生成/保存/加载/查询/批量发送以太坊钱包

注意：
- 先在 .env 中设置 RPC_URL（比如 Infura/Alchemy 或本地节点）
- 强烈建议在 testnet 上测试
"""
import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Any
from pathlib import Path
from getpass import getpass

from web3 import Web3, HTTPProvider
from eth_account import Account
from mnemonic import Mnemonic
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()  # loads RPC_URL from .env if present

# -----------------------
# Configuration / helpers
# -----------------------
RPC_URL = os.getenv("RPC_URL", "https://rpc.ankr.com/eth_goerli")  # 默认 testnet RPC（可改）
w3 = Web3(HTTPProvider(RPC_URL))
Account.enable_unaudited_hdwallet_features()  # enable mnemonic -> account

def wei_to_eth(wei: int) -> float:
    return wei / 10**18

def eth_to_wei(eth: float) -> int:
    return int(eth * 10**18)

# -----------------------
# Wallet manager class
# -----------------------
class WalletManager:
    def __init__(self, keystore_dir: str = "keystores"):
        self.keystore_dir = Path(keystore_dir)
        self.keystore_dir.mkdir(parents=True, exist_ok=True)
        self.mnemo = Mnemonic("english")

    # 生成 N 个随机钱包（可选基于 mnemonic）
    def generate_wallets(self, n: int, use_mnemonic: bool = False, mnemonic_passphrase: Optional[str] = None) -> List[Dict[str, Any]]:
        wallets = []
        for i in range(n):
            if use_mnemonic:
                # 使用 BIP39 + HD derivation m/44'/60'/0'/0/index
                mnemonic = self.mnemo.generate(strength=128)  # 12 words
                acct = Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{0}")  # index 0 for simplicity
                wallets.append({
                    "mnemonic": mnemonic,
                    "address": acct.address,
                    "private_key": acct.key.hex()
                })
            else:
                acct = Account.create()  # random
                wallets.append({
                    "address": acct.address,
                    "private_key": acct.key.hex()
                })
        return wallets

    # 保存 keystore JSON（加密），返回文件路径
    def save_keystore(self, private_key_hex: str, password: str, filename_prefix: Optional[str] = None) -> Path:
        acct = Account.from_key(private_key_hex)
        keystore = Account.encrypt(private_key_hex, password)
        timestamp = int(time.time())
        fname = f"UTC--{timestamp}--{acct.address}"
        if filename_prefix:
            fname = f"{filename_prefix}--{fname}"
        path = self.keystore_dir / (fname + ".json")
        with open(path, "w") as f:
            json.dump(keystore, f)
        return path

    # 保存 mnemonic 明文（非常敏感，谨慎）
    def save_mnemonic(self, mnemonic: str, path: Optional[Path] = None):
        if path is None:
            path = self.keystore_dir / "mnemonics.txt"
        with open(path, "a") as f:
            f.write(mnemonic.strip() + "\n")
        return path

    # 从 keystore 加载 Account 对象（需要密码）
    def load_keystore(self, keystore_path: str, password: str) -> Account:
        with open(keystore_path, "r") as f:
            data = json.load(f)
        private_key = Account.decrypt(data, password)
        acct = Account.from_key(private_key)
        return acct

    # 从私钥加载
    def load_from_private_key(self, private_key_hex: str) -> Account:
        return Account.from_key(private_key_hex)

    # 查询单个地址余额（wei）
    def get_balance_wei(self, address: str) -> int:
        return w3.eth.get_balance(Web3.to_checksum_address(address))

    # 并发查询多个地址余额，返回 dict address -> balance_eth
    def get_balances(self, addresses: List[str], max_workers: int = 10) -> Dict[str, float]:
        out = {}
        def _get(addr):
            try:
                b = self.get_balance_wei(addr)
                return addr, wei_to_eth(b)
            except Exception as e:
                return addr, None
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(_get, addr) for addr in addresses]
            for fut in as_completed(futures):
                addr, bal = fut.result()
                out[addr] = bal
        return out

    # Send a single ETH transaction (returns tx hash hex)
    def send_eth(self,
                 from_private_key: str,
                 to_address: str,
                 value_eth: float,
                 gas_price_gwei: Optional[float] = None,
                 gas_limit: int = 21000,
                 chain_id: Optional[int] = None) -> str:
        acct = Account.from_key(from_private_key)
        from_addr = acct.address
        to_addr = Web3.to_checksum_address(to_address)
        nonce = w3.eth.get_transaction_count(from_addr)
        tx = {
            "nonce": nonce,
            "to": to_addr,
            "value": eth_to_wei(value_eth),
            "gas": gas_limit,
        }
        # gas price
        if gas_price_gwei is not None:
            tx["gasPrice"] = int(gas_price_gwei * 1e9)
        else:
            # try using base fee + tip via w3.eth.gas_price (may be EIP-1559 or legacy)
            try:
                tx["gasPrice"] = w3.eth.gas_price
            except:
                tx["gasPrice"] = int(20 * 1e9)  # fallback
        if chain_id is None:
            try:
                chain_id = w3.eth.chain_id
            except:
                chain_id = 1
        tx["chainId"] = chain_id

        signed = Account.sign_transaction(tx, private_key=from_private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        return tx_hash.hex()

    # 批量发送（顺序），wallets: list of dicts with 'private_key' and 'to' and 'value'
    def batch_send_sequential(self, jobs: List[Dict], pause_seconds: float = 0.2):
        results = []
        for job in jobs:
            try:
                txhash = self.send_eth(
                    from_private_key=job["private_key"],
                    to_address=job["to"],
                    value_eth=job["value_eth"],
                    gas_price_gwei=job.get("gas_price_gwei"),
                    gas_limit=job.get("gas_limit", 21000),
                )
                results.append({"status": "ok", "tx": txhash, "from": Account.from_key(job["private_key"]).address})
                # small pause to avoid nonce/rate problems
                time.sleep(pause_seconds)
            except Exception as e:
                results.append({"status": "error", "error": str(e), "from": Account.from_key(job["private_key"]).address})
        return results

    # 并发批量发送：要小心 nonce 和 race condition（本实现假设每个 from address 只会发一笔）
    def batch_send_concurrent(self, jobs: List[Dict], max_workers: int = 8):
        results = []
        def _send(job):
            try:
                txhash = self.send_eth(
                    from_private_key=job["private_key"],
                    to_address=job["to"],
                    value_eth=job["value_eth"],
                    gas_price_gwei=job.get("gas_price_gwei"),
                    gas_limit=job.get("gas_limit", 21000),
                )
                return {"status": "ok", "tx": txhash, "from": Account.from_key(job["private_key"]).address}
            except Exception as e:
                return {"status": "error", "error": str(e), "from": Account.from_key(job["private_key"]).address}

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(_send, job) for job in jobs]
            for fut in as_completed(futures):
                results.append(fut.result())
        return results

# -----------------------
# CLI / Example usage
# -----------------------
def example_usage():
    wm = WalletManager("keystores_demo")
    print("Network chain id:", w3.eth.chain_id)
    print("1) 生成 3 个随机钱包（仅私钥）并保存 keystore：")
    wallets = wm.generate_wallets(3, use_mnemonic=False)
    for i, w in enumerate(wallets):
        print(i, w["address"])
        # ask password interactively (demo); in automation pass password variable
        pw = "testpassword"  # demo; change to interactive in real use
        path = wm.save_keystore(w["private_key"], pw, filename_prefix=f"demo{i}")
        print(" saved keystore ->", path)

    print("\n2) 查询这些地址余额：")
    addrs = [w["address"] for w in wallets]
    balances = wm.get_balances(addrs)
    for a, b in balances.items():
        print(a, "ETH:", b)

    print("\n3) 批量发送示例（注意：需要有余额的地址）")
    # build jobs list - here just a template; DO NOT RUN unless funded and tested
    jobs = []
    for w in wallets:
        jobs.append({
            "private_key": w["private_key"],
            "to": wallets[0]["address"],  # just demo send back to first
            "value_eth": 0.0001,
        })
    # Uncomment to actually send
    results = wm.batch_send_sequential(jobs)
    print(results)

if __name__ == "__main__":
    # simple CLI interface
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--gen", type=int, help="Generate N wallets and save keystores")
    parser.add_argument("--mnemonic", action="store_true", help="Generate with mnemonic (12 words)")
    parser.add_argument("--list-balances", action="store_true", help="List balances of all keystores in dir")
    parser.add_argument("--keystore-dir", default="keystores", help="Keystore directory")
    parser.add_argument("--send-demo", action="store_true", help="Demo: load keystore and send small tx (interactive)")
    args = parser.parse_args()

    wm = WalletManager(args.keystore_dir)

    if args.gen:
        n = args.gen
        pwd = getpass("Enter password to encrypt keystores: ")
        wallets = wm.generate_wallets(n, use_mnemonic=args.mnemonic)
        for i, w in enumerate(wallets):
            pk = w["private_key"]
            path = wm.save_keystore(pk, pwd, filename_prefix=f"gen{i}")
            print("Generated:", w["address"], "->", path)
            if args.mnemonic and "mnemonic" in w:
                wm.save_mnemonic(w["mnemonic"])
                print(" saved mnemonic to mnemonics.txt (in keystore dir)")
        print("Done.")
        exit(0)

    if args.list_balances:
        files = list(Path(args.keystore_dir).glob("*.json"))
        addrs = []
        for f in files:
            try:
                data = json.load(open(f))
                addr = data.get("address") or data.get("id")  # keystore JSON format varies
                # best effort: find address inside
                if not addr:
                    # try searching for '"address":"0x...' substring
                    text = open(f).read()
                    import re
                    m = re.search(r'"address"\s*:\s*"([^"]+)"', text)
                    if m:
                        addr = m.group(1)
                if addr:
                    addrs.append(Web3.to_checksum_address(addr))
            except Exception:
                continue
        if not addrs:
            print("No addresses found in keystore dir.")
            exit(0)
        balances = wm.get_balances(addrs)
        for a,b in balances.items():
            print(a, "ETH:", b)
        exit(0)

    if args.send_demo:
        # interactive demo: pick a keystore, decrypt, and send
        files = list(Path(args.keystore_dir).glob("*.json"))
        if not files:
            print("No keystores found in", args.keystore_dir)
            exit(1)
        print("Found keystores:")
        for i,f in enumerate(files):
            print(i, f)
        idx = int(input("Choose index to use: "))
        pw = getpass("Password for keystore: ")
        acct = wm.load_keystore(str(files[idx]), pw)
        print("Using address:", acct.address)
        to = input("To address: ").strip()
        amount = float(input("Amount ETH: "))
        confirm = input(f"Send {amount} ETH from {acct.address} to {to}? (yes/no) ")
        if confirm.lower() != "yes":
            print("Cancelled.")
            exit(0)
        txhash = wm.send_eth(acct.key.hex(), to, amount)
        print("Tx sent:", txhash)
        exit(0)

    # default: show example usage
    example_usage()
