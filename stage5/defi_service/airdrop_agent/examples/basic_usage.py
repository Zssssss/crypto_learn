#!/usr/bin/env python3
"""
空投狩猎基础使用示例
"""
import asyncio
import json
from airdrop_finder import AirdropFinder
from wallet_manager import wallet_manager
from interaction_executor import interaction_executor
from utils.logger import logger

async def basic_airdrop_discovery():
    """基础空投发现示例"""
    print("🎯 基础空投发现示例")
    
    async with AirdropFinder() as finder:
        # 发现所有空投
        airdrops = await finder.find_all_airdrops()
        
        # 过滤高价值空投
        high_value_airdrops = finder.filter_airdrops(
            airdrops, 
            min_value=100, 
            networks=["ethereum", "arbitrum"]
        )
        
        print(f"发现 {len(high_value_airdrops)} 个高价值空投:")
        for airdrop in high_value_airdrops[:5]:
            print(f"  💰 {airdrop.name} - ${airdrop.estimated_value}")
            print(f"     网络: {airdrop.network}")
            print(f"     难度: {airdrop.difficulty}")
            print(f"     要求: {', '.join(airdrop.requirements)}")
            print()

def wallet_management_example():
    """钱包管理示例"""
    print("💰 钱包管理示例")
    
    # 获取钱包摘要
    summary = wallet_manager.get_wallet_summary()
    
    for address, info in summary.items():
        print(f"钱包: {address[:10]}...")
        print(f"  总价值: ${info['total_value_usd']:.2f}")
        
        for network, details in info['networks'].items():
            print(f"  {network}: {details['native_balance']:.4f} ETH (${details['native_value_usd']:.2f})")
    
    # 保存钱包信息
    wallet_manager.save_wallets_to_file("example_wallets.json")
    print("✅ 钱包信息已保存")

async def single_airdrop_execution():
    """单个空投执行示例"""
    print("🤖 单个空投执行示例")
    
    # 模拟一个空投
    from airdrop_finder import Airdrop
    from datetime import datetime
    
    mock_airdrop = Airdrop(
        name="zkSync Test Airdrop",
        project="zkSync",
        network="arbitrum",
        description="测试zkSync网络交互",
        estimated_value=50,
        difficulty="easy",
        requirements=["桥接资产", "简单交互"],
        deadline=None,
        url="https://bridge.zksync.io"
    )
    
    # 获取钱包地址
    wallets = wallet_manager.get_all_wallets()
    if not wallets:
        print("❌ 未配置钱包")
        return
    
    wallet_address = wallets[0]
    print(f"使用钱包: {wallet_address[:10]}...")
    
    # 估算gas费用
    gas_cost = interaction_executor.estimate_task_gas('bridge', 'arbitrum')
    print(f"估算gas费用: ${gas_cost:.2f}")
    
    # 检查余额
    balance = wallet_manager.get_wallet_balance(wallet_address, 'arbitrum')
    print(f"钱包余额: {balance:.4f} ETH")
    
    if balance > 0.01:
        print("✅ 余额充足，可以执行任务")
        
        # 模拟执行任务
        result = interaction_executor.execute_airdrop_task(mock_airdrop, wallet_address)
        print(f"执行结果: {result}")
    else:
        print("⚠️ 余额不足")

async def main():
    """主示例函数"""
    print("🪂 Airdrop Hunter Agent - 使用示例")
    print("=" * 50)
    
    try:
        # 示例1: 基础空投发现
        await basic_airdrop_discovery()
        
        print("\n" + "=" * 50 + "\n")
        
        # 示例2: 钱包管理
        wallet_management_example()
        
        print("\n" + "=" * 50 + "\n")
        
        # 示例3: 单个空投执行
        await single_airdrop_execution()
        
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        print("请确保已正确配置 .env 文件")

if __name__ == "__main__":
    asyncio.run(main())