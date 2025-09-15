# bot_exec.py
import os
import time
import json
from decimal import Decimal
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

RPC = os.environ.get("RPC_URL")
ACCOUNT = Web3.to_checksum_address(os.environ.get("ACCOUNT"))
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")
EXECUTOR = Web3.to_checksum_address(os.environ.get("EXECUTOR"))

w3 = Web3(Web3.HTTPProvider(RPC))

# ---------- on-chain addresses (Arbitrum) ----------
USDT = Web3.to_checksum_address("0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9")
WETH = Web3.to_checksum_address("0x82af49447d8a07e3bd95bd0d56f35241523fbab1")
QUOTER_V2 = Web3.to_checksum_address("0x61FFE014BA17989E743C5F6CB21BF9697530B21E")  # if present
ROUTER_V3 = Web3.to_checksum_address("0xE592427A0AEce92De3Edee1F18E0157C05861564")
ROUTER_V2 = Web3.to_checksum_address("0xf2614A233c7C3e7f08b1F887Ba133a13f1eb2c55")  # sushi example
FEE_V3 = 3000

# ---------- ABIs (minimal fragments) ----------
QUOTER_ABI = json.loads('[{ "inputs":[{"components":[{"internalType":"address","name":"tokenIn","type":"address"},{"internalType":"address","name":"tokenOut","type":"address"},{"internalType":"uint24","name":"fee","type":"uint24"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMinimum","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceLimitX96","type":"uint160"}],"internalType":"struct IQuoterV2.ExactInputSingleParams","name":"params","type":"tuple"}],"name":"quoteExactInputSingle","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint160","name":"sqrtPriceX96After","type":"uint160"},{"internalType":"uint32","name":"initializedTicksCrossed","type":"uint32"},{"internalType":"uint256","name":"gasEstimate","type":"uint256"}],"stateMutability":"nonpayable","type":"function"}]')
V2_ROUTER_ABI = json.loads('[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"}]')
ERC20_ABI = json.loads('[{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"spender","type":"address"},{"name":"value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},{"constant":true,"inputs":[{"name":"owner","type":"address"},{"name":"spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"type":"function"}]')
EXECUTOR_ABI = json.loads('[{"inputs":[{"internalType":"address","name":"usdt","type":"address"},{"internalType":"address","name":"midToken","type":"address"},{"internalType":"address","name":"v3Router","type":"address"},{"internalType":"address","name":"v2Router","type":"address"},{"internalType":"uint24","name":"v3Fee","type":"uint24"},{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"minProfit","type":"uint256"},{"internalType":"uint256","name":"v3MinOut","type":"uint256"},{"internalType":"uint256","name":"v2MinOut","type":"uint256"}],"name":"arb_USDT_V3_V2","outputs":[],"stateMutability":"nonpayable","type":"function"}]')

quoter = w3.eth.contract(address=QUOTER_V2, abi=QUOTER_ABI)
v2router = w3.eth.contract(address=ROUTER_V2, abi=V2_ROUTER_ABI)
usdt_contract = w3.eth.contract(address=USDT, abi=ERC20_ABI)
execC = w3.eth.contract(address=EXECUTOR, abi=EXECUTOR_ABI)

# ---------- params ----------
AMOUNT_USDT = 100 * (10**6)         # 100 USDT (6 decimals)
MIN_NET_PROFIT_USDT = int(0.5 * 1e6)  # 最小净盈利 0.5 USDT
SLIPPAGE_BPS = 40                   # 0.4% slippage tolerance

# ---------- helper functions ----------
def quote_v3_to_weth(amount_in_usdt):
    try:
        out = quoter.functions.quoteExactInputSingle((USDT, WETH, FEE_V3, "0x0000000000000000000000000000000000000000", amount_in_usdt, 0, 0)).call()
        return int(out[0])
    except Exception as e:
        # print("v3 quote err", e)
        return 0

def quote_v2_get_back(amount_mid):
    try:
        amounts = v2router.functions.getAmountsOut(amount_mid, [WETH, USDT]).call()
        return int(amounts[-1])
    except Exception as e:
        # print("v2 quote err", e)
        return 0

