"""钱包管理模块"""
import json
import time
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from eth_account import Account
from web3 import Web3
from web3.middleware import geth_poa_middleware
from config import config
from utils.logger import logger

class WalletManager:
    """钱包管理器"""
    
    def __init__(self):
        self.wallets: Dict[str, Dict] = {}
        self.web3_instances: Dict[str, Web3] = {}
        self._initialize_web3()
        self._load_wallets()
    
    def _initialize_web3(self):
        """初始化Web3连接"""
        for network_name, network_config in config.networks.items():
            try:
                w3 = Web3(Web3.HTTPProvider(network_config.rpc_url))
                if network_name in ["bsc", "polygon", "arbitrum", "optimism"]:
                    w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                if w3.is_connected():
                    self.web3_instances[network_name] = w3
                    logger.info(f"✅ 已连接到 {network_name} 网络")
                else:
                    logger.warning(f"❌ 无法连接到 {network_name} 网络")
            except Exception as e:
                logger.error(f"连接 {network_name} 网络时出错: {e}")
    
    def _load_wallets(self):
        """加载钱包"""
        for private_key in config.wallets.private_keys:
            try:
                account = Account.from_key(private_key)
                address = account.address
                
                self.wallets[address] = {
                    'private_key': private_key,
                    'account': account,
                    'balances': {}
                }
                
                # 更新余额
                self._update_wallet_balances(address)
                
                logger.info(f"✅ 已加载钱包: {address}")
            except Exception as e:
                logger.error(f"加载钱包时出错: {e}")
    
    def _update_wallet_balances(self, address: str):
        """更新钱包余额"""
        wallet = self.wallets[address]
        wallet['balances'] = {}
        
        for network_name, w3 in self.web3_instances.items():
            try:
                balance_wei = w3.eth.get_balance(address)
                balance_eth = w3.from_wei(balance_wei, 'ether')
                
                wallet['balances'][network_name] = {
                    'native': float(balance_eth),
                    'tokens': {}
                }
                
                logger.debug(f"{address} 在 {network_name} 的余额: {balance_eth} ETH")
            except Exception as e:
                logger.error(f"获取 {address} 在 {network_name} 的余额时出错: {e}")
    
    def get_all_wallets(self) -> List[str]:
        """获取所有钱包地址"""
        return list(self.wallets.keys())
    
    def get_wallet_balance(self, address: str, network: str, token_address: Optional[str] = None) -> float:
        """获取钱包余额
        
        Args:
            address: 钱包地址
            network: 网络名称
            token_address: 代币合约地址，None表示原生代币
            
        Returns:
            余额数量
        """
        if address not in self.wallets:
            raise ValueError(f"钱包 {address} 不存在")
        
        if network not in self.web3_instances:
            raise ValueError(f"网络 {network} 不存在")
        
        w3 = self.web3_instances[network]
        
        try:
            if token_address is None:
                # 原生代币
                balance_wei = w3.eth.get_balance(address)
                return float(w3.from_wei(balance_wei, 'ether'))
            else:
                # ERC20代币
                token_contract = w3.eth.contract(
                    address=Web3.to_checksum_address(token_address),
                    abi=self._get_erc20_abi()
                )
                balance = token_contract.functions.balanceOf(address).call()
                decimals = token_contract.functions.decimals().call()
                return balance / (10 ** decimals)
        except Exception as e:
            logger.error(f"获取余额时出错: {e}")
            return 0.0
    
    def send_transaction(self, network: str, from_address: str, to_address: str, 
                        amount: float, gas_price: Optional[int] = None) -> str:
        """发送交易
        
        Args:
            network: 网络名称
            from_address: 发送地址
            to_address: 接收地址
            amount: 发送数量(ETH)
            gas_price: gas价格(gwei)
            
        Returns:
            交易哈希
        """
        if from_address not in self.wallets:
            raise ValueError(f"钱包 {from_address} 不存在")
        
        if network not in self.web3_instances:
            raise ValueError(f"网络 {network} 不存在")
        
        w3 = self.web3_instances[network]
        wallet = self.wallets[from_address]
        private_key = wallet['private_key']
        
        try:
            # 获取nonce
            nonce = w3.eth.get_transaction_count(from_address)
            
            # 获取gas价格
            if gas_price is None:
                gas_price = w3.eth.gas_price
            else:
                gas_price = w3.to_wei(gas_price, 'gwei')
            
            # 构建交易
            transaction = {
                'nonce': nonce,
                'to': to_address,
                'value': w3.to_wei(amount, 'ether'),
                'gas': 21000,  # 标准转账
                'gasPrice': gas_price,
                'chainId': config.networks[network].chain_id
            }
            
            # 签名交易
            signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
            
            # 发送交易
            tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            
            logger.info(f"📤 已发送交易: {tx_hash.hex()}")
            return tx_hash.hex()
            
        except Exception as e:
            logger.error(f"发送交易时出错: {e}")
            raise
    
    def estimate_gas_cost(self, network: str, from_address: str, to_address: str, 
                         amount: float) -> Dict[str, float]:
        """估算gas费用
        
        Args:
            network: 网络名称
            from_address: 发送地址
            to_address: 接收地址
            amount: 发送数量
            
        Returns:
            包含gas费用信息的字典
        """
        if network not in self.web3_instances:
            raise ValueError(f"网络 {network} 不存在")
        
        w3 = self.web3_instances[network]
        
        try:
            # 估算gas限制
            transaction = {
                'from': from_address,
                'to': to_address,
                'value': w3.to_wei(amount, 'ether')
            }
            
            gas_limit = w3.eth.estimate_gas(transaction)
            gas_price = w3.eth.gas_price
            
            gas_cost_eth = float(w3.from_wei(gas_limit * gas_price, 'ether'))
            gas_cost_usd = gas_cost_eth * self._get_eth_price()
            
            return {
                'gas_limit': gas_limit,
                'gas_price_gwei': float(w3.from_wei(gas_price, 'gwei')),
                'gas_cost_eth': gas_cost_eth,
                'gas_cost_usd': gas_cost_usd
            }
            
        except Exception as e:
            logger.error(f"估算gas费用时出错: {e}")
            return {}
    
    def _get_eth_price(self) -> float:
        """获取ETH价格(简化版，实际应该从价格API获取)"""
        return 3000.0  # 假设ETH价格为3000美元
    
    def _get_erc20_abi(self) -> List[Dict]:
        """获取ERC20标准ABI"""
        return [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]
    
    def get_wallet_summary(self) -> Dict[str, Dict]:
        """获取钱包摘要"""
        summary = {}
        
        for address, wallet in self.wallets.items():
            total_value_usd = 0
            networks = {}
            
            for network_name, balances in wallet['balances'].items():
                network_value = 0
                
                # 计算原生代币价值
                native_balance = balances.get('native', 0)
                if network_name == "ethereum":
                    native_value = native_balance * self._get_eth_price()
                else:
                    # 简化的价值计算
                    native_value = native_balance * 3000
                
                network_value += native_value
                
                networks[network_name] = {
                    'native_balance': native_balance,
                    'native_value_usd': native_value
                }
                
                total_value_usd += network_value
            
            summary[address] = {
                'total_value_usd': total_value_usd,
                'networks': networks
            }
        
        return summary
    
    def save_wallets_to_file(self, filename: str = "wallets_backup.json"):
        """保存钱包信息到文件(不包含私钥)"""
        wallet_data = {}
        
        for address, wallet in self.wallets.items():
            wallet_data[address] = {
                'balances': wallet['balances'],
                'created_at': int(time.time())
            }
        
        with open(filename, 'w') as f:
            json.dump(wallet_data, f, indent=2)
        
        logger.info(f"💾 钱包信息已保存到 {filename}")

# 全局钱包管理器实例
wallet_manager = WalletManager()