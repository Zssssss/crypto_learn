import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TradingEnv(gym.Env):
    """
    Gym-style trading environment for perpetual futures on Hyper.
    
    Actions:
      0 - Hold
      1 - Open Long
      2 - Open Short  
      3 - Close position
    
    Reward:
      - Change in equity (balance + unrealized_pnl) minus fees
    """
    
    metadata = {"render_modes": ["human"]}
    
    def __init__(
        self, 
        df: pd.DataFrame, 
        window_size: int = 50, 
        fee_rate: float = 0.0005,
        initial_balance: float = 1000.0,
        leverage: float = 10.0,
        max_position_size: float = 1.0
    ):
        super().__init__()
        
        assert "close" in df.columns, "df must contain 'close' column"
        self.df = df.reset_index(drop=True)
        self.window_size = window_size
        self.fee_rate = fee_rate
        self.initial_balance = initial_balance
        self.leverage = leverage
        self.max_position_size = max_position_size
        
        # 离散动作空间
        self.action_space = spaces.Discrete(4)
        
        # 观察空间: 价格窗口 + 账户状态
        self.observation_space = spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(window_size + 6,),  # 价格窗口 + 6个账户特征
            dtype=np.float32
        )
        
        self._reset_internal()
        
    def _reset_internal(self):
        """重置内部状态"""
        self.current_step = self.window_size
        self.balance = float(self.initial_balance)
        self.position = 0.0  # 持仓量
        self.position_side = 0  # 1=多头, -1=空头, 0=空仓
        self.entry_price = 0.0
        self.prev_equity = float(self.initial_balance)
        self.done = False
        self.trades = []
        
    def _get_window(self) -> np.ndarray:
        """获取价格窗口数据"""
        start = max(0, self.current_step - self.window_size)
        window = self.df["close"].iloc[start:self.current_step].values.astype(np.float32)
        
        # 标准化处理
        if len(window) > 0:
            base = window[-1]
            if base != 0:
                norm = window / base - 1.0
            else:
                norm = np.zeros_like(window)
        else:
            norm = np.zeros(self.window_size)
            
        # 确保窗口大小一致
        if len(norm) < self.window_size:
            norm = np.pad(norm, (self.window_size - len(norm), 0), mode='constant')
            
        return norm
    
    def _get_observation(self) -> np.ndarray:
        """构建观察向量"""
        price_window = self._get_window()
        
        # 账户状态特征
        account_features = np.array([
            float(self.position_side),           # 持仓方向
            float(self.position),                # 持仓量
            float(self.entry_price),            # 入场价格
            float(self.balance),                # 账户余额
            float(self._get_unrealized_pnl()),   # 未实现盈亏
            float(self._get_margin_ratio())      # 保证金比率
        ], dtype=np.float32)
        
        return np.concatenate([price_window, account_features])
    
    def _get_unrealized_pnl(self) -> float:
        """计算未实现盈亏"""
        if self.position == 0:
            return 0.0
            
        current_price = float(self.df["close"].iloc[self.current_step])
        price_diff = current_price - self.entry_price
        
        if self.position_side == 1:  # 多头
            return price_diff * self.position * self.leverage
        else:  # 空头
            return -price_diff * self.position * self.leverage
    
    def _get_margin_ratio(self) -> float:
        """计算保证金比率"""
        if self.position == 0:
            return 0.0
            
        current_price = float(self.df["close"].iloc[self.current_step])
        position_value = self.position * current_price * self.leverage
        margin_used = position_value / self.leverage
        
        if self.balance > 0:
            return margin_used / self.balance
        return 0.0
    
    def _calculate_reward(self) -> float:
        """计算奖励"""
        equity = self.balance + self._get_unrealized_pnl()
        reward = equity - self.prev_equity
        self.prev_equity = equity
        return float(reward)
    
    def step(self, action: int):
        """执行一步交易"""
        if self.done:
            return self._get_observation(), 0.0, True, False, {"msg": "already done"}
            
        current_price = float(self.df["close"].iloc[self.current_step])
        fee = 0.0
        
        # 执行动作
        if action == 1:  # 开多
            if self.position_side == 0:
                position_size = min(
                    self.max_position_size,
                    (self.balance * 0.8) / (current_price / self.leverage)
                )
                if position_size > 0:
                    self.position = position_size
                    self.position_side = 1
                    self.entry_price = current_price
                    fee = current_price * self.position * self.fee_rate
                    self.balance -= fee
                    
        elif action == 2:  # 开空
            if self.position_side == 0:
                position_size = min(
                    self.max_position_size,
                    (self.balance * 0.8) / (current_price / self.leverage)
                )
                if position_size > 0:
                    self.position = position_size
                    self.position_side = -1
                    self.entry_price = current_price
                    fee = current_price * self.position * self.fee_rate
                    self.balance -= fee
                    
        elif action == 3:  # 平仓
            if self.position > 0:
                # 计算已实现盈亏
                pnl = self._get_unrealized_pnl()
                self.balance += pnl
                
                # 平仓手续费
                fee = current_price * self.position * self.fee_rate
                self.balance -= fee
                
                # 记录交易
                self.trades.append({
                    'entry_price': self.entry_price,
                    'exit_price': current_price,
                    'side': self.position_side,
                    'size': self.position,
                    'pnl': pnl - fee,
                    'balance': self.balance
                })
                
                # 重置仓位
                self.position = 0.0
                self.position_side = 0
                self.entry_price = 0.0
                
        # action 0: 持仓不动
        
        # 检查是否爆仓
        equity = self.balance + self._get_unrealized_pnl()
        if equity <= 0:
            self.done = True
            logger.warning(f"Liquidation at step {self.current_step}")
            
        # 检查是否到达数据末尾
        self.current_step += 1
        if self.current_step >= len(self.df):
            self.done = True
            
        # 计算奖励
        reward = self._calculate_reward()
        
        obs = self._get_observation()
        info = {
            "equity": equity,
            "balance": self.balance,
            "position": self.position,
            "position_side": self.position_side,
            "unrealized_pnl": self._get_unrealized_pnl(),
            "fee": fee,
            "current_price": current_price
        }
        
        return obs, reward, self.done, False, info
    
    def reset(self, *, seed: Optional[int] = None, options=None):
        """重置环境"""
        super().reset(seed=seed)
        self._reset_internal()
        return self._get_observation(), {}
    
    def render(self, mode="human"):
        """渲染当前状态"""
        equity = self.balance + self._get_unrealized_pnl()
        print(
            f"Step: {self.current_step} | "
            f"Balance: {self.balance:.4f} | "
            f"Position: {self.position_side * self.position:.4f} | "
            f"Entry: {self.entry_price:.4f} | "
            f"Equity: {equity:.4f} | "
            f"PnL: {self._get_unrealized_pnl():.4f}"
        )
        
    def get_trades(self) -> list:
        """获取交易记录"""
        return self.trades