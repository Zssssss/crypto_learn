import hashlib
import json
import requests
import time

RPC_USER = "123"
RPC_PASSWORD = "123"
RPC_PORT = 8332
RPC_URL = f"http://127.0.0.1:{RPC_PORT}/"

def rpc_call(method, params=[]):
    import requests, json
    payload = json.dumps({
        "jsonrpc": "1.0",
        "id": "pythonminer",
        "method": method,
        "params": params
    })
    headers = {"content-type": "application/json"}
    response = requests.post(RPC_URL, data=payload, headers=headers, auth=(RPC_USER, RPC_PASSWORD))
    import pdb;pdb.set_trace()
    return response.json()

# 获取区块模板
def get_block_template():
    return rpc_call("getblocktemplate", [{"rules": ["segwit"]}])

# 挖矿函数
def mine_block(template, address):
    target = int(template["target"], 16)  # 难度目标
    header = {
        "version": template["version"],
        "previousblockhash": template["previousblockhash"],
        "transactions": [],
        "coinbaseaux": {"flags": ""},
        "coinbasevalue": template["coinbasevalue"],
        "longpollid": template["longpollid"],
        "bits": template["bits"],
        "height": template["height"]
    }

    print(f"开始挖矿... 区块高度 {header['height']}")
    nonce = 0
    while True:
        block_header = f"{header['version']}{header['previousblockhash']}{nonce}".encode()
        hash_result = hashlib.sha256(hashlib.sha256(block_header).digest()).digest()
        hash_int = int.from_bytes(hash_result, byteorder="big")

        if hash_int < target:
            print(f"找到区块! Nonce={nonce}")
            # 提交区块
            block_hex = rpc_call("getblocktemplate", [{"rules": ["segwit"]}])
            rpc_call("generatetoaddress", [1, address])  # 本地直接生成
            break
        nonce += 1

if __name__ == "__main__":
    address = rpc_call("getnewaddress")
    print(f"奖励地址: {address}")

    while True:
        tmpl = get_block_template()
        mine_block(tmpl, address)
        time.sleep(2)
