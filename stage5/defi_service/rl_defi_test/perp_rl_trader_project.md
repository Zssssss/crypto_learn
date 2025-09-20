# Perpetuals RL Trading Agent Project

This repository contains a complete runnable project scaffold for training and running a reinforcement-learning agent on perpetual-futures (perp) markets. It supports: historical backtesting, gym-style environment, DQN / PPO training scripts (stable-baselines3), a realtime data adapter stub for Hyper-like perp DEX via WebSocket, utilities, and a Dockerfile.

---

## Project structure

```
perp_rl_trader/
├── README.md
├── requirements.txt
├── Dockerfile
├── configs/
│   └── config.yaml
├── data/
│   └── sample_data.csv
├── env/
│   └── trading_env.py
├── data_loader.py
├── realtime_adapter.py
├── train_dqn.py
├── train_ppo.py
├── utils.py
└── scripts/
    └── run_backtest.sh
```

---

## `requirements.txt`

```text
numpy
pandas
matplotlib
gymnasium
stable-baselines3[extra]==2.0.0
torch
pyyaml
websockets
ta
python-dotenv
```

---

## `Dockerfile`

```Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
CMD ["bash"]
```

---

## `configs/config.yaml`

```yaml
# hyper-parameters and paths
data:
  csv_path: data/sample_data.csv
env:
  window_size: 50
  fee_rate: 0.0005
training:
  total_timesteps: 200000
  algo: dqn # dqn or ppo
account:
  initial_balance: 1000.0
realtime:
  websocket_url: "wss://example-hyper-ws"
  symbol: "BTC-PERP"
```

---

## `data/sample_data.csv`

A small CSV example with columns: `timestamp, open, high, low, close, volume`.

(You can paste your historical kline CSV here.)

---

## `env/trading_env.py`

```python
import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Optional


class TradingEnv(gym.Env):
    """
    Gym-style trading environment for perpetual futures.

    Observations:
      - normalized window of closes (window_size)
      - normalized features (optional)
      - position (1, -1, 0), entry_price, balance

    Actions (Discrete):
      0 - Hold
      1 - Open Long (if flat)
      2 - Open Short (if flat)
      3 - Close position (if any)

    Reward:
      - change in equity (balance + unrealized_pnl) minus fees
    """

    metadata = {"render.modes": ["human"]}

    def __init__(self, df: pd.DataFrame, window_size: int = 50, fee_rate: float = 0.0005, initial_balance: float = 1000.0):
        super().__init__()
        assert "close" in df.columns, "df must contain 'close' column"
        self.df = df.reset_index(drop=True)
        self.window_size = window_size
        self.fee_rate = fee_rate
        self.initial_balance = initial_balance

        # discrete actions
        self.action_space = spaces.Discrete(4)

        # observation: window_size closes + 3 account features
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(window_size + 3,), dtype=np.float32)

        self._reset_internal()

    def _reset_internal(self):
        self.current_step = self.window_size
        self.balance = float(self.initial_balance)
        self.position = 0  # 1 long, -1 short, 0 flat
        self.entry_price = 0.0
        self.prev_equity = float(self.initial_balance)
        self.done = False

    def _get_window(self):
        start = self.current_step - self.window_size
        window = self.df["close"].iloc[start:self.current_step].values.astype(np.float32)
        # normalize by last price in window
        base = window[-1]
        norm = window / base - 1.0
        return norm

    def _get_observation(self):
        w = self._get_window()
        account = np.array([float(self.position), float(self.entry_price), float(self.balance)], dtype=np.float32)
        obs = np.concatenate([w, account])
        return obs

    def step(self, action: int):
        if self.done:
            return self._get_observation(), 0.0, True, {}, {"msg": "already done"}

        price = float(self.df["close"].iloc[self.current_step])
        fee = 0.0

        # Execute action
        if action == 1:  # open long
            if self.position == 0:
                self.position = 1
                self.entry_price = price
                fee = price * self.fee_rate
                self.balance -= fee
        elif action == 2:  # open short
            if self.position == 0:
                self.position = -1
                self.entry_price = price
                fee = price * self.fee_rate
                self.balance -= fee
        elif action == 3:  # close
            if self.position != 0:
                pnl = (price - self.entry_price) * self.position
                self.balance += pnl
                fee = price * self.fee_rate
                self.balance -= fee
                self.position = 0
                self.entry_price = 0.0
        # else action 0: hold

        # Compute unrealized pnl
        unrealized = 0.0
        if self.position != 0:
            unrealized = (price - self.entry_price) * self.position

        equity = self.balance + unrealized
        reward = equity - self.prev_equity
        self.prev_equity = equity

        self.current_step += 1
        if self.current_step >= len(self.df):
            self.done = True

        obs = self._get_observation()
        info = {"equity": equity, "balance": self.balance, "position": self.position, "fee": fee}
        return obs, float(reward), bool(self.done), False, info

    def reset(self, *, seed: Optional[int] = None, options=None):
        super().reset(seed=seed)
        self._reset_internal()
        return self._get_observation(), {}

    def render(self, mode="human"):
        print(f"step={self.current_step} balance={self.balance:.4f} position={self.position} entry={self.entry_price}")

```

