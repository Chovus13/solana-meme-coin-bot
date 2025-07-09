"""
Token analysis module for evaluating memecoin safety, market data, and contract information
"""

import asyncio
import logging
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import time

class TokenAnalyzer:
    """Comprehensive token analysis using multiple data sources"""
    
    def __init__(self, api_keys):
        """Initialize token analyzer with API keys"""
        self.logger = logging.getLogger(__name__)
        self.api_keys = api_keys
        
        # API endpoints
        self.solsniffer_base_url = "https://solsniffer.com/api/v2"
        self.gmgn_base_url = "https://gmgn.ai/defi/quotation/v1"
        self.pumpfun_base_url = "https://frontend-api.pump.fun"
        self.birdeye_base_url = "https://public-api.birdeye.so/defi"
        
        # Rate limiting
        self.rate_limits = {
            'solsniffer': {'calls': 0, 'reset_time': 0, 'limit_per_minute': 30},
            'gmgn': {'calls': 0, 'reset_time': 0, 'limit_per_minute': 60},
            'pumpfun': {'calls': 0, 'reset_time': 0, 'limit_per_minute': 100},
            'birdeye': {'calls': 0, 'reset_time': 0, 'limit_per_minute': 50}
        }
        
        # Cache for recent results
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
    
    async def get_safety_score(self, token_address: str) -> int:
        """Get token safety score from Solsniffer"""
        try:
            # Check cache first
            cache_key = f"safety_{token_address}"
            if self._is_cached(cache_key):
                return self.cache[cache_key]['data']
            
            await self._rate_limit('solsniffer')
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.solsniffer_base_url}/token/{token_address}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Extract safety score
                        safety_score = data.get('score', 0)
                        
                        # Cache result
                        self._cache_result(cache_key, safety_score)
                        
                        self.logger.info(f"Safety score for {token_address}: {safety_score}")
                        return safety_score
                    
                    elif response.status == 404:
                        # Token not found, might be new
                        self.logger.warning(f"Token {token_address} not found in Solsniffer")
                        return 0
                    
                    else:
                        self.logger.error(f"Solsniffer API error: {response.status}")
                        return 0
        
        except Exception as e:
            self.logger.error(f"Error getting safety score for {token_address}: {e}")
            return 0
    
    async def get_market_data(self, token_address: str) -> Dict[str, Any]:
        """Get comprehensive market data for a token"""
        try:
            # Check cache first
            cache_key = f"market_{token_address}"
            if self._is_cached(cache_key):
                return self.cache[cache_key]['data']
            
            # Combine data from multiple sources
            market_data = {}
            
            # Get GMGN data
            gmgn_data = await self._get_gmgn_data(token_address)
            market_data.update(gmgn_data)
            
            # Get PumpFun data
            pumpfun_data = await self._get_pumpfun_data(token_address)
            market_data.update(pumpfun_data)
            
            # Get Birdeye data
            birdeye_data = await self._get_birdeye_data(token_address)
            market_data.update(birdeye_data)
            
            # Calculate derived metrics
            market_data = self._calculate_derived_metrics(market_data)
            
            # Cache result
            self._cache_result(cache_key, market_data)
            
            return market_data
        
        except Exception as e:
            self.logger.error(f"Error getting market data for {token_address}: {e}")
            return {}
    
    async def _get_gmgn_data(self, token_address: str) -> Dict[str, Any]:
        """Get token data from GMGN API"""
        try:
            await self._rate_limit('gmgn')
            
            async with aiohttp.ClientSession() as session:
                # Get token info
                url = f"{self.gmgn_base_url}/tokens/sol/{token_address}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('code') == 0 and data.get('data'):
                            token_data = data['data']['token']
                            
                            return {
                                'market_cap': token_data.get('market_cap', 0),
                                'price': float(token_data.get('price', 0)),
                                'volume_24h': token_data.get('volume_24h', 0),
                                'liquidity': token_data.get('liquidity', 0),
                                'holder_count': token_data.get('holder_count', 0),
                                'creation_timestamp': token_data.get('creation_timestamp', 0),
                                'creator': token_data.get('creator', ''),
                                'name': token_data.get('name', ''),
                                'symbol': token_data.get('symbol', ''),
                                'decimals': token_data.get('decimals', 9),
                                'total_supply': token_data.get('total_supply', 0),
                                'gmgn_rank': token_data.get('rank', 0)
                            }
            
            return {}
        
        except Exception as e:
            self.logger.error(f"Error getting GMGN data for {token_address}: {e}")
            return {}
    
    async def _get_pumpfun_data(self, token_address: str) -> Dict[str, Any]:
        """Get token data from PumpFun API"""
        try:
            await self._rate_limit('pumpfun')
            
            async with aiohttp.ClientSession() as session:
                # Get coin data
                url = f"{self.pumpfun_base_url}/coins/{token_address}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        return {
                            'pumpfun_market_cap': data.get('market_cap', 0),
                            'pumpfun_price': float(data.get('usd_market_cap', 0)) / float(data.get('total_supply', 1)) if data.get('total_supply') else 0,
                            'pumpfun_complete': data.get('complete', False),
                            'pumpfun_creator': data.get('creator', ''),
                            'pumpfun_created_timestamp': data.get('created_timestamp', 0),
                            'pumpfun_description': data.get('description', ''),
                            'pumpfun_image_uri': data.get('image_uri', ''),
                            'pumpfun_telegram': data.get('telegram', ''),
                            'pumpfun_twitter': data.get('twitter', ''),
                            'pumpfun_website': data.get('website', ''),
                            'is_pumpfun_token': True
                        }
            
            return {'is_pumpfun_token': False}
        
        except Exception as e:
            self.logger.error(f"Error getting PumpFun data for {token_address}: {e}")
            return {'is_pumpfun_token': False}
    
    async def _get_birdeye_data(self, token_address: str) -> Dict[str, Any]:
        """Get token data from Birdeye API"""
        try:
            await self._rate_limit('birdeye')
            
            headers = {
                'X-API-KEY': self.api_keys.birdeye_api_key if hasattr(self.api_keys, 'birdeye_api_key') else ''
            }
            
            async with aiohttp.ClientSession(headers=headers) as session:
                # Get token overview
                url = f"{self.birdeye_base_url}/token_overview"
                params = {'address': token_address}
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('success') and data.get('data'):
                            token_data = data['data']
                            
                            return {
                                'birdeye_price': float(token_data.get('price', 0)),
                                'birdeye_market_cap': token_data.get('mc', 0),
                                'birdeye_volume_24h': token_data.get('v24h', 0),
                                'birdeye_liquidity': token_data.get('liquidity', 0),
                                'birdeye_price_change_24h': token_data.get('priceChange24h', 0),
                                'birdeye_price_change_percentage_24h': token_data.get('priceChange24hPercent', 0),
                                'birdeye_last_trade_unix_time': token_data.get('lastTradeUnixTime', 0),
                                'birdeye_buy_24h': token_data.get('buy24h', 0),
                                'birdeye_sell_24h': token_data.get('sell24h', 0),
                                'birdeye_trade_24h': token_data.get('trade24h', 0)
                            }
            
            return {}
        
        except Exception as e:
            self.logger.error(f"Error getting Birdeye data for {token_address}: {e}")
            return {}
    
    def _calculate_derived_metrics(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate derived metrics from market data"""
        try:
            # Get price from available sources (prefer GMGN, fallback to others)
            price = market_data.get('price') or market_data.get('birdeye_price') or market_data.get('pumpfun_price', 0)
            
            # Get market cap from available sources
            market_cap = market_data.get('market_cap') or market_data.get('birdeye_market_cap') or market_data.get('pumpfun_market_cap', 0)
            
            # Get volume from available sources
            volume_24h = market_data.get('volume_24h') or market_data.get('birdeye_volume_24h', 0)
            
            # Get liquidity from available sources
            liquidity = market_data.get('liquidity') or market_data.get('birdeye_liquidity', 0)
            
            # Calculate age in hours
            creation_timestamp = market_data.get('creation_timestamp') or market_data.get('pumpfun_created_timestamp', 0)
            if creation_timestamp:
                age_hours = (time.time() - creation_timestamp) / 3600
            else:
                age_hours = 24  # Default assumption
            
            # Calculate volume to market cap ratio
            volume_mc_ratio = volume_24h / market_cap if market_cap > 0 else 0
            
            # Calculate liquidity to market cap ratio
            liquidity_mc_ratio = liquidity / market_cap if market_cap > 0 else 0
            
            # Determine if liquidity is locked (simplified heuristic)
            liquidity_locked = liquidity_mc_ratio > 0.1  # At least 10% of market cap in liquidity
            
            # Determine if mint is disabled (would need contract analysis)
            # For now, use heuristics
            mint_disabled = age_hours > 1  # Assume older tokens have disabled mint
            
            # Calculate holder distribution score
            holder_count = market_data.get('holder_count', 0)
            if holder_count > 0:
                # Simple heuristic for distribution
                if holder_count > 1000:
                    distribution_score = 1.0
                elif holder_count > 100:
                    distribution_score = 0.8
                elif holder_count > 10:
                    distribution_score = 0.6
                else:
                    distribution_score = 0.3
            else:
                distribution_score = 0.0
            
            # Add derived metrics
            market_data.update({
                'unified_price': price,
                'unified_market_cap': market_cap,
                'unified_volume_24h': volume_24h,
                'unified_liquidity': liquidity,
                'age_hours': age_hours,
                'volume_mc_ratio': volume_mc_ratio,
                'liquidity_mc_ratio': liquidity_mc_ratio,
                'liquidity_locked': liquidity_locked,
                'mint_disabled': mint_disabled,
                'distribution_score': distribution_score,
                'last_updated': time.time()
            })
            
            return market_data
        
        except Exception as e:
            self.logger.error(f"Error calculating derived metrics: {e}")
            return market_data
    
    async def get_contract_info(self, token_address: str) -> Dict[str, Any]:
        """Get detailed contract information"""
        try:
            # This would typically involve on-chain analysis
            # For now, return basic structure
            return {
                'address': token_address,
                'is_verified': True,  # Would need actual verification
                'has_proxy': False,   # Would need contract analysis
                'owner_functions': [],  # Would need ABI analysis
                'risk_factors': []      # Would need security analysis
            }
        
        except Exception as e:
            self.logger.error(f"Error getting contract info for {token_address}: {e}")
            return {}
    
    async def get_social_metrics(self, token_address: str) -> Dict[str, Any]:
        """Get social media metrics for a token"""
        try:
            # This would integrate with social media APIs
            # For now, return placeholder structure
            return {
                'twitter_mentions': 0,
                'telegram_members': 0,
                'discord_members': 0,
                'reddit_mentions': 0,
                'sentiment_score': 0.5,
                'social_volume': 0,
                'social_dominance': 0.0
            }
        
        except Exception as e:
            self.logger.error(f"Error getting social metrics for {token_address}: {e}")
            return {}
    
    async def analyze_liquidity_locks(self, token_address: str) -> Dict[str, Any]:
        """Analyze liquidity lock status"""
        try:
            # This would need on-chain analysis of liquidity pools
            # For now, return basic structure
            return {
                'has_locked_liquidity': False,
                'lock_percentage': 0.0,
                'lock_duration': 0,
                'lock_contract': '',
                'unlock_date': None
            }
        
        except Exception as e:
            self.logger.error(f"Error analyzing liquidity locks for {token_address}: {e}")
            return {}
    
    async def get_whale_analysis(self, token_address: str) -> Dict[str, Any]:
        """Analyze whale holdings and transactions"""
        try:
            # This would need on-chain analysis
            # For now, return basic structure
            return {
                'top_10_holders_percentage': 0.0,
                'whale_transactions_24h': 0,
                'largest_holder_percentage': 0.0,
                'distribution_quality': 'unknown'
            }
        
        except Exception as e:
            self.logger.error(f"Error analyzing whale data for {token_address}: {e}")
            return {}
    
    async def _rate_limit(self, api_name: str):
        """Implement rate limiting for APIs"""
        try:
            current_time = time.time()
            rate_limit = self.rate_limits[api_name]
            
            # Reset counter if minute has passed
            if current_time - rate_limit['reset_time'] >= 60:
                rate_limit['calls'] = 0
                rate_limit['reset_time'] = current_time
            
            # Check if we've exceeded the limit
            if rate_limit['calls'] >= rate_limit['limit_per_minute']:
                sleep_time = 60 - (current_time - rate_limit['reset_time'])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                # Reset after sleeping
                rate_limit['calls'] = 0
                rate_limit['reset_time'] = time.time()
            
            # Increment call counter
            rate_limit['calls'] += 1
        
        except Exception as e:
            self.logger.error(f"Error in rate limiting for {api_name}: {e}")
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if result is cached and still valid"""
        if cache_key not in self.cache:
            return False
        
        cache_entry = self.cache[cache_key]
        return (time.time() - cache_entry['timestamp']) < self.cache_duration
    
    def _cache_result(self, cache_key: str, data: Any):
        """Cache a result"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        
        # Clean old cache entries
        self._clean_cache()
    
    def _clean_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, value in self.cache.items()
            if (current_time - value['timestamp']) >= self.cache_duration
        ]
        
        for key in expired_keys:
            del self.cache[key]
    
    async def get_comprehensive_analysis(self, token_address: str) -> Dict[str, Any]:
        """Get comprehensive token analysis"""
        try:
            # Run all analyses concurrently
            tasks = [
                self.get_safety_score(token_address),
                self.get_market_data(token_address),
                self.get_contract_info(token_address),
                self.get_social_metrics(token_address),
                self.analyze_liquidity_locks(token_address),
                self.get_whale_analysis(token_address)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine all results
            comprehensive_analysis = {
                'token_address': token_address,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'safety_score': results[0] if not isinstance(results[0], Exception) else 0,
                'market_data': results[1] if not isinstance(results[1], Exception) else {},
                'contract_info': results[2] if not isinstance(results[2], Exception) else {},
                'social_metrics': results[3] if not isinstance(results[3], Exception) else {},
                'liquidity_analysis': results[4] if not isinstance(results[4], Exception) else {},
                'whale_analysis': results[5] if not isinstance(results[5], Exception) else {}
            }
            
            # Calculate overall risk score
            comprehensive_analysis['overall_risk_score'] = self._calculate_overall_risk(comprehensive_analysis)
            
            return comprehensive_analysis
        
        except Exception as e:
            self.logger.error(f"Error in comprehensive analysis for {token_address}: {e}")
            return {}
    
    def _calculate_overall_risk(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall risk score based on all factors"""
        try:
            risk_factors = []
            
            # Safety score factor (higher is better)
            safety_score = analysis.get('safety_score', 0)
            safety_risk = max(0, (100 - safety_score) / 100)
            risk_factors.append(safety_risk * 0.3)  # 30% weight
            
            # Market data factors
            market_data = analysis.get('market_data', {})
            
            # Age factor (very new tokens are riskier)
            age_hours = market_data.get('age_hours', 24)
            age_risk = max(0, (24 - age_hours) / 24) if age_hours < 24 else 0
            risk_factors.append(age_risk * 0.2)  # 20% weight
            
            # Liquidity factor
            liquidity_mc_ratio = market_data.get('liquidity_mc_ratio', 0)
            liquidity_risk = max(0, (0.1 - liquidity_mc_ratio) / 0.1) if liquidity_mc_ratio < 0.1 else 0
            risk_factors.append(liquidity_risk * 0.2)  # 20% weight
            
            # Distribution factor
            distribution_score = market_data.get('distribution_score', 0)
            distribution_risk = 1 - distribution_score
            risk_factors.append(distribution_risk * 0.15)  # 15% weight
            
            # Social sentiment factor
            social_metrics = analysis.get('social_metrics', {})
            sentiment_score = social_metrics.get('sentiment_score', 0.5)
            sentiment_risk = 1 - sentiment_score
            risk_factors.append(sentiment_risk * 0.15)  # 15% weight
            
            # Calculate weighted average
            overall_risk = sum(risk_factors)
            
            return min(1.0, max(0.0, overall_risk))
        
        except Exception as e:
            self.logger.error(f"Error calculating overall risk: {e}")
            return 0.5  # Default medium risk
