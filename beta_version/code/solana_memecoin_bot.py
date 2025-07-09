"""
Main Solana Memecoin Trading Bot
Integrates social media monitoring, token analysis, AI prediction, and automated trading
"""

import asyncio
import logging
import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue
import signal
import sys

# Local imports
from config import (
    api_keys, trading_config, monitoring_config, 
    filter_config, web_config, database_config, validate_config
)
from social_media.twitter_monitor import TwitterMonitor
from social_media.reddit_monitor import RedditMonitor
from social_media.discord_monitor import DiscordMonitor
from social_media.telegram_monitor import TelegramMonitor
from social_media.tiktok_monitor import TikTokMonitor
from token_analysis.token_analyzer import TokenAnalyzer
from token_analysis.ai_predictor import AIPredictor
from trading.solana_trader import SolanaTrader
from utils.database import DatabaseManager
from utils.notifier import NotificationManager
from utils.logger import setup_logger

@dataclass
class TokenDiscovery:
    """Data class for discovered tokens"""
    symbol: str
    contract_address: str
    source: str  # twitter, reddit, discord, telegram, tiktok
    timestamp: datetime
    original_message: str
    author: str
    platform_url: str
    confidence_score: float = 0.0
    social_metrics: Dict[str, Any] = None

@dataclass
class TokenAnalysis:
    """Data class for token analysis results"""
    token_discovery: TokenDiscovery
    safety_score: int
    market_data: Dict[str, Any]
    ai_prediction: Dict[str, Any]
    filter_passed: bool
    analysis_timestamp: datetime
    recommendation: str  # BUY, PASS, MONITOR

@dataclass
class Position:
    """Data class for trading positions"""
    token_address: str
    symbol: str
    entry_price: float
    current_price: float
    amount_sol: float
    tokens_held: float
    entry_timestamp: datetime
    status: str  # OPEN, CLOSED, PARTIAL_CLOSE
    pnl_percent: float = 0.0
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0

class SolanaMemecoinBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        """Initialize the bot with all components"""
        self.logger = setup_logger("SolanaMemecoinBot")
        self.running = False
        self.paused = False
        
        # Core components
        self.db_manager = DatabaseManager(database_config.database_path)
        self.notification_manager = NotificationManager(api_keys.notification_webhook)
        
        # Social media monitors
        self.twitter_monitor = TwitterMonitor(api_keys)
        self.reddit_monitor = RedditMonitor(api_keys)
        self.discord_monitor = DiscordMonitor(api_keys)
        self.telegram_monitor = TelegramMonitor(api_keys)
        self.tiktok_monitor = TikTokMonitor(api_keys)
        
        # Analysis components
        self.token_analyzer = TokenAnalyzer(api_keys)
        self.ai_predictor = AIPredictor()
        
        # Trading component
        self.solana_trader = SolanaTrader(api_keys, trading_config)
        
        # Data queues
        self.discovery_queue = Queue()
        self.analysis_queue = Queue()
        self.trading_queue = Queue()
        
        # State tracking
        self.discovered_tokens: Dict[str, TokenDiscovery] = {}
        self.analyzed_tokens: Dict[str, TokenAnalysis] = {}
        self.active_positions: Dict[str, Position] = {}
        self.processed_messages: set = set()
        
        # Statistics
        self.stats = {
            'tokens_discovered': 0,
            'tokens_analyzed': 0,
            'positions_opened': 0,
            'positions_closed': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'start_time': None
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("SolanaMemecoinBot initialized successfully")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
        sys.exit(0)
    
    async def start(self):
        """Start the bot and all monitoring processes"""
        if not validate_config():
            self.logger.error("Configuration validation failed")
            return False
        
        self.logger.info("Starting Solana Memecoin Trading Bot...")
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        try:
            # Initialize database
            await self.db_manager.initialize()
            
            # Load existing positions
            await self._load_existing_positions()
            
            # Start social media monitors
            monitor_tasks = []
            
            if api_keys.twitter_bearer_token:
                monitor_tasks.append(self._start_twitter_monitoring())
            
            if api_keys.reddit_client_id:
                monitor_tasks.append(self._start_reddit_monitoring())
            
            if api_keys.discord_token:
                monitor_tasks.append(self._start_discord_monitoring())
            
            if api_keys.telegram_api_id:
                monitor_tasks.append(self._start_telegram_monitoring())
            
            if api_keys.tiktok_session_id:
                monitor_tasks.append(self._start_tiktok_monitoring())
            
            # Start processing pipelines
            processing_tasks = [
                self._process_discoveries(),
                self._process_analysis(),
                self._process_trading(),
                self._monitor_positions(),
                self._update_statistics()
            ]
            
            # Combine all tasks
            all_tasks = monitor_tasks + processing_tasks
            
            # Start all tasks
            await asyncio.gather(*all_tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"Error starting bot: {e}")
            return False
        
        return True
    
    def stop(self):
        """Stop the bot and all processes"""
        self.logger.info("Stopping Solana Memecoin Trading Bot...")
        self.running = False
        
        # Save current state
        self._save_state()
        
        # Close all positions if requested
        # self._close_all_positions()
        
        self.logger.info("Bot stopped successfully")
    
    def pause(self):
        """Pause bot operations (monitoring continues, trading stops)"""
        self.paused = True
        self.logger.info("Bot paused - monitoring continues, trading stopped")
    
    def resume(self):
        """Resume bot operations"""
        self.paused = False
        self.logger.info("Bot resumed - full operations active")
    
    async def _start_twitter_monitoring(self):
        """Start Twitter monitoring task"""
        self.logger.info("Starting Twitter monitoring...")
        
        while self.running:
            try:
                # Monitor specific accounts
                for account in monitoring_config.twitter_accounts:
                    tweets = await self.twitter_monitor.get_recent_tweets(
                        account, 
                        monitoring_config.memecoin_keywords
                    )
                    
                    for tweet in tweets:
                        await self._process_social_message(tweet, 'twitter')
                
                # Monitor keywords
                keyword_tweets = await self.twitter_monitor.search_tweets(
                    monitoring_config.memecoin_keywords,
                    limit=50
                )
                
                for tweet in keyword_tweets:
                    await self._process_social_message(tweet, 'twitter')
                
                await asyncio.sleep(monitoring_config.twitter_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in Twitter monitoring: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _start_reddit_monitoring(self):
        """Start Reddit monitoring task"""
        self.logger.info("Starting Reddit monitoring...")
        
        while self.running:
            try:
                for subreddit in monitoring_config.reddit_subreddits:
                    posts = await self.reddit_monitor.get_hot_posts(
                        subreddit,
                        monitoring_config.memecoin_keywords,
                        limit=25
                    )
                    
                    for post in posts:
                        await self._process_social_message(post, 'reddit')
                
                await asyncio.sleep(monitoring_config.reddit_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in Reddit monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _start_discord_monitoring(self):
        """Start Discord monitoring task"""
        self.logger.info("Starting Discord monitoring...")
        
        while self.running:
            try:
                messages = await self.discord_monitor.get_recent_messages(
                    monitoring_config.discord_channels,
                    monitoring_config.memecoin_keywords
                )
                
                for message in messages:
                    await self._process_social_message(message, 'discord')
                
                await asyncio.sleep(monitoring_config.discord_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in Discord monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _start_telegram_monitoring(self):
        """Start Telegram monitoring task"""
        self.logger.info("Starting Telegram monitoring...")
        
        while self.running:
            try:
                messages = await self.telegram_monitor.get_channel_messages(
                    monitoring_config.telegram_channels,
                    monitoring_config.memecoin_keywords
                )
                
                for message in messages:
                    await self._process_social_message(message, 'telegram')
                
                await asyncio.sleep(monitoring_config.telegram_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in Telegram monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _start_tiktok_monitoring(self):
        """Start TikTok monitoring task"""
        self.logger.info("Starting TikTok monitoring...")
        
        while self.running:
            try:
                videos = await self.tiktok_monitor.search_hashtags(
                    ['#memecoin', '#solana', '#crypto', '#pump'],
                    limit=20
                )
                
                for video in videos:
                    await self._process_social_message(video, 'tiktok')
                
                await asyncio.sleep(monitoring_config.tiktok_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in TikTok monitoring: {e}")
                await asyncio.sleep(300)  # Longer wait for TikTok errors
    
    async def _process_social_message(self, message: Dict[str, Any], source: str):
        """Process a social media message for token discovery"""
        try:
            # Extract message ID for deduplication
            message_id = f"{source}_{message.get('id', message.get('url', str(hash(str(message)))))}"
            
            if message_id in self.processed_messages:
                return
            
            self.processed_messages.add(message_id)
            
            # Extract potential token information
            token_info = self._extract_token_info(message, source)
            
            if token_info:
                discovery = TokenDiscovery(
                    symbol=token_info['symbol'],
                    contract_address=token_info['contract_address'],
                    source=source,
                    timestamp=datetime.now(),
                    original_message=message.get('text', message.get('content', '')),
                    author=message.get('author', message.get('username', 'unknown')),
                    platform_url=message.get('url', ''),
                    confidence_score=token_info.get('confidence', 0.5)
                )
                
                # Add to discovery queue
                self.discovery_queue.put(discovery)
                self.stats['tokens_discovered'] += 1
                
                self.logger.info(f"Token discovered: {discovery.symbol} from {source}")
        
        except Exception as e:
            self.logger.error(f"Error processing social message: {e}")
    
    def _extract_token_info(self, message: Dict[str, Any], source: str) -> Optional[Dict[str, Any]]:
        """Extract token information from social media message"""
        import re
        
        text = message.get('text', message.get('content', ''))
        if not text:
            return None
        
        # Look for contract addresses (Solana addresses are base58, 32-44 chars)
        contract_pattern = r'[A-HJ-NP-Z1-9]{32,44}'
        contracts = re.findall(contract_pattern, text)
        
        # Look for ticker symbols
        ticker_pattern = r'\\$([A-Z]{2,10})\\b'
        tickers = re.findall(ticker_pattern, text.upper())
        
        # Look for CA: pattern
        ca_pattern = r'CA:?\\s*([A-HJ-NP-Z1-9]{32,44})'
        ca_matches = re.findall(ca_pattern, text)
        
        contracts.extend(ca_matches)
        
        if not contracts and not tickers:
            return None
        
        # Calculate confidence based on context
        confidence = 0.3  # Base confidence
        
        # Boost confidence for certain keywords
        boost_keywords = ['pump', 'moon', 'gem', 'launched', 'new token', 'fair launch']
        for keyword in boost_keywords:
            if keyword.lower() in text.lower():
                confidence += 0.2
        
        # Boost confidence for contract addresses
        if contracts:
            confidence += 0.3
        
        # Reduce confidence for negative keywords
        negative_keywords = ['scam', 'rug', 'avoid', 'warning']
        for keyword in negative_keywords:
            if keyword.lower() in text.lower():
                confidence -= 0.4
        
        confidence = max(0.0, min(1.0, confidence))
        
        return {
            'symbol': tickers[0] if tickers else 'UNKNOWN',
            'contract_address': contracts[0] if contracts else '',
            'confidence': confidence
        }
    
    async def _process_discoveries(self):
        """Process discovered tokens for analysis"""
        self.logger.info("Starting discovery processing...")
        
        while self.running:
            try:
                if not self.discovery_queue.empty():
                    discovery = self.discovery_queue.get()
                    
                    # Skip if already analyzed recently
                    if discovery.contract_address in self.discovered_tokens:
                        last_discovery = self.discovered_tokens[discovery.contract_address]
                        if (datetime.now() - last_discovery.timestamp).seconds < 3600:  # 1 hour
                            continue
                    
                    # Store discovery
                    self.discovered_tokens[discovery.contract_address] = discovery
                    
                    # Add to analysis queue
                    self.analysis_queue.put(discovery)
                    
                    # Save to database
                    await self.db_manager.save_discovery(discovery)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error processing discoveries: {e}")
                await asyncio.sleep(5)
    
    async def _process_analysis(self):
        """Process token analysis pipeline"""
        self.logger.info("Starting analysis processing...")
        
        while self.running:
            try:
                if not self.analysis_queue.empty():
                    discovery = self.analysis_queue.get()
                    
                    # Skip if confidence too low
                    if discovery.confidence_score < 0.4:
                        self.logger.debug(f"Skipping {discovery.symbol} - low confidence")
                        continue
                    
                    # Perform comprehensive analysis
                    analysis = await self._analyze_token(discovery)
                    
                    if analysis:
                        self.analyzed_tokens[discovery.contract_address] = analysis
                        self.stats['tokens_analyzed'] += 1
                        
                        # Save analysis to database
                        await self.db_manager.save_analysis(analysis)
                        
                        # Add to trading queue if passed filters
                        if analysis.filter_passed and analysis.recommendation == 'BUY':
                            self.trading_queue.put(analysis)
                            
                            self.logger.info(f"Token {analysis.token_discovery.symbol} passed filters - queued for trading")
                
                await asyncio.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Error processing analysis: {e}")
                await asyncio.sleep(5)
    
    async def _analyze_token(self, discovery: TokenDiscovery) -> Optional[TokenAnalysis]:
        """Perform comprehensive token analysis"""
        try:
            self.logger.info(f"Analyzing token: {discovery.symbol}")
            
            # Get safety score from Solsniffer
            safety_score = await self.token_analyzer.get_safety_score(discovery.contract_address)
            
            if safety_score < filter_config.min_safety_score:
                self.logger.info(f"Token {discovery.symbol} failed safety check: {safety_score}")
                
                # Send notification for low safety score
                await self.notification_manager.send_notification(
                    f"⚠️ Low Safety Score Alert\\n"
                    f"Token: {discovery.symbol}\\n"
                    f"Safety Score: {safety_score}/100\\n"
                    f"Contract: {discovery.contract_address}\\n"
                    f"Source: {discovery.source}"
                )
                
                return TokenAnalysis(
                    token_discovery=discovery,
                    safety_score=safety_score,
                    market_data={},
                    ai_prediction={},
                    filter_passed=False,
                    analysis_timestamp=datetime.now(),
                    recommendation='PASS'
                )
            
            # Get market data
            market_data = await self.token_analyzer.get_market_data(discovery.contract_address)
            
            # Check market filters
            if not self._check_market_filters(market_data):
                return TokenAnalysis(
                    token_discovery=discovery,
                    safety_score=safety_score,
                    market_data=market_data,
                    ai_prediction={},
                    filter_passed=False,
                    analysis_timestamp=datetime.now(),
                    recommendation='PASS'
                )
            
            # Get AI prediction
            ai_prediction = await self.ai_predictor.predict_success(
                discovery, market_data, safety_score
            )
            
            # Determine recommendation
            recommendation = self._get_recommendation(safety_score, market_data, ai_prediction)
            
            analysis = TokenAnalysis(
                token_discovery=discovery,
                safety_score=safety_score,
                market_data=market_data,
                ai_prediction=ai_prediction,
                filter_passed=recommendation in ['BUY', 'MONITOR'],
                analysis_timestamp=datetime.now(),
                recommendation=recommendation
            )
            
            self.logger.info(f"Analysis complete for {discovery.symbol}: {recommendation}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing token {discovery.symbol}: {e}")
            return None
    
    def _check_market_filters(self, market_data: Dict[str, Any]) -> bool:
        """Check if token passes market-based filters"""
        try:
            market_cap = market_data.get('market_cap', 0)
            liquidity = market_data.get('liquidity', 0)
            volume_24h = market_data.get('volume_24h', 0)
            
            # Market cap filter
            if market_cap < filter_config.min_market_cap or market_cap > filter_config.max_market_cap:
                return False
            
            # Liquidity filter
            if liquidity < filter_config.min_liquidity:
                return False
            
            # Volume filter
            if volume_24h < filter_config.min_volume_24h:
                return False
            
            # Liquidity lock check
            if filter_config.require_locked_liquidity and not market_data.get('liquidity_locked', False):
                return False
            
            # Mint disabled check
            if filter_config.require_disabled_mint and not market_data.get('mint_disabled', False):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking market filters: {e}")
            return False
    
    def _get_recommendation(self, safety_score: int, market_data: Dict[str, Any], ai_prediction: Dict[str, Any]) -> str:
        """Get trading recommendation based on analysis"""
        try:
            # Safety score requirement
            if safety_score < filter_config.min_safety_score:
                return 'PASS'
            
            # AI prediction score
            ai_score = ai_prediction.get('success_probability', 0)
            
            # Market conditions
            market_score = self._calculate_market_score(market_data)
            
            # Combined score
            combined_score = (safety_score * 0.4 + ai_score * 100 * 0.4 + market_score * 0.2) / 100
            
            if combined_score >= 0.75:
                return 'BUY'
            elif combined_score >= 0.6:
                return 'MONITOR'
            else:
                return 'PASS'
                
        except Exception as e:
            self.logger.error(f"Error getting recommendation: {e}")
            return 'PASS'
    
    def _calculate_market_score(self, market_data: Dict[str, Any]) -> float:
        """Calculate market condition score"""
        score = 0.0
        
        try:
            # Volume score (normalized)
            volume = market_data.get('volume_24h', 0)
            volume_score = min(volume / 10000, 1.0)  # Cap at $10k
            score += volume_score * 0.3
            
            # Liquidity score
            liquidity = market_data.get('liquidity', 0)
            liquidity_score = min(liquidity / 50000, 1.0)  # Cap at $50k
            score += liquidity_score * 0.3
            
            # Age score (newer is better for memecoins)
            age_hours = market_data.get('age_hours', 24)
            age_score = max(0, 1.0 - (age_hours / 24))  # Decaying score over 24h
            score += age_score * 0.2
            
            # Holder distribution score
            holder_count = market_data.get('holder_count', 1)
            holder_score = min(holder_count / 1000, 1.0)  # Cap at 1000 holders
            score += holder_score * 0.2
            
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating market score: {e}")
            return 0.0
    
    async def _process_trading(self):
        """Process trading decisions"""
        self.logger.info("Starting trading processing...")
        
        while self.running:
            try:
                if self.paused:
                    await asyncio.sleep(10)
                    continue
                
                if not self.trading_queue.empty():
                    analysis = self.trading_queue.get()
                    
                    # Check position limits
                    if len(self.active_positions) >= trading_config.max_positions:
                        self.logger.info("Maximum positions reached, skipping trade")
                        continue
                    
                    # Execute trade
                    success = await self._execute_buy_order(analysis)
                    
                    if success:
                        self.logger.info(f"Successfully opened position for {analysis.token_discovery.symbol}")
                
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error processing trading: {e}")
                await asyncio.sleep(10)
    
    async def _execute_buy_order(self, analysis: TokenAnalysis) -> bool:
        """Execute a buy order for a token"""
        try:
            token_address = analysis.token_discovery.contract_address
            symbol = analysis.token_discovery.symbol
            
            # Check if already have position
            if token_address in self.active_positions:
                self.logger.info(f"Already have position in {symbol}")
                return False
            
            # Calculate position size
            buy_amount = min(
                trading_config.buy_amount_sol,
                trading_config.max_buy_amount_sol
            )
            
            # Execute buy order
            result = await self.solana_trader.buy_token(
                token_address=token_address,
                amount_sol=buy_amount,
                slippage=trading_config.buy_slippage
            )
            
            if result['success']:
                # Create position
                position = Position(
                    token_address=token_address,
                    symbol=symbol,
                    entry_price=result['price'],
                    current_price=result['price'],
                    amount_sol=buy_amount,
                    tokens_held=result['tokens_received'],
                    entry_timestamp=datetime.now(),
                    status='OPEN'
                )
                
                # Set stop loss and take profit
                position.stop_loss_price = result['price'] * (1 - trading_config.stop_loss_percentage)
                position.take_profit_price = result['price'] * trading_config.take_profit_multiplier
                
                self.active_positions[token_address] = position
                self.stats['positions_opened'] += 1
                
                # Save position to database
                await self.db_manager.save_position(position)
                
                # Send notification
                await self.notification_manager.send_notification(
                    f"🚀 Position Opened\\n"
                    f"Token: {symbol}\\n"
                    f"Amount: {buy_amount} SOL\\n"
                    f"Price: ${result['price']:.8f}\\n"
                    f"Tokens: {result['tokens_received']:,.0f}\\n"
                    f"Target: {trading_config.take_profit_multiplier}x"
                )
                
                return True
            else:
                self.logger.error(f"Failed to buy {symbol}: {result['error']}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error executing buy order: {e}")
            return False
    
    async def _monitor_positions(self):
        """Monitor open positions and manage exits"""
        self.logger.info("Starting position monitoring...")
        
        while self.running:
            try:
                if self.paused:
                    await asyncio.sleep(30)
                    continue
                
                for token_address, position in list(self.active_positions.items()):
                    if position.status != 'OPEN':
                        continue
                    
                    # Update current price
                    current_price = await self.solana_trader.get_token_price(token_address)
                    if current_price:
                        position.current_price = current_price
                        position.pnl_percent = ((current_price - position.entry_price) / position.entry_price) * 100
                    
                    # Check exit conditions
                    should_exit, exit_reason = self._check_exit_conditions(position)
                    
                    if should_exit:
                        await self._execute_sell_order(position, exit_reason)
                
                await asyncio.sleep(30)  # Check positions every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error monitoring positions: {e}")
                await asyncio.sleep(60)
    
    def _check_exit_conditions(self, position: Position) -> Tuple[bool, str]:
        """Check if position should be exited"""
        try:
            # Take profit condition
            if position.current_price >= position.take_profit_price:
                return True, 'TAKE_PROFIT'
            
            # Stop loss condition
            if position.current_price <= position.stop_loss_price:
                return True, 'STOP_LOSS'
            
            # Time-based exit (24 hours)
            hours_held = (datetime.now() - position.entry_timestamp).total_seconds() / 3600
            if hours_held >= 24:
                return True, 'TIME_LIMIT'
            
            return False, ''
            
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {e}")
            return False, ''
    
    async def _execute_sell_order(self, position: Position, exit_reason: str):
        """Execute a sell order for a position"""
        try:
            # Determine sell percentage
            if exit_reason == 'TAKE_PROFIT':
                # Sell most but keep moonbag
                sell_percentage = 1.0 - trading_config.moonbag_percentage
            else:
                # Sell everything
                sell_percentage = 1.0
            
            tokens_to_sell = position.tokens_held * sell_percentage
            
            # Execute sell order
            result = await self.solana_trader.sell_token(
                token_address=position.token_address,
                amount_tokens=tokens_to_sell,
                slippage=trading_config.sell_slippage
            )
            
            if result['success']:
                # Update position
                sol_received = result['sol_received']
                pnl_sol = sol_received - (position.amount_sol * sell_percentage)
                pnl_percent = (pnl_sol / (position.amount_sol * sell_percentage)) * 100
                
                if sell_percentage == 1.0:
                    position.status = 'CLOSED'
                    del self.active_positions[position.token_address]
                else:
                    position.status = 'PARTIAL_CLOSE'
                    position.tokens_held *= trading_config.moonbag_percentage
                    position.amount_sol *= trading_config.moonbag_percentage
                
                # Update statistics
                self.stats['positions_closed'] += 1
                self.stats['total_pnl'] += pnl_sol
                
                # Save updated position
                await self.db_manager.update_position(position)
                
                # Send notification
                await self.notification_manager.send_notification(
                    f"💰 Position {'Closed' if sell_percentage == 1.0 else 'Partially Closed'}\\n"
                    f"Token: {position.symbol}\\n"
                    f"Reason: {exit_reason}\\n"
                    f"PnL: {pnl_percent:.2f}% ({pnl_sol:.4f} SOL)\\n"
                    f"Exit Price: ${position.current_price:.8f}"
                )
                
                self.logger.info(f"Position {'closed' if sell_percentage == 1.0 else 'partially closed'} for {position.symbol}: {pnl_percent:.2f}% PnL")
            
            else:
                self.logger.error(f"Failed to sell {position.symbol}: {result['error']}")
                
        except Exception as e:
            self.logger.error(f"Error executing sell order: {e}")
    
    async def _update_statistics(self):
        """Update bot statistics"""
        while self.running:
            try:
                # Calculate win rate
                closed_positions = await self.db_manager.get_closed_positions()
                if closed_positions:
                    winning_positions = [p for p in closed_positions if p.pnl_percent > 0]
                    self.stats['win_rate'] = len(winning_positions) / len(closed_positions) * 100
                
                # Save statistics
                await self.db_manager.save_statistics(self.stats)
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error updating statistics: {e}")
                await asyncio.sleep(300)
    
    async def _load_existing_positions(self):
        """Load existing positions from database"""
        try:
            positions = await self.db_manager.get_open_positions()
            for position in positions:
                self.active_positions[position.token_address] = position
            
            self.logger.info(f"Loaded {len(positions)} existing positions")
            
        except Exception as e:
            self.logger.error(f"Error loading existing positions: {e}")
    
    def _save_state(self):
        """Save current state to database"""
        try:
            # Save will be handled by individual methods
            self.logger.info("State saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        return {
            'running': self.running,
            'paused': self.paused,
            'uptime': str(datetime.now() - self.stats['start_time']) if self.stats['start_time'] else '0:00:00',
            'statistics': self.stats,
            'active_positions': len(self.active_positions),
            'queue_sizes': {
                'discovery': self.discovery_queue.qsize(),
                'analysis': self.analysis_queue.qsize(),
                'trading': self.trading_queue.qsize()
            }
        }
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        return [asdict(position) for position in self.active_positions.values()]
    
    def get_recent_discoveries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent token discoveries"""
        discoveries = sorted(
            self.discovered_tokens.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        return [asdict(d) for d in discoveries[:limit]]

# Main execution
async def main():
    """Main execution function"""
    bot = SolanaMemecoinBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        bot.logger.info("Received keyboard interrupt")
    except Exception as e:
        bot.logger.error(f"Unexpected error: {e}")
    finally:
        bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
