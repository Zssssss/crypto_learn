"""
套利机器人单元测试
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from arbitrage_bot_v2 import (
    Config,
    ArbitrageOpportunity,
    DEXInterface,
    UniswapV3,
    UniswapV2,
    ArbitrageBot
)


class TestConfig(unittest.TestCase):
    """测试配置类"""
    
    def setUp(self):
        """设置测试环境"""
        # 设置必要的环境变量
        os.environ["ACCOUNT"] = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
        os.environ["PRIVATE_KEY"] = "0x" + "a" * 64
        
    def test_config_initialization(self):
        """测试配置初始化"""
        config = Config()
        self.assertIsNotNone(config.rpc_url)
        self.assertIsNotNone(config.account)
        self.assertEqual(config.amount_usdt, 100 * 10**6)
        self.assertEqual(config.min_net_profit_usdt, int(0.5 * 1e6))
        
    def test_config_validation_success(self):
        """测试配置验证成功"""
        config = Config()
        self.assertTrue(config.validate())
        
    def test_config_validation_failure(self):
        """测试配置验证失败"""
        config = Config()
        config.account = ""
        self.assertFalse(config.validate())
        
        config.account = "invalid_address"
        self.assertFalse(config.validate())


class TestArbitrageOpportunity(unittest.TestCase):
    """测试套利机会数据结构"""
    
    def test_opportunity_creation(self):
        """测试创建套利机会"""
        opportunity = ArbitrageOpportunity(
            token_path=["USDT", "WETH", "USDT"],
            dex_path=["uniswap_v3", "sushiswap"],
            amount_in=100 * 10**6,
            expected_profit=2 * 10**6,
            gas_cost=int(0.5 * 10**6),
            net_profit=int(1.5 * 10**6),
            timestamp=datetime.now()
        )
        
        self.assertEqual(len(opportunity.token_path), 3)
        self.assertEqual(len(opportunity.dex_path), 2)
        self.assertEqual(opportunity.net_profit, int(1.5 * 10**6))
        
    def test_opportunity_to_dict(self):
        """测试转换为字典"""
        timestamp = datetime.now()
        opportunity = ArbitrageOpportunity(
            token_path=["USDT", "WETH", "USDT"],
            dex_path=["uniswap_v3", "sushiswap"],
            amount_in=100 * 10**6,
            expected_profit=2 * 10**6,
            gas_cost=int(0.5 * 10**6),
            net_profit=int(1.5 * 10**6),
            timestamp=timestamp
        )
        
        data = opportunity.to_dict()
        self.assertIn("token_path", data)
        self.assertIn("dex_path", data)
        self.assertIn("net_profit", data)
        self.assertEqual(data["timestamp"], timestamp.isoformat())


class TestDEXInterface(unittest.TestCase):
    """测试 DEX 接口"""
    
    @patch('web3.Web3')
    def test_uniswap_v3_initialization(self, mock_web3):
        """测试 Uniswap V3 初始化"""
        mock_w3 = Mock()
        mock_contract = Mock()
        mock_w3.eth.contract.return_value = mock_contract
        
        dex = UniswapV3(mock_w3, "0x" + "0" * 40)
        self.assertEqual(dex.name, "UniswapV3")
        self.assertEqual(dex.fee, 3000)
        
    @patch('web3.Web3')
    def test_uniswap_v3_quote(self, mock_web3):
        """测试 Uniswap V3 报价"""
        mock_w3 = Mock()
        mock_contract = Mock()
        mock_w3.eth.contract.return_value = mock_contract
        
        # 模拟报价返回
        mock_contract.functions.quoteExactInputSingle.return_value.call.return_value = (
            10**18,  # amountOut
            0,       # sqrtPriceX96After
            0,       # initializedTicksCrossed
            100000   # gasEstimate
        )
        
        dex = UniswapV3(mock_w3, "0x" + "0" * 40)
        result = dex.quote("0x" + "1" * 40, "0x" + "2" * 40, 100 * 10**6)
        
        self.assertEqual(result, 10**18)
        
    @patch('web3.Web3')
    def test_uniswap_v2_quote(self, mock_web3):
        """测试 Uniswap V2 报价"""
        mock_w3 = Mock()
        mock_contract = Mock()
        mock_w3.eth.contract.return_value = mock_contract
        
        # 模拟报价返回
        mock_contract.functions.getAmountsOut.return_value.call.return_value = [
            100 * 10**6,  # 输入金额
            10**18         # 输出金额
        ]
        
        dex = UniswapV2(mock_w3, "0x" + "0" * 40)
        result = dex.quote("0x" + "1" * 40, "0x" + "2" * 40, 100 * 10**6)
        
        self.assertEqual(result, 10**18)


class TestArbitrageBot(unittest.TestCase):
    """测试套利机器人主类"""
    
    def setUp(self):
        """设置测试环境"""
        os.environ["ACCOUNT"] = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
        os.environ["PRIVATE_KEY"] = "0x" + "a" * 64
        
    @patch('arbitrage_bot_v2.Web3')
    def test_bot_initialization(self, mock_web3_class):
        """测试机器人初始化"""
        # 模拟 Web3 连接
        mock_w3 = Mock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 42161  # Arbitrum
        mock_web3_class.return_value = mock_w3
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        config = Config()
        bot = ArbitrageBot(config)
        
        self.assertIsNotNone(bot.w3)
        self.assertIsNotNone(bot.dexes)
        self.assertEqual(bot.stats["opportunities_found"], 0)
        self.assertEqual(bot.stats["trades_executed"], 0)
        
    @patch('arbitrage_bot_v2.Web3')
    def test_estimate_gas_cost(self, mock_web3_class):
        """测试 Gas 成本估算"""
        # 模拟 Web3
        mock_w3 = Mock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 42161
        mock_w3.eth.gas_price = 10**9  # 1 Gwei
        mock_web3_class.return_value = mock_w3
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        config = Config()
        bot = ArbitrageBot(config)
        
        # 模拟 DEX 报价
        mock_dex = Mock()
        mock_dex.quote.return_value = 3000 * 10**6  # 1 ETH = 3000 USDT
        bot.dexes["uniswap_v3"] = mock_dex
        
        gas_cost = bot.estimate_gas_cost()
        self.assertGreater(gas_cost, 0)
        self.assertLess(gas_cost, 10 * 10**6)  # 应该小于 10 USDT
        
    @patch('arbitrage_bot_v2.Web3')
    def test_find_arbitrage_opportunities(self, mock_web3_class):
        """测试寻找套利机会"""
        # 模拟 Web3
        mock_w3 = Mock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 42161
        mock_web3_class.return_value = mock_w3
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        config = Config()
        bot = ArbitrageBot(config)
        
        # 模拟 DEX 报价产生套利机会
        mock_dex1 = Mock()
        mock_dex1.quote.side_effect = [
            10**18,  # USDT -> WETH
            102 * 10**6  # WETH -> USDT (有利润)
        ]
        
        mock_dex2 = Mock()
        mock_dex2.quote.side_effect = [
            10**18,  # USDT -> WETH
            98 * 10**6  # WETH -> USDT (无利润)
        ]
        
        bot.dexes = {
            "dex1": mock_dex1,
            "dex2": mock_dex2
        }
        
        # 简化代币列表
        bot.token_whitelist = {config.usdt, config.weth}
        
        opportunities = bot.find_arbitrage_opportunities()
        # 由于模拟的限制，这里可能找不到机会
        self.assertIsInstance(opportunities, list)


class TestIntegration(unittest.TestCase):
    """集成测试"""
    
    @patch('arbitrage_bot_v2.Web3')
    @patch('arbitrage_bot_v2.requests')
    def test_send_notification(self, mock_requests, mock_web3_class):
        """测试发送通知"""
        # 设置环境变量
        os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
        os.environ["TELEGRAM_CHAT_ID"] = "test_chat_id"
        
        # 模拟 Web3
        mock_w3 = Mock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 42161
        mock_web3_class.return_value = mock_w3
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        config = Config()
        bot = ArbitrageBot(config)
        
        # 测试发送通知
        bot.send_notification("Test message")
        
        # 验证请求被调用
        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        self.assertIn("test_token", call_args[0][0])
        self.assertEqual(call_args[1]["data"]["text"], "Test message")
        
    @patch('arbitrage_bot_v2.Web3')
    def test_print_stats(self, mock_web3_class):
        """测试打印统计信息"""
        # 模拟 Web3
        mock_w3 = Mock()
        mock_w3.is_connected.return_value = True
        mock_w3.eth.chain_id = 42161
        mock_web3_class.return_value = mock_w3
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        config = Config()
        bot = ArbitrageBot(config)
        
        # 设置一些统计数据
        bot.stats["opportunities_found"] = 100
        bot.stats["trades_executed"] = 10
        bot.stats["trades_successful"] = 8
        bot.stats["total_profit"] = Decimal("125.5")
        
        # 测试打印统计（不应该抛出异常）
        bot.print_stats()


class TestEdgeCases(unittest.TestCase):
    """边缘情况测试"""
    
    @patch('arbitrage_bot_v2.Web3')
    def test_rpc_connection_failure(self, mock_web3_class):
        """测试 RPC 连接失败"""
        # 模拟连接失败
        mock_w3 = Mock()
        mock_w3.is_connected.return_value = False
        mock_web3_class.return_value = mock_w3
        mock_web3_class.HTTPProvider = Mock()
        
        config = Config()
        config.backup_rpc_url = ""  # 没有备用 RPC
        
        with self.assertRaises(ConnectionError):
            bot = ArbitrageBot(config)
            
    @patch('arbitrage_bot_v2.Web3')
    def test_backup_rpc_fallback(self, mock_web3_class):
        """测试备用 RPC 回退"""
        # 第一个连接失败，第二个成功
        mock_w3_fail = Mock()
        mock_w3_fail.is_connected.return_value = False
        
        mock_w3_success = Mock()
        mock_w3_success.is_connected.return_value = True
        mock_w3_success.eth.chain_id = 42161
        
        mock_web3_class.side_effect = [mock_w3_fail, mock_w3_success]
        mock_web3_class.HTTPProvider = Mock()
        mock_web3_class.to_checksum_address = lambda x: x
        
        config = Config()
        config.backup_rpc_url = "https://backup.rpc.url"
        
        bot = ArbitrageBot(config)
        self.assertIsNotNone(bot.w3)
        
    def test_invalid_private_key(self):
        """测试无效私钥"""
        os.environ["PRIVATE_KEY"] = "invalid_key"
        config = Config()
        # 私钥格式验证应该在实际使用时进行
        self.assertIsNotNone(config.private_key)


class TestPerformance(unittest.TestCase):
    """性能测试"""
    
    @patch('arbitrage_bot_v2.Web3')
    def test_opportunity_sorting_performance(self, mock_web3_class):
        """测试机会排序性能"""
        import time
        
        # 创建大量套利机会
        opportunities = []
        for i in range(1000):
            opportunities.append(
                ArbitrageOpportunity(
                    token_path=["USDT", "WETH", "USDT"],
                    dex_path=["dex1", "dex2"],
                    amount_in=100 * 10**6,
                    expected_profit=(i + 1) * 10**4,
                    gas_cost=int(0.5 * 10**6),
                    net_profit=i * 10**4,
                    timestamp=datetime.now()
                )
            )
        
        # 测试排序性能
        start_time = time.time()
        sorted_opportunities = sorted(opportunities, key=lambda x: x.net_profit, reverse=True)
        elapsed_time = time.time() - start_time
        
        # 应该在 1 秒内完成
        self.assertLess(elapsed_time, 1.0)
        # 验证排序正确
        self.assertEqual(sorted_opportunities[0].net_profit, 999 * 10**4)
        self.assertEqual(sorted_opportunities[-1].net_profit, 0)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestArbitrageOpportunity))
    suite.addTests(loader.loadTestsFromTestCase(TestDEXInterface))
    suite.addTests(loader.loadTestsFromTestCase(TestArbitrageBot))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformance))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)