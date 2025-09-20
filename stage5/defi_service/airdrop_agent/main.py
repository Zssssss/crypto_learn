#!/usr/bin/env python3
"""空投狩猎主程序"""
import asyncio
import signal
import sys
import time
from datetime import datetime
from typing import Dict, List
import schedule
from config import config
from utils.logger import logger, print_banner
from airdrop_finder import AirdropFinder
from interaction_executor import interaction_executor
from wallet_manager import wallet_manager

class AirdropHunter:
    """空投狩猎主控制器"""
    
    def __init__(self):
        self.running = False
        self.airdrop_finder = None
        self.current_airdrops: List = []
        self.task_results: Dict[str, List[Dict]] = {}
        
    def signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info("🛑 收到停止信号，正在优雅关闭...")
        self.running = False
        
    async def start(self):
        """启动空投狩猎"""
        self.running = True
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 打印启动横幅
        print_banner()
        
        # 检查钱包配置
        if not config.wallets.private_keys:
            logger.error("❌ 未配置钱包私钥，请在 .env 文件中设置 PRIVATE_KEYS")
            return
        
        # 显示钱包信息
        wallet_summary = wallet_manager.get_wallet_summary()
        logger.info("💰 钱包信息:")
        for address, info in wallet_summary.items():
            logger.info(f"   {address[:10]}...: ${info['total_value_usd']:.2f}")
        
        # 设置定时任务
        schedule.every(config.airdrop.check_interval).seconds.do(
            lambda: asyncio.create_task(self._check_airdrops())
        )
        
        # 立即执行一次检查
        await self._check_airdrops()
        
        # 主循环
        logger.info("🚀 空投狩猎已启动，按 Ctrl+C 停止...")
        
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(1)
        
        # 清理资源
        await self._cleanup()
        
    async def _check_airdrops(self):
        """检查空投"""
        try:
            logger.info("🔍 开始检查新的空投机会...")
            
            async with AirdropFinder() as finder:
                # 发现空投
                all_airdrops = await finder.find_all_airdrops()
                
                # 过滤空投
                filtered_airdrops = finder.filter_airdrops(
                    all_airdrops,
                    min_value=config.airdrop.min_profit_threshold,
                    networks=["ethereum", "bsc", "polygon", "arbitrum", "optimism"]
                )
                
                if filtered_airdrops:
                    logger.info(f"🎯 发现 {len(filtered_airdrops)} 个符合条件的空投")
                    
                    # 保存空投信息
                    finder.save_airdrops()
                    
                    # 执行空投任务
                    if config.airdrop.auto_execute:
                        await self._execute_airdrops(filtered_airdrops)
                    else:
                        logger.info("📝 自动执行已禁用，请手动查看空投列表")
                        
                else:
                    logger.info("😴 未发现符合条件的空投")
                    
        except Exception as e:
            logger.error(f"检查空投时出错: {e}")
    
    async def _execute_airdrops(self, airdrops: List):
        """执行空投任务"""
        logger.info(f"🤖 开始执行 {len(airdrops)} 个空投任务...")
        
        for airdrop in airdrops:
            if not self.running:
                break
                
            for wallet_address in wallet_manager.get_all_wallets():
                if not self.running:
                    break
                    
                try:
                    # 检查是否已执行过
                    task_key = f"{airdrop.project}_{airdrop.name}"
                    if wallet_address in interaction_executor.completed_tasks and \
                       task_key in interaction_executor.completed_tasks[wallet_address]:
                        logger.info(f"⏭️ 跳过已执行的任务: {airdrop.name}")
                        continue
                    
                    # 估算gas费用
                    estimated_gas = interaction_executor.estimate_task_gas(
                        self._get_task_type(airdrop),
                        airdrop.network.lower()
                    )
                    
                    # 检查钱包余额
                    balance = wallet_manager.get_wallet_balance(
                        wallet_address,
                        airdrop.network.lower()
                    )
                    
                    if balance < 0.01:  # 最小余额要求
                        logger.warning(f"⚠️ 钱包 {wallet_address[:10]}... 余额不足: {balance} ETH")
                        continue
                    
                    if estimated_gas > 50:  # 最大gas费用限制
                        logger.warning(f"⚠️ Gas费用过高: ${estimated_gas:.2f}")
                        continue
                    
                    # 执行空投任务
                    logger.info(f"🎯 开始执行 {airdrop.name} 任务...")
                    
                    result = interaction_executor.execute_airdrop_task(airdrop, wallet_address)
                    
                    # 保存结果
                    if wallet_address not in self.task_results:
                        self.task_results[wallet_address] = []
                    
                    self.task_results[wallet_address].append({
                        'airdrop': airdrop.name,
                        'project': airdrop.project,
                        'network': airdrop.network,
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # 等待一段时间避免过于频繁
                    await asyncio.sleep(random.uniform(30, 60))
                    
                except Exception as e:
                    logger.error(f"执行空投任务时出错: {e}")
        
        # 保存任务结果
        self._save_results()
        
    def _get_task_type(self, airdrop) -> str:
        """获取任务类型"""
        description = str(airdrop.description).lower()
        tags = [str(tag).lower() for tag in airdrop.tags] if airdrop.tags else []
        
        if any(word in description for word in ['桥接', 'bridge', '跨链']):
            return 'bridge'
        elif any(word in description for word in ['交易', 'swap', '兑换']):
            return 'swap'
        elif any(word in description for word in ['流动性', 'liquidity', 'lp']):
            return 'liquidity'
        elif any(word in description for word in ['铸造', 'mint', 'nft']):
            return 'mint'
        else:
            return 'generic'
    
    def _save_results(self):
        """保存执行结果"""
        try:
            with open('task_results.json', 'w', encoding='utf-8') as f:
                json.dump(self.task_results, f, indent=2, ensure_ascii=False)
            
            logger.info("💾 任务结果已保存到 task_results.json")
            
        except Exception as e:
            logger.error(f"保存结果时出错: {e}")
    
    async def _cleanup(self):
        """清理资源"""
        try:
            # 保存钱包信息
            wallet_manager.save_wallets_to_file()
            
            # 保存任务历史
            interaction_executor.save_task_history()
            
            # 关闭浏览器
            interaction_executor.close()
            
            logger.info("✅ 资源清理完成")
            
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")
    
    def print_status(self):
        """打印当前状态"""
        logger.info("📊 当前状态:")
        logger.info(f"   运行状态: {'运行中' if self.running else '已停止'}")
        logger.info(f"   发现空投: {len(self.current_airdrops)}")
        logger.info(f"   已加载钱包: {len(wallet_manager.get_all_wallets())}")
        
        if self.task_results:
            total_tasks = sum(len(results) for results in self.task_results.values())
            logger.info(f"   已完成任务: {total_tasks}")

# 命令行接口
def print_help():
    """打印帮助信息"""
    help_text = """
🪂 Airdrop Hunter Agent - 使用说明
    
使用方法:
    python main.py [命令]
    
命令:
    start       启动空投狩猎
    status      查看当前状态
    wallets     显示钱包信息
    history     显示任务历史
    help        显示此帮助信息
    
示例:
    python main.py start
    python main.py status
    """
    print(help_text)

async def main():
    """主函数"""
    hunter = AirdropHunter()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'start':
            await hunter.start()
        elif command == 'status':
            hunter.print_status()
        elif command == 'wallets':
            summary = wallet_manager.get_wallet_summary()
            for address, info in summary.items():
                print(f"{address}: ${info['total_value_usd']:.2f}")
        elif command == 'history':
            history = interaction_executor.get_task_history()
            for wallet, tasks in history.items():
                print(f"\n{wallet}:")
                for task in tasks:
                    print(f"  - {task}")
        elif command == 'help':
            print_help()
        else:
            print(f"未知命令: {command}")
            print_help()
    else:
        await hunter.start()

if __name__ == "__main__":
    asyncio.run(main())