def estimate_gas_usdt():
    # Use eth_estimateGas by building a sample call to executor with conservative mins
    try:
        # dummy mins = 0 for estimate
        v3_min = 1
        v2_min = 1
        txn = execC.functions.arb_USDT_V3_V2(USDT, WETH, ROUTER_V3, ROUTER_V2, FEE_V3, AMOUNT_USDT, 1, v3_min, v2_min).build_transaction({
            "from": ACCOUNT,
        })
        gas_est = w3.eth.estimate_gas(txn)
        gas_price = w3.eth.gas_price
        wei_cost = gas_est * gas_price
        # convert wei to USDT using quoter WETH->USDT price (approx)
        # estimate ETH per wei => wei_cost / 1e18 ETH ; find ETH->USDT via quoter
        eth_to_usdt = quoter.functions.quoteExactInputSingle((WETH, USDT, FEE_V3, "0x0000000000000000000000000000000000000000", 10**18, 0, 0)).call()[0]
        if eth_to_usdt == 0:
            return int(0.5 * 1e6)
        usdt_cost = (Decimal(wei_cost) / Decimal(10**18)) * Decimal(eth_to_usdt) / Decimal(10**6)
        return int(usdt_cost * (10**6))  # 6-decimals
    except Exception as e:
        # fallback estimate (0.5 USDT)
        return int(0.5 * 1e6)

def ensure_allowance(amount):
    allow = usdt_contract.functions.allowance(ACCOUNT, EXECUTOR).call()
    if allow >= amount:
        return True
    # send approve tx
    tx = usdt_contract.functions.approve(EXECUTOR, amount).build_transaction({
        "from": ACCOUNT,
        "nonce": w3.eth.get_transaction_count(ACCOUNT),
        "gasPrice": w3.eth.gas_price,
        "gas": 100000
    })
    signed = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print("approve sent:", tx_hash.hex())
    # wait for receipt simple loop
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return receipt.status == 1

# ---------- main loop ----------
def main_loop():
    print("Bot start. Monitoring opportunities...")
    while True:
        try:
            # 1) quote legs
            mid_out = quote_v3_to_weth(AMOUNT_USDT)  # WETH amount (18dec)
            if mid_out == 0:
                time.sleep(1); continue
            back_out = quote_v2_get_back(mid_out)    # USDT (6dec)
            if back_out == 0:
                time.sleep(1); continue

            gross = back_out - AMOUNT_USDT  # unit: USDT 6dec
            gas_cost = estimate_gas_usdt()

            print(f"[QUOTE] back_out={back_out/1e6:.6f} USDT gross={gross/1e6:.6f} USDT gas_est={gas_cost/1e6:.6f} USDT")

            if gross > gas_cost + MIN_NET_PROFIT_USDT:
                # Good opportunity — prepare mins with slippage
                v3MinOut = int(mid_out * (10000 - SLIPPAGE_BPS) // 10000)
                v2MinOut = int(back_out * (10000 - SLIPPAGE_BPS) // 10000)

                print(">> Found potential arb. Ensuring allowance...")
                ok = ensure_allowance(AMOUNT_USDT)
                if not ok:
                    print("Approve failed, skip.")
                    time.sleep(2); continue

                # Build transaction using realistic gas estimate
                func = execC.functions.arb_USDT_V3_V2(USDT, WETH, ROUTER_V3, ROUTER_V2, FEE_V3, AMOUNT_USDT, int(MIN_NET_PROFIT_USDT), v3MinOut, v2MinOut)
                tx_base = func.build_transaction({
                    "from": ACCOUNT,
                    "nonce": w3.eth.get_transaction_count(ACCOUNT),
                    "gasPrice": w3.eth.gas_price,
                })

                # estimate gas for this exact call (may revert on estimate if require conditions fail)
                try:
                    gas_est = w3.eth.estimate_gas(tx_base)
                except Exception as e:
                    # estimation may fail if on-chain state changed; set conservative limit
                    gas_est = 700000
                gas_limit = int(gas_est * 1.2)  # 20% buffer

                tx = func.build_transaction({
                    "from": ACCOUNT,
                    "nonce": tx_base["nonce"],
                    "gasPrice": w3.eth.gas_price,
                    "gas": gas_limit,
                    "value": 0
                })

                signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
                tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
                print("arb tx sent:", tx_hash.hex())
                # Wait for confirmation
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
                if receipt.status == 1:
                    print("✅ Arb executed successfully:", tx_hash.hex())
                else:
                    print("❌ Arb tx failed (reverted):", tx_hash.hex())

                # small cooldown
                time.sleep(5)
            else:
                # not profitable
                time.sleep(1)
        except Exception as e:
            print("Loop error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main_loop()
