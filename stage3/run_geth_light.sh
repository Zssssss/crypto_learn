#!/bin/bash

# ===============================
# 一键启动 Geth 轻节点脚本
# ===============================

# 数据存储目录（可修改）
DATADIR="$HOME/geth_lightnode"

# 端口配置
HTTP_PORT=8545
WS_PORT=8546

# 网络选择: "mainnet" 或 "goerli"
NETWORK="mainnet"

# 检查 geth 是否已安装
if ! command -v geth &> /dev/null
then
    echo "geth 未安装，请先安装 Geth 客户端"
    exit 1
fi

echo "启动 Geth 轻节点..."
echo "数据目录: $DATADIR"
echo "网络: $NETWORK"

# 启动命令
geth \
  --syncmode "light" \
  --$NETWORK \
  --datadir "$DATADIR" \
  --http \
  --http.addr "0.0.0.0" \
  --http.port $HTTP_PORT \
  --http.api eth,net,web3 \
  --ws \
  --ws.addr "0.0.0.0" \
  --ws.port $WS_PORT \
  --ws.api eth,net,web3 \
  --cache 512 \
  --allow-insecure-unlock
