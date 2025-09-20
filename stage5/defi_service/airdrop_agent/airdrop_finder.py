"""空投发现模块"""
import asyncio
import aiohttp
import json
import time
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from config import config
from utils.logger import logger

@dataclass
class Airdrop:
    """空投信息数据类"""
    name: str
    project: str
    network: str
    description: str
    estimated_value: float
    difficulty: str  # easy, medium, hard
    requirements: List[str]
    deadline: Optional[datetime]
    url: str
    status: str = "active"  # active, ended, upcoming
    tags: List[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.tags is None:
            self.tags = []

class AirdropFinder:
    """空投发现器"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.ua = UserAgent()
        self.discovered_airdrops: Dict[str, Airdrop] = {}
        self.last_check_time: Dict[str, float] = {}
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': self.ua.random},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
    
    async def find_all_airdrops(self) -> List[Airdrop]:
        """发现所有空投"""
        airdrops = []
        
        # 从多个来源获取空投
        sources = [
            self._get_airdrops_from_coingecko,
            self._get_airdrops_from_defillama,
            self._get_airdrops_from_twitter,
            self._get_airdrops_from_discord,
            self._get_airdrops_from_telegram
        ]
        
        tasks = [source() for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                airdrops.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"获取空投时出错: {result}")
        
        # 去重
        unique_airdrops = {}
        for airdrop in airdrops:
            key = f"{airdrop.project}_{airdrop.network}"
            if key not in unique_airdrops or airdrop.created_at > unique_airdrops[key].created_at:
                unique_airdrops[key] = airdrop
        
        self.discovered_airdrops = unique_airdrops
        logger.info(f"🎯 发现 {len(unique_airdrops)} 个空投机会")
        
        return list(unique_airdrops.values())
    
    async def _get_airdrops_from_coingecko(self) -> List[Airdrop]:
        """从CoinGecko获取空投信息"""
        airdrops = []
        
        try:
            url = "https://www.coingecko.com/en/airdrops"
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 解析空投列表
                    airdrop_rows = soup.find_all('tr', class_='table-row')
                    
                    for row in airdrop_rows[:10]:  # 限制数量
                        try:
                            cells = row.find_all('td')
                            if len(cells) >= 4:
                                name = cells[0].get_text(strip=True)
                                project = name
                                estimated_value = self._extract_value(cells[2].get_text(strip=True))
                                deadline_str = cells[3].get_text(strip=True)
                                
                                # 解析截止日期
                                deadline = self._parse_deadline(deadline_str)
                                
                                # 获取详情链接
                                link_elem = row.find('a', href=True)
                                url = f"https://www.coingecko.com{link_elem['href']}" if link_elem else ""
                                
                                airdrop = Airdrop(
                                    name=name,
                                    project=project,
                                    network="Multi-chain",
                                    description=f"{name} 空投活动",
                                    estimated_value=estimated_value,
                                    difficulty="medium",
                                    requirements=["钱包连接", "社交媒体关注"],
                                    deadline=deadline,
                                    url=url,
                                    tags=["coingecko", "verified"]
                                )
                                
                                airdrops.append(airdrop)
                                
                        except Exception as e:
                            logger.debug(f"解析CoinGecko空投时出错: {e}")
                            
        except Exception as e:
            logger.error(f"获取CoinGecko空投时出错: {e}")
        
        return airdrops
    
    async def _get_airdrops_from_defillama(self) -> List[Airdrop]:
        """从DeFiLlama获取空投信息"""
        airdrops = []
        
        try:
            url = "https://airdrops.defillama.com/api/airdrops"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get('airdrops', [])[:20]:
                        try:
                            airdrop = Airdrop(
                                name=item.get('name', ''),
                                project=item.get('project', ''),
                                network=item.get('network', 'Ethereum'),
                                description=item.get('description', ''),
                                estimated_value=float(item.get('estimated_value', 0)),
                                difficulty=item.get('difficulty', 'medium'),
                                requirements=item.get('requirements', []),
                                deadline=self._parse_deadline(item.get('deadline')),
                                url=item.get('url', ''),
                                tags=["defillama", "defi"]
                            )
                            
                            airdrops.append(airdrop)
                            
                        except Exception as e:
                            logger.debug(f"解析DeFiLlama空投时出错: {e}")
                            
        except Exception as e:
            logger.error(f"获取DeFiLlama空投时出错: {e}")
        
        return airdrops
    
    async def _get_airdrops_from_twitter(self) -> List[Airdrop]:
        """从Twitter获取空投信息"""
        # 这里简化实现，实际应该使用Twitter API
        airdrops = []
        
        # 模拟一些Twitter空投
        mock_airdrops = [
            {
                "name": "zkSync Airdrop",
                "project": "zkSync",
                "network": "zkSync Era",
                "description": "zkSync 生态空投，交互zkSync网络",
                "estimated_value": 500,
                "difficulty": "hard",
                "requirements": ["桥接资产", "交互DApp", "提供流动性"],
                "deadline": "2024-12-31",
                "url": "https://zksync.io",
                "tags": ["twitter", "layer2"]
            },
            {
                "name": "StarkNet Airdrop",
                "project": "StarkNet",
                "network": "StarkNet",
                "description": "StarkNet 潜在空投，需要交互",
                "estimated_value": 300,
                "difficulty": "medium",
                "requirements": ["使用StarkNet钱包", "交互DApp"],
                "deadline": "2024-11-30",
                "url": "https://starknet.io",
                "tags": ["twitter", "layer2"]
            }
        ]
        
        for item in mock_airdrops:
            try:
                airdrop = Airdrop(
                    name=item["name"],
                    project=item["project"],
                    network=item["network"],
                    description=item["description"],
                    estimated_value=item["estimated_value"],
                    difficulty=item["difficulty"],
                    requirements=item["requirements"],
                    deadline=self._parse_deadline(item["deadline"]),
                    url=item["url"],
                    tags=item["tags"]
                )
                
                airdrops.append(airdrop)
                
            except Exception as e:
                logger.debug(f"解析Twitter空投时出错: {e}")
        
        return airdrops
    
    async def _get_airdrops_from_discord(self) -> List[Airdrop]:
        """从Discord获取空投信息"""
        # 模拟Discord空投
        airdrops = []
        
        mock_airdrops = [
            {
                "name": "LayerZero Airdrop",
                "project": "LayerZero",
                "network": "Multi-chain",
                "description": "跨链桥协议空投",
                "estimated_value": 1000,
                "difficulty": "medium",
                "requirements": ["使用LayerZero桥", "参与社区"],
                "deadline": "2024-10-15",
                "url": "https://layerzero.network",
                "tags": ["discord", "bridge"]
            }
        ]
        
        for item in mock_airdrops:
            try:
                airdrop = Airdrop(
                    name=item["name"],
                    project=item["project"],
                    network=item["network"],
                    description=item["description"],
                    estimated_value=item["estimated_value"],
                    difficulty=item["difficulty"],
                    requirements=item["requirements"],
                    deadline=self._parse_deadline(item["deadline"]),
                    url=item["url"],
                    tags=item["tags"]
                )
                
                airdrops.append(airdrop)
                
            except Exception as e:
                logger.debug(f"解析Discord空投时出错: {e}")
        
        return airdrops
    
    async def _get_airdrops_from_telegram(self) -> List[Airdrop]:
        """从Telegram获取空投信息"""
        # 模拟Telegram空投
        airdrops = []
        
        mock_airdrops = [
            {
                "name": "Arbitrum Odyssey",
                "project": "Arbitrum",
                "network": "Arbitrum",
                "description": "Arbitrum生态任务活动",
                "estimated_value": 200,
                "difficulty": "easy",
                "requirements": ["完成Galxe任务", "桥接资产"],
                "deadline": "2024-09-30",
                "url": "https://arbitrum.io",
                "tags": ["telegram", "layer2"]
            }
        ]
        
        for item in mock_airdrops:
            try:
                airdrop = Airdrop(
                    name=item["name"],
                    project=item["project"],
                    network=item["network"],
                    description=item["description"],
                    estimated_value=item["estimated_value"],
                    difficulty=item["difficulty"],
                    requirements=item["requirements"],
                    deadline=self._parse_deadline(item["deadline"]),
                    url=item["url"],
                    tags=item["tags"]
                )
                
                airdrops.append(airdrop)
                
            except Exception as e:
                logger.debug(f"解析Telegram空投时出错: {e}")
        
        return airdrops
    
    def _extract_value(self, text: str) -> float:
        """从文本中提取价值"""
        match = re.search(r'[\d,]+\.?\d*', text.replace(',', ''))
        if match:
            return float(match.group())
        return 0.0
    
    def _parse_deadline(self, deadline_str: str) -> Optional[datetime]:
        """解析截止日期"""
        if not deadline_str or deadline_str.lower() in ['tba', 'ongoing', '']:
            return None
        
        try:
            # 尝试多种日期格式
            formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']
            for fmt in formats:
                try:
                    return datetime.strptime(deadline_str, fmt)
                except ValueError:
                    continue
            
            # 相对日期
            if 'days' in deadline_str.lower():
                days = int(re.search(r'\d+', deadline_str).group())
                return datetime.now() + timedelta(days=days)
                
        except Exception:
            pass
        
        return None
    
    def filter_airdrops(self, airdrops: List[Airdrop], 
                       min_value: float = 0, 
                       networks: List[str] = None,
                       difficulty: str = None) -> List[Airdrop]:
        """过滤空投
        
        Args:
            airdrops: 空投列表
            min_value: 最小价值
            networks: 指定网络
            difficulty: 难度等级
            
        Returns:
            过滤后的空投列表
        """
        filtered = airdrops
        
        if min_value > 0:
            filtered = [a for a in filtered if a.estimated_value >= min_value]
        
        if networks:
            filtered = [a for a in filtered if a.network.lower() in [n.lower() for n in networks]]
        
        if difficulty:
            filtered = [a for a in filtered if a.difficulty == difficulty]
        
        # 过滤已过期的
        now = datetime.now()
        filtered = [a for a in filtered if a.deadline is None or a.deadline > now]
        
        return filtered
    
    def save_airdrops(self, filename: str = "airdrops.json"):
        """保存空投信息到文件"""
        airdrops_data = []
        
        for airdrop in self.discovered_airdrops.values():
            airdrop_dict = {
                'name': airdrop.name,
                'project': airdrop.project,
                'network': airdrop.network,
                'description': airdrop.description,
                'estimated_value': airdrop.estimated_value,
                'difficulty': airdrop.difficulty,
                'requirements': airdrop.requirements,
                'deadline': airdrop.deadline.isoformat() if airdrop.deadline else None,
                'url': airdrop.url,
                'status': airdrop.status,
                'tags': airdrop.tags,
                'created_at': airdrop.created_at.isoformat()
            }
            airdrops_data.append(airdrop_dict)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(airdrops_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 已保存 {len(airdrops_data)} 个空投到 {filename}")

# 使用示例
async def main():
    async with AirdropFinder() as finder:
        airdrops = await finder.find_all_airdrops()
        filtered = finder.filter_airdrops(airdrops, min_value=100)
        
        for airdrop in filtered[:5]:
            print(f"🎯 {airdrop.name} - {airdrop.project}")
            print(f"   价值: ${airdrop.estimated_value}")
            print(f"   网络: {airdrop.network}")
            print(f"   难度: {airdrop.difficulty}")
            print(f"   截止: {airdrop.deadline}")
            print(f"   要求: {', '.join(airdrop.requirements)}")
            print(f"   链接: {airdrop.url}")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())