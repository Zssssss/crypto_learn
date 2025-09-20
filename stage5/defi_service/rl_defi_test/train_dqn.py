#!/usr/bin/env python3
"""
DQN训练脚本
用于训练基于深度Q网络的永续合约交易代理
"""
import os
import yaml
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import argparse

from stable_baselines3 import DQN
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from stable_baselines3.common.monitor import Monitor

from env.trading_env import TradingEnv
from data_loader import load_csv
from utils import add_technical_indicators, calculate_performance_metrics, setup_logging

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)


class TradingCallback(EvalCallback):
    """自定义评估回调"""
    
    def __init__(self, eval_env, **kwargs):
        super().__init__(eval_env, **kwargs)
        self.best_sharpe = -float('inf')
        
    def _on_step(self) -> bool:
        """每步回调"""
        return super()._on_step()


def create_training_env(config: dict) -> TradingEnv:
    """创建训练环境"""
    # 加载数据
    df = load_csv(config["data"]["csv_path"])
    
    # 添加技术指标
    df = add_technical_indicators(df)
    
    # 创建环境
    env = TradingEnv(
        df=df,
        window_size=config["env"]["window_size"],
        fee_rate=config["env"]["fee_rate"],
        initial_balance=config["account"]["initial_balance"],
        leverage=config["env"].get("leverage", 10.0),
        max_position_size=config["env"].get("max_position_size", 1.0)
    )
    
    # 包装环境以记录统计信息
    env = Monitor(env)
    
    return env


def create_eval_env(config: dict, train_ratio: float = 0.7) -> TradingEnv:
    """创建评估环境"""
    # 加载数据
    df = load_csv(config["data"]["csv_path"])
    df = add_technical_indicators(df)
    
    # 使用不同的数据分割进行评估
    split_idx = int(len(df) * train_ratio)
    eval_df = df[split_idx:]
    
    env = TradingEnv(
        df=eval_df,
        window_size=config["env"]["window_size"],
        fee_rate=config["env"]["fee_rate"],
        initial_balance=config["account"]["initial_balance"],
        leverage=config["env"].get("leverage", 10.0),
        max_position_size=config["env"].get("max_position_size", 1.0)
    )
    
    return Monitor(env)


def train_dqn(config_path: str = "configs/config.yaml"):
    """训练DQN模型"""
    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # 创建环境
    env = create_training_env(config)
    
    # 创建评估环境
    eval_env = create_eval_env(config)
    
    # 创建模型保存目录
    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(os.path.join(model_dir, "checkpoints"), exist_ok=True)
    os.makedirs(os.path.join(model_dir, "best_model"), exist_ok=True)
    os.makedirs(os.path.join(model_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(model_dir, "tensorboard"), exist_ok=True)
    
    # 创建回调
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path=os.path.join(model_dir, "checkpoints"),
        name_prefix="dqn_perp"
    )
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=os.path.join(model_dir, "best_model"),
        log_path=os.path.join(model_dir, "logs"),
        eval_freq=10000,
        n_eval_episodes=10,
        deterministic=True
    )
    
    # 创建DQN模型
    model = DQN(
        "MlpPolicy",
        env,
        learning_rate=config["training"]["learning_rate"],
        buffer_size=100000,
        learning_starts=1000,
        batch_size=config["training"]["batch_size"],
        gamma=0.99,
        target_update_interval=1000,
        train_freq=4,
        gradient_steps=1,
        exploration_fraction=0.1,
        exploration_final_eps=0.01,
        verbose=1,
        tensorboard_log=os.path.join(model_dir, "tensorboard")
    )
    
    # 训练模型
    logger.info("Starting DQN training...")
    model.learn(
        total_timesteps=config["training"]["total_timesteps"],
        callback=[checkpoint_callback, eval_callback]
    )
    
    # 保存最终模型
    final_model_path = os.path.join(model_dir, "dqn_perp_final")
    model.save(final_model_path)
    logger.info(f"Training completed. Final model saved to {final_model_path}")
    
    # 评估最终模型
    logger.info("Evaluating final model...")
    obs, _ = eval_env.reset()
    done = False
    trades = []
    
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, _, info = eval_env.step(action)
        
        # 收集交易信息
        if 'trades' in info:
            trades.extend(info['trades'])
    
    # 计算性能指标
    if trades:
        metrics = calculate_performance_metrics(trades, config["account"]["initial_balance"])
        logger.info("Performance Metrics:")
        for key, value in metrics.items():
            logger.info(f"  {key}: {value:.4f}")
    
    return model


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Train DQN agent for perpetual futures trading")
    parser.add_argument("--config", type=str, default="configs/config.yaml", help="Config file path")
    parser.add_argument("--timesteps", type=int, help="Override total timesteps")
    
    args = parser.parse_args()
    
    # 如果提供了时间步参数，更新配置
    if args.timesteps:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        config["training"]["total_timesteps"] = args.timesteps
        with open(args.config, 'w') as f:
            yaml.dump(config, f)
    
    # 训练模型
    model = train_dqn(args.config)
    
    return model


if __name__ == "__main__":
    main()