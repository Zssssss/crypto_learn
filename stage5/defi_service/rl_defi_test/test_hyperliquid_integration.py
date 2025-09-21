#!/usr/bin/env python3
"""
Hyperliquid集成测试
测试从数据获取到格式化的完整流程
"""
import asyncio
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import logging
import yaml

# 设置测试环境
logging.basicConfig(level=logging.INFO)

from hyperliquid_data_provider import HyperliquidDataProvider, HyperliquidConfig
from data_formatter import DataFormatter
from data_validator import DataQualityValidator, DataHealthMonitor
from realtime_processor import RealtimeDataProcessor


class TestHyperliquidIntegration:
    """集成测试类"""
    
    def setup_method(self):
        """测试设置"""
        self.config = {
            'realtime': {'symbol': 'BTC-USD'},
            'data': {'interval': '1'},
            'env': {'window_size': 10}
        }
        
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """测试清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_data_provider_connection(self):
        """测试数据提供器连接"""
        config = HyperliquidConfig(symbol="BTC-USD")
        provider = HyperliquidDataProvider(config)
        
        try:
            # 测试获取市场信息
            market_info = await provider.get_market_info()
            assert isinstance(market_info, dict)
            assert 'symbol' in market_info
            assert market_info['symbol'] == "BTC-USD"
            
            # 测试获取历史数据
            df = await provider.get_historical_data(limit=10)
            assert isinstance(df, pd.DataFrame)
            assert not df.empty
            
            # 检查数据结构
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            assert all(col in df.columns for col in required_columns)
            
        finally:
            await provider.close()
    
    async def test_data_formatter(self):
        """测试数据格式化"""
        # 创建测试数据
        test_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
            'open': np.random.uniform(40000, 41000, 100),
            'high': np.random.uniform(41000, 42000, 100),
            'low': np.random.uniform(39000, 40000, 100),
            'close': np.random.uniform(40000, 41000, 100),
            'volume': np.random.uniform(1000, 10000, 100)
        })
        
        # 确保价格关系正确
        test_data['high'] = test_data[['high', 'open', 'close', 'low']].max(axis=1)
        test_data['low'] = test_data[['low', 'open', 'close', 'high']].min(axis=1)
        
        formatter = DataFormatter(self.config)
        
        # 测试数据格式化
        formatted_df = formatter.format_hyperliquid_data(test_data)
        assert not formatted_df.empty
        
        # 测试特征创建
        features = formatter.create_state_features(formatted_df)
        assert features.size > 0
        
        # 测试标签创建
        labels = formatter.create_action_labels(formatted_df)
        assert labels.size > 0
        
        # 测试训练数据准备
        X_train, X_val, X_test, y_train, y_val, y_test = formatter.prepare_training_dataset(
            formatted_df, test_size=0.2, val_size=0.1
        )
        
        assert X_train.shape[0] > 0
        assert X_val.shape[0] > 0
        assert X_test.shape[0] > 0
        
        # 检查标签范围
        assert all(0 <= label <= 2 for label in y_train)
        assert all(0 <= label <= 2 for label in y_val)
        assert all(0 <= label <= 2 for label in y_test)
    
    async def test_data_validator(self):
        """测试数据验证器"""
        validator = DataQualityValidator(self.config)
        
        # 测试有效数据
        valid_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1min'),
            'open': [100.0] * 10,
            'high': [101.0] * 10,
            'low': [99.0] * 10,
            'close': [100.5] * 10,
            'volume': [1000.0] * 10
        })
        
        result = validator.validate_dataframe(valid_data)
        assert result['valid']
        
        # 测试无效数据
        invalid_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1min'),
            'open': [100.0] * 10,
            'high': [99.0] * 10,  # high < low
            'low': [100.0] * 10,
            'close': [100.5] * 10,
            'volume': [-100.0] * 10  # negative volume
        })
        
        result = validator.validate_dataframe(invalid_data)
        assert not result['valid']
        
        # 测试数据清理
        cleaned_data = validator.clean_data(invalid_data)
        assert cleaned_data['high'].iloc[0] >= cleaned_data['low'].iloc[0]
        assert all(cleaned_data['volume'] >= 0)
    
    async def test_realtime_processor(self):
        """测试实时处理器"""
        processor = RealtimeDataProcessor(self.config, buffer_size=20)
        
        # 测试启动和停止
        await processor.start()
        assert processor.is_running
        
        await asyncio.sleep(1)  # 给处理器一些时间
        
        await processor.stop()
        assert not processor.is_running
    
    async def test_end_to_end_flow(self):
        """测试端到端流程"""
        # 创建数据提供器
        config = HyperliquidConfig(symbol="BTC-USD")
        provider = HyperliquidDataProvider(config)
        
        try:
            # 获取实际数据
            raw_df = await provider.get_historical_data(limit=100)
            assert not raw_df.empty
            
            # 验证数据
            validator = DataQualityValidator(self.config)
            result = validator.validate_dataframe(raw_df)
            
            if result['valid']:
                # 清理数据
                cleaned_df = validator.clean_data(raw_df)
                
                # 格式化数据
                formatter = DataFormatter(self.config)
                X_train, X_val, X_test, y_train, y_val, y_test = formatter.prepare_training_dataset(
                    cleaned_df, test_size=0.2, val_size=0.1
                )
                
                assert X_train.shape[0] > 0
                
                # 保存测试数据
                np.savez(
                    f"{self.temp_dir}/test_data.npz",
                    X_train=X_train, X_val=X_val, X_test=X_test,
                    y_train=y_train, y_val=y_val, y_test=y_test
                )
                
                logger.info("End-to-end test completed successfully")
                
        finally:
            await provider.close()


async def run_integration_tests():
    """运行集成测试"""
    test_instance = TestHyperliquidIntegration()
    
    tests = [
        test_instance.test_data_provider_connection,
        test_instance.test_data_formatter,
        test_instance.test_data_validator,
        test_instance.test_realtime_processor,
        test_instance.test_end_to_end_flow
    ]
    
    results = []
    for test in tests:
        try:
            await test()
            results.append(f"✓ {test.__name__}")
        except Exception as e:
            results.append(f"✗ {test.__name__}: {e}")
    
    print("\nTest Results:")
    for result in results:
        print(result)
    
    return all("✓" in r for r in results)


if __name__ == "__main__":
    success = asyncio.run(run_integration_tests())
    if success:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed!")
        exit(1)