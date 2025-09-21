"""
数据格式转换器
将Hyperliquid原始数据转换为强化学习训练所需的格式
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime, timedelta
import json

from data_loader import prepare_data, validate_data
from utils import add_technical_indicators, create_features, normalize_data

logger = logging.getLogger(__name__)


class DataFormatter:
    """数据格式转换器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.window_size = config.get('env', {}).get('window_size', 50)
        self.feature_columns = self._get_feature_columns()
    
    def _get_feature_columns(self) -> List[str]:
        """获取特征列"""
        return [
            'open', 'high', 'low', 'close', 'volume',
            'ma5', 'ma10', 'ma20', 'ma50',
            'ema12', 'ema26',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_upper', 'bb_middle', 'bb_lower',
            'atr', 'stoch_k', 'stoch_d', 'willr',
            'volume_ma', 'volume_ratio',
            'price_change', 'price_momentum', 'volatility'
        ]
    
    def format_hyperliquid_data(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """格式化Hyperliquid数据"""
        if raw_df.empty:
            return raw_df
        
        # 标准化列名
        column_mapping = {
            't': 'timestamp',
            'o': 'open',
            'h': 'high',
            'l': 'low',
            'c': 'close',
            'v': 'volume',
            's': 'symbol'
        }
        
        df = raw_df.copy()
        
        # 重命名列
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # 确保必要列存在
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"Missing columns: {missing_columns}")
            for col in missing_columns:
                df[col] = 0.0
        
        # 转换数据类型
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 处理时间戳
        if df['timestamp'].dtype == 'int64':
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        elif df['timestamp'].dtype == 'object':
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 按时间排序
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # 填充缺失值
        df = df.fillna(method='ffill').fillna(0)
        
        return df
    
    def add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加派生特征"""
        if df.empty:
            return df
        
        df = df.copy()
        
        # 添加技术指标
        df = add_technical_indicators(df)
        
        # 添加额外特征
        df['price_range'] = df['high'] - df['low']
        df['price_range_pct'] = df['price_range'] / df['close']
        
        # 价格位置特征
        df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        
        # 成交量特征
        df['volume_ma_10'] = df['volume'].rolling(window=10).mean()
        df['volume_ma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio_10'] = df['volume'] / df['volume_ma_10']
        df['volume_ratio_20'] = df['volume'] / df['volume_ma_20']
        
        # 价格动量特征
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # 波动率特征
        df['realized_vol_5'] = df['returns'].rolling(window=5).std()
        df['realized_vol_10'] = df['returns'].rolling(window=10).std()
        df['realized_vol_20'] = df['returns'].rolling(window=20).std()
        
        # 价格趋势特征
        df['trend_up'] = (df['close'] > df['close'].shift(1)).astype(int)
        df['trend_strength'] = df['trend_up'].rolling(window=10).mean()
        
        # 市场微观结构特征
        df['high_low_ratio'] = df['high'] / df['low']
        df['close_open_ratio'] = df['close'] / df['open']
        
        # 处理无穷大和NaN值
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(method='ffill').fillna(0)
        
        return df
    
    def create_state_features(self, df: pd.DataFrame) -> np.ndarray:
        """创建状态特征"""
        if df.empty or len(df) < self.window_size:
            return np.array([])
        
        features = []
        
        for i in range(self.window_size, len(df)):
            window = df.iloc[i-self.window_size:i]
            
            # 基础价格特征
            close_prices = window['close'].values
            volume = window['volume'].values
            
            # 标准化价格
            latest_price = close_prices[-1]
            if latest_price > 0:
                price_features = close_prices / latest_price - 1.0
            else:
                price_features = np.zeros(self.window_size)
            
            # 技术指标特征
            technical_features = []
            
            # 移动平均线特征
            for ma_col in ['ma5', 'ma10', 'ma20', 'ma50']:
                if ma_col in window.columns:
                    ma_val = window[ma_col].iloc[-1]
                    if not pd.isna(ma_val) and latest_price > 0:
                        technical_features.append((ma_val - latest_price) / latest_price)
                    else:
                        technical_features.append(0.0)
            
            # RSI特征
            if 'rsi' in window.columns:
                rsi_val = window['rsi'].iloc[-1]
                if not pd.isna(rsi_val):
                    technical_features.append(rsi_val / 100.0)
                else:
                    technical_features.append(0.5)
            
            # MACD特征
            if 'macd' in window.columns:
                macd_val = window['macd'].iloc[-1]
                if not pd.isna(macd_val) and latest_price > 0:
                    technical_features.append(macd_val / latest_price)
                else:
                    technical_features.append(0.0)
            
            # 波动率特征
            if len(close_prices) > 1:
                returns = np.diff(close_prices) / close_prices[:-1]
                volatility = np.std(returns)
                technical_features.append(volatility)
            else:
                technical_features.append(0.0)
            
            # 成交量特征
            if len(volume) > 0:
                vol_mean = np.mean(volume)
                if vol_mean > 0:
                    technical_features.extend([
                        volume[-1] / vol_mean,
                        np.std(volume) / vol_mean
                    ])
                else:
                    technical_features.extend([1.0, 0.0])
            else:
                technical_features.extend([1.0, 0.0])
            
            # 组合所有特征
            feature_vector = np.concatenate([
                price_features,
                technical_features
            ])
            
            features.append(feature_vector)
        
        return np.array(features)
    
    def create_action_labels(self, df: pd.DataFrame) -> np.ndarray:
        """创建动作标签"""
        if df.empty or len(df) <= self.window_size:
            return np.array([])
        
        # 计算未来收益率
        close_prices = df['close'].values
        future_returns = []
        
        for i in range(self.window_size, len(df)):
            if i + 1 < len(close_prices):
                ret = (close_prices[i+1] - close_prices[i]) / close_prices[i]
            else:
                ret = 0.0
            future_returns.append(ret)
        
        future_returns = np.array(future_returns)
        
        # 创建离散动作标签
        # 0: 空仓, 1: 做多, 2: 做空
        thresholds = [-0.005, 0.005]  # 0.5% 阈值
        
        labels = np.digitize(future_returns, thresholds)
        
        return labels
    
    def normalize_features(self, features: np.ndarray) -> np.ndarray:
        """标准化特征"""
        if features.size == 0:
            return features
        
        # Z-score标准化
        mean = np.mean(features, axis=0)
        std = np.std(features, axis=0)
        
        # 避免除以零
        std = np.where(std == 0, 1, std)
        
        normalized_features = (features - mean) / std
        
        # 限制极端值
        normalized_features = np.clip(normalized_features, -3, 3)
        
        return normalized_features
    
    def prepare_training_dataset(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
        val_size: float = 0.1
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """准备训练数据集"""
        if df.empty or len(df) < self.window_size + 1:
            return (np.array([]), np.array([]), np.array([]), 
                   np.array([]), np.array([]), np.array([]))
        
        # 格式化数据
        formatted_df = self.format_hyperliquid_data(df)
        
        # 添加派生特征
        enriched_df = self.add_derived_features(formatted_df)
        
        # 创建特征和标签
        features = self.create_state_features(enriched_df)
        labels = self.create_action_labels(enriched_df)
        
        if features.size == 0 or labels.size == 0:
            return (np.array([]), np.array([]), np.array([]), 
                   np.array([]), np.array([]), np.array([]))
        
        # 确保特征和标签长度匹配
        min_len = min(len(features), len(labels))
        features = features[:min_len]
        labels = labels[:min_len]
        
        # 标准化特征
        features = self.normalize_features(features)
        
        # 分割数据集
        total_samples = len(features)
        test_samples = int(total_samples * test_size)
        val_samples = int(total_samples * val_size)
        train_samples = total_samples - test_samples - val_samples
        
        if train_samples <= 0:
            logger.warning("Insufficient data for training")
            return (np.array([]), np.array([]), np.array([]), 
                   np.array([]), np.array([]), np.array([]))
        
        # 分割数据
        X_train = features[:train_samples]
        y_train = labels[:train_samples]
        
        X_val = features[train_samples:train_samples + val_samples]
        y_val = labels[train_samples:train_samples + val_samples]
        
        X_test = features[train_samples + val_samples:]
        y_test = labels[train_samples + val_samples:]
        
        logger.info(f"Dataset prepared - Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
        
        return X_train, X_val, X_test, y_train, y_val, y_test
    
    def save_formatted_data(self, df: pd.DataFrame, filepath: str):
        """保存格式化数据"""
        try:
            df.to_csv(filepath, index=False)
            logger.info(f"Formatted data saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving formatted data: {e}")
    
    def load_formatted_data(self, filepath: str) -> pd.DataFrame:
        """加载格式化数据"""
        try:
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            logger.info(f"Formatted data loaded from {filepath}")
            return df
        except Exception as e:
            logger.error(f"Error loading formatted data: {e}")
            return pd.DataFrame()


# 使用示例
def main():
    """主函数示例"""
    logging.basicConfig(level=logging.INFO)
    
    # 加载配置
    import yaml
    with open('configs/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 创建格式化器
    formatter = DataFormatter(config)
    
    # 加载示例数据
    from data_loader import load_csv
    df = load_csv('data/sample_data.csv')
    
    if not df.empty:
        # 格式化数据
        formatted_df = formatter.format_hyperliquid_data(df)
        
        # 添加派生特征
        enriched_df = formatter.add_derived_features(formatted_df)
        
        # 准备训练数据
        X_train, X_val, X_test, y_train, y_val, y_test = formatter.prepare_training_dataset(
            enriched_df, test_size=0.2, val_size=0.1
        )
        
        print(f"Training data shape: X={X_train.shape}, y={y_train.shape}")
        print(f"Validation data shape: X={X_val.shape}, y={y_val.shape}")
        print(f"Test data shape: X={X_test.shape}, y={y_test.shape}")


if __name__ == "__main__":
    main()