---

## `data_loader.py`

```python
import pandas as pd


def load_csv(path: str) -> pd.DataFrame:
    """Load CSV and ensure columns exist: timestamp, open, high, low, close, volume"""
    df = pd.read_csv(path)
    # basic checks
    for c in ["timestamp", "open", "high", "low", "close"]:
        if c not in df.columns:
            raise ValueError(f"Missing column: {c}")
    # sort by time
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df
```

---

## `realtime_adapter.py`

```python
"""
Simple realtime websocket adapter stub.

Replace URL and message parsing with the actual Hyper (or other perp DEX) websocket schema.
This file exposes an async generator `subscribe_klines` that yields new kline rows as dicts.
"""
import asyncio
import json
import websockets
from typing import AsyncGenerator, Dict


async def subscribe_klines(ws_url: str, symbol: str) -> AsyncGenerator[Dict, None]:
    """Connect to ws_url and yield kline dicts. Customize per exchange API."""
    async with websockets.connect(ws_url) as ws:
        # example subscription message; change to actual API
        sub = {"type": "subscribe", "channel": "kline", "symbol": symbol}
        await ws.send(json.dumps(sub))
        async for msg in ws:
            data = json.loads(msg)
            # parse according to API
            # yield dict must contain: timestamp, open, high, low, close, volume
            try:
                k = data.get("kline") or data
                yield {
                    "timestamp": k["ts"],
                    "open": float(k["open"]),
                    "high": float(k["high"]),
                    "low": float(k["low"]),
                    "close": float(k["close"]),
                    "volume": float(k.get("volume", 0.0)),
                }
            except Exception:
                continue


# Small runner example
if __name__ == "__main__":
    async def main():
        async for k in subscribe_klines("wss://example", "BTC-PERP"):
            print(k)

    asyncio.run(main())
```

---

## `utils.py`

```python
import numpy as np
import pandas as pd
import talib as ta


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close = df["close"].values
    df["ma10"] = ta.SMA(close, timeperiod=10)
    df["ma50"] = ta.SMA(close, timeperiod=50)
    df["rsi"] = ta.RSI(close, timeperiod=14)
    df["atr"] = ta.ATR(df["high"].values, df["low"].values, df["close"].values, timeperiod=14)
    df = df.fillna(method="bfill").fillna(0)
    return df


def create_obs_from_df(df: pd.DataFrame, idx: int, window: int):
    start = idx - window
    window_df = df.iloc[start:idx]
    # use normalized close
    closes = window_df["close"].values
    norm = closes / closes[-1] - 1.0
    return norm
```

---

## `train_dqn.py`

```python
import yaml
import pandas as pd
from stable_baselines3 import DQN
from env.trading_env import TradingEnv
from data_loader import load_csv


def main(config_path="configs/config.yaml"):
    cfg = yaml.safe_load(open(config_path, "r"))
    df = load_csv(cfg["data"]["csv_path"])  # ensure you have a CSV

    env = TradingEnv(df, window_size=cfg["env"]["window_size"], fee_rate=cfg["env"]["fee_rate"], initial_balance=cfg["account"]["initial_balance"])

    model = DQN("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=cfg["training"]["total_timesteps"])
    model.save("models/dqn_perp")


if __name__ == "__main__":
    main()
```

---

## `train_ppo.py`

```python
import yaml
import pandas as pd
from stable_baselines3 import PPO
from env.trading_env import TradingEnv
from data_loader import load_csv


def main(config_path="configs/config.yaml"):
    cfg = yaml.safe_load(open(config_path, "r"))
    df = load_csv(cfg["data"]["csv_path"])  # ensure you have a CSV

    env = TradingEnv(df, window_size=cfg["env"]["window_size"], fee_rate=cfg["env"]["fee_rate"], initial_balance=cfg["account"]["initial_balance"])

    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=cfg["training"]["total_timesteps"])
    model.save("models/ppo_perp")


if __name__ == "__main__":
    main()
```

---

## `scripts/run_backtest.sh`

```bash
#!/usr/bin/env bash
python train_dqn.py
```

---

## `README.md` (short)

```markdown
# Perp RL Trader

This project trains an RL agent to trade perpetual swap markets.

## Quickstart

1. Install dependencies: `pip install -r requirements.txt`
2. Put historical klines CSV into `data/sample_data.csv` (columns: timestamp, open, high, low, close, volume)
3. Edit `configs/config.yaml` if needed
4. Run `python train_dqn.py`

## Next steps
- Extend observation with orderbook/funding rate
- Replace `realtime_adapter` with the real exchange websocket
- Add risk management wrapper to enforce max drawdown
```

---

If you'd like, I can now:

- generate these files as a downloadable zip, or
- implement a more advanced environment (multiscale features, margin/leveraged position math, partial position sizes), or
- connect to a specific Hyper (please provide exact websocket/API docs) for a working realtime adapter.

Tell me which one you want next.

