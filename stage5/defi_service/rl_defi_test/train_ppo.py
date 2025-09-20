#!/usr/bin/env python3
"""
PPO训练脚本
用于训练基于近端策略优化的永续合约交易代理
"""
import os
import yaml
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import argparse

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.utils import set_random_seed

from env.trading_env import TradingEnv
from data_loader import load_csv
from utils import add_technical_indicators, calculate_performance_metrics, setup_logging

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)


def make_env(df: pd.DataFrame, config: dict, rank: int = 0):
    """创建环境工厂函数"""
    def _init():
        env = TradingEnv(
            df=df,
            window_size=config["env"]["window_size"],
            fee_rate=config["env"]["fee_rate"],
            initial_balance=config["account"]["initial_balance"],
            leverage=config["env"].get("leverage", 10.0),
            max_position_size=config["env"].get("max_position_size", 1.0)
        )
        env = Monitor(env)
        return env
    return _init


def create_training_env(config: dict, n_envs: int = 4):
    """创建并行训练环境"""
    # 加载数据
    df = load_csv(config["data"]["csv_path"])
    df = add_technical_indicators(df)
    
    # 创建多个环境实例
    env_fns = [make_env(df, config, i) for i in range(n_envs)]
    
    # 使用子进程向量环境
    if n_envs > 1:
        env = SubprocVecEnv(env_fns)
    else:
        env = DummyVecEnv(env_fns)
    
    return env


def create_eval_env(config: dict, train_ratio: float = 0.7):
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


def train_ppo(config_path: str = "configs/config.yaml"):
    """训练PPO模型"""
    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # 设置随机种子
    set_random_seed(42)
    
    # 创建环境
    n_envs = 4  # 并行环境数量
    env = create_training_env(config, n_envs)
    
    # 创建评估环境
    eval_env = create_eval_env(config)
    
    # 创建模型保存目录
    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(os.path.join(model_dir, "checkpoints"), exist_ok=True)
    os.makedirs(os.path.join(model_dir, "best_model_ppo"), exist_ok=True)
    os.makedirs(os.path.join(model_dir, "logs_ppo"), exist_ok=True)
    os.makedirs(os.path.join(model_dir, "tensorboard_ppo"), exist_ok=True)
    
    # 创建回调
    checkpoint_callback = CheckpointCallback(
        save_freq=50000 // n_envs,
        save_path=os.path.join(model_dir, "checkpoints"),
        name_prefix="ppo_perp"
    )
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=os.path.join(model_dir, "best_model_ppo"),
        log_path=os.path.join(model_dir, "logs_ppo"),
        eval_freq=25000 // n_envs,
        n_eval_episodes=10,
        deterministic=True
    )
    
    # 创建PPO模型
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=config["training"]["learning_rate"],
        n_steps=2048,
        batch_size=config["training"]["batch_size"],
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        clip_range_vf=None,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        use_sde=False,
        sde_sample_freq=-1,
        verbose=1,
        tensorboard_log=os.path.join(model_dir, "tensorboard_ppo")
    )
    
    # 训练模型
    logger.info("Starting PPO training...")
    total_timesteps = config["training"]["total_timesteps"]
    
    model.learn(
        total_timesteps=total_timesteps,
        callback=[checkpoint_callback, eval_callback]
    )
    
    # 保存最终模型
    final_model_path = os.path.join(model_dir, "ppo_perp_final")
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
        if hasattr(eval_env, 'env'):
            env_instance = eval_env.env
        else:
            env_instance = eval_env
            
        trades.extend(env_instance.get_trades())
    
    # 计算性能指标
    if trades:
        metrics = calculate_performance_metrics(trades, config["account"]["initial_balance"])
        logger.info("Performance Metrics:")
        for key, value in metrics.items():
            logger.info(f"  {key}: {value:.4f}")
    
    # 清理环境
    env.close()
    eval_env.close()
    
    return model


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Train PPO agent for perpetual futures trading")
    parser.add_argument("--config", type=str, default="configs/config.yaml", help="Config file path")
    parser.add_argument("--timesteps", type=int, help="Override total timesteps")
    parser.add_argument("--n-envs", type=int, default=4, help="Number of parallel environments")
    
    args = parser.parse_args()
    
    # 如果提供了时间步参数，更新配置
    if args.timesteps:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        config["training"]["total_timesteps"] = args.timesteps
        with open(args.config, 'w') as f:
            yaml.dump(config, f)
    
    # 训练模型
    model = train_ppo(args.config)
    
    return model


if __name__ == "__main__":
    main()