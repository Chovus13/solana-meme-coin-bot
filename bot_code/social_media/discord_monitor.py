"""
Discord monitoring module for discovering memecoin mentions in servers and channels
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
import discord
from discord.ext import commands
import json

class DiscordMonitor:
    """Monitor Discord servers and channels for memecoin-related content"""
    
    def __init__(self, api_keys):
        """Initialize Discord monitor with bot token"""
        self.logger = logging.getLogger(__name__)
        self.api_keys = api_keys
        
        # Discord bot setup
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        if api_keys.discord_token:
            self.bot = commands.Bot(command_prefix='!', intents=intents)
            self.setup_bot_events()
        else:
            self.bot = None
            self.logger.warning("No Discord token provided")
        
        # Compiled regex patterns
        self.contract_pattern = re.compile(r'[A-HJ-NP-Z1-9]{32,44}')
        self.ticker_pattern = re.compile(r'\\$([A-Z]{2,10})\\b')
        self.ca_pattern = re.compile(r'CA:?\\s*([A-HJ-NP-Z1-9]{32,44})')
        
        # Track processed messages
        self.processed_messages = set()
        
        # Callback for processing messages
        self.message_callback = None
        
        # Monitoring configuration
        self.monitored_channels = set()
        self.keywords = []
        
        # Running state
        self.is_running = False
    
    def setup_bot_events(self):
        """Setup Discord bot event handlers"""
        
        @self.bot.event
        async def on_ready():
            self.logger.info(f'Discord bot logged in as {self.bot.user}')
            self.is_running = True
        
        @self.bot.event
        async def on_message(message):
            # Don't process our own messages
            if message.author == self.bot.user:
                return
            
            # Process message if it's from a monitored channel
            if self.message_callback and message.channel.id in self.monitored_channels:
                await self._process_message(message)
            
            # Process commands
            await self.bot.process_commands(message)
        
        @self.bot.event
        async def on_error(event, *args, **kwargs):
            self.logger.error(f'Discord bot error in {event}: {args}')
    
    async def start_monitoring(self, channel_ids: List[int], keywords: List[str], callback: Callable):
        """Start monitoring specified Discord channels"""
        if not self.bot:
            self.logger.error("No Discord bot available")
            return False
        
        self.monitored_channels = set(channel_ids)
        self.keywords = keywords
        self.message_callback = callback
        
        try:
            # Start the bot
            await self.bot.start(self.api_keys.discord_token)
        except Exception as e:
            self.logger.error(f"Error starting Discord bot: {e}")
            return False
        
        return True
    
    async def get_recent_messages(self, channel_ids: List[int], keywords: List[str], hours_back: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent messages from specified channels"""
        if not self.bot or not self.bot.is_ready():
            return []
        
        recent_messages = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        for channel_id in channel_ids:
            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    self.logger.warning(f"Could not find channel {channel_id}")
                    continue
                
                message_count = 0
                async for message in channel.history(limit=limit, after=cutoff_time):
                    if message_count >= limit:
                        break
                    
                    if self._contains_keywords(message.content, keywords):
                        processed_message = await self._process_discord_message(message)
                        if processed_message:
                            recent_messages.append(processed_message)
                    
                    message_count += 1
                
            except discord.Forbidden:
                self.logger.warning(f"No permission to read channel {channel_id}")
            except Exception as e:
                self.logger.error(f"Error getting messages from channel {channel_id}: {e}")
        
        self.logger.info(f"Found {len(recent_messages)} relevant Discord messages")
        return recent_messages
    
    async def search_guild_messages(self, guild_id: int, keywords: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Search for messages across all channels in a guild"""
        if not self.bot or not self.bot.is_ready():
            return []
        
        found_messages = []
        
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                self.logger.warning(f"Could not find guild {guild_id}")
                return []
            
            for channel in guild.text_channels:
                try:
                    if not channel.permissions_for(guild.me).read_messages:
                        continue
                    
                    message_count = 0
                    async for message in channel.history(limit=limit):
                        if message_count >= limit:
                            break
                        
                        if self._contains_keywords(message.content, keywords):
                            processed_message = await self._process_discord_message(message)
                            if processed_message:
                                found_messages.append(processed_message)
                        
                        message_count += 1
                
                except discord.Forbidden:
                    continue
                except Exception as e:
                    self.logger.error(f"Error searching channel {channel.name}: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error searching guild {guild_id}: {e}")
        
        return found_messages
    
    async def get_channel_info(self, channel_id: int) -> Dict[str, Any]:
        """Get information about a Discord channel"""
        if not self.bot or not self.bot.is_ready():
            return {}
        
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return {}
            
            return {
                'id': channel.id,
                'name': channel.name,
                'type': str(channel.type),
                'guild_name': channel.guild.name if channel.guild else None,
                'guild_id': channel.guild.id if channel.guild else None,
                'member_count': channel.guild.member_count if channel.guild else None,
                'created_at': channel.created_at.isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"Error getting channel info for {channel_id}: {e}")
            return {}
    
    async def monitor_user_messages(self, user_id: int, keywords: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Monitor messages from a specific user across accessible channels"""
        if not self.bot or not self.bot.is_ready():
            return []
        
        user_messages = []
        
        try:
            user = self.bot.get_user(user_id)
            if not user:
                return []
            
            # Check all guilds the bot is in
            for guild in self.bot.guilds:
                member = guild.get_member(user_id)
                if not member:
                    continue
                
                for channel in guild.text_channels:
                    try:
                        if not channel.permissions_for(guild.me).read_messages:
                            continue
                        
                        message_count = 0
                        async for message in channel.history(limit=limit):
                            if message_count >= limit:
                                break
                            
                            if message.author.id == user_id and self._contains_keywords(message.content, keywords):
                                processed_message = await self._process_discord_message(message)
                                if processed_message:
                                    user_messages.append(processed_message)
                            
                            message_count += 1
                    
                    except discord.Forbidden:
                        continue
                    except Exception as e:
                        continue
        
        except Exception as e:
            self.logger.error(f"Error monitoring user {user_id}: {e}")
        
        return user_messages
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the specified keywords"""
        if not text:
            return False
        
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    async def _process_message(self, message):
        """Process a Discord message from event handler"""
        try:
            if self._contains_keywords(message.content, self.keywords):
                processed_message = await self._process_discord_message(message)
                if processed_message and self.message_callback:
                    await self.message_callback(processed_message, 'discord')
        
        except Exception as e:
            self.logger.error(f"Error processing Discord message: {e}")
    
    async def _process_discord_message(self, message) -> Optional[Dict[str, Any]]:
        """Process a Discord message and extract relevant information"""
        try:
            message_id = str(message.id)
            
            # Skip if already processed
            if message_id in self.processed_messages:
                return None
            
            self.processed_messages.add(message_id)
            
            # Extract token information
            content = message.content
            contract_addresses = self.contract_pattern.findall(content)
            ticker_symbols = self.ticker_pattern.findall(content.upper())
            ca_addresses = self.ca_pattern.findall(content)
            
            # Combine contract addresses
            all_contracts = list(set(contract_addresses + ca_addresses))
            
            # Calculate engagement score
            engagement_score = self._calculate_engagement_score(message)
            
            # Determine if this is memecoin-related
            is_memecoin_related = self._is_memecoin_related(content)
            
            # Get message age
            age_hours = (datetime.utcnow() - message.created_at).total_seconds() / 3600
            
            # Get channel and guild info
            channel_info = {
                'id': message.channel.id,
                'name': message.channel.name,
                'type': str(message.channel.type)
            }
            
            guild_info = {}
            if message.guild:
                guild_info = {
                    'id': message.guild.id,
                    'name': message.guild.name,
                    'member_count': message.guild.member_count
                }
            
            # Get user info
            user_info = {
                'id': message.author.id,
                'username': message.author.name,
                'discriminator': message.author.discriminator,
                'display_name': message.author.display_name,
                'bot': message.author.bot
            }
            
            processed_message = {
                'id': message_id,
                'content': content,
                'text': content,  # Alias for compatibility
                'author': message.author.name,
                'user_info': user_info,
                'channel_info': channel_info,
                'guild_info': guild_info,
                'created_at': message.created_at.isoformat(),
                'url': message.jump_url,
                'contract_addresses': all_contracts,
                'ticker_symbols': ticker_symbols,
                'engagement_score': engagement_score,
                'is_memecoin_related': is_memecoin_related,
                'age_hours': age_hours,
                'has_attachments': len(message.attachments) > 0,
                'has_embeds': len(message.embeds) > 0,
                'mentions': [mention.name for mention in message.mentions],
                'type': 'discord_message'
            }
            
            return processed_message
            
        except Exception as e:
            self.logger.error(f"Error processing Discord message: {e}")
            return None
    
    def _calculate_engagement_score(self, message) -> float:
        """Calculate engagement score for a Discord message"""
        try:
            # Discord doesn't have public like/reaction counts in the same way
            # We'll use available metrics
            
            score = 0.0
            
            # Reactions count
            if message.reactions:
                total_reactions = sum(reaction.count for reaction in message.reactions)
                score += total_reactions * 0.5
            
            # Mentions count
            score += len(message.mentions) * 0.2
            
            # Message length (longer messages might be more informative)
            content_length = len(message.content)
            length_score = min(content_length / 500, 1.0)  # Normalize to max 500 chars
            score += length_score * 0.3
            
            # Attachments/embeds bonus
            if message.attachments or message.embeds:
                score += 0.5
            
            # Normalize to 0-1 scale
            import math
            normalized = math.log(max(score + 1, 1)) / 5
            
            return min(normalized, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating engagement score: {e}")
            return 0.0
    
    def _is_memecoin_related(self, text: str) -> bool:
        """Determine if Discord message is memecoin-related"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Positive indicators
        positive_keywords = [
            'pump', 'moon', 'gem', 'new token', 'just launched', 'fair launch',
            'presale', 'memecoin', 'meme coin', 'altcoin', 'defi', 'dex',
            'raydium', 'jupiter', 'pumpfun', 'pump.fun', 'solana', 'sol',
            'contract', 'ca:', 'ticker', 'symbol', 'address', 'stealth launch',
            'dev doxxed', 'liquidity locked', 'renounced', 'safu', 'ape in',
            'diamond hands', 'to the moon', 'lambo', 'hodl'
        ]
        
        # Negative indicators
        negative_keywords = [
            'scam', 'rug', 'rugpull', 'avoid', 'warning', 'caution', 'fake',
            'honeypot', 'suspicious', 'fraud', 'dump', 'exit scam', 'beware'
        ]
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
        
        # Check for contract addresses or tickers
        has_contract = bool(self.contract_pattern.search(text) or self.ca_pattern.search(text))
        has_ticker = bool(self.ticker_pattern.search(text))
        
        # Scoring logic
        if negative_count > positive_count:
            return False
        
        if has_contract or has_ticker:
            return True
        
        return positive_count >= 2
    
    async def get_guild_channels(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get list of text channels in a guild"""
        if not self.bot or not self.bot.is_ready():
            return []
        
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return []
            
            channels = []
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).read_messages:
                    channels.append({
                        'id': channel.id,
                        'name': channel.name,
                        'topic': channel.topic,
                        'position': channel.position,
                        'category': channel.category.name if channel.category else None
                    })
            
            return channels
            
        except Exception as e:
            self.logger.error(f"Error getting guild channels for {guild_id}: {e}")
            return []
    
    async def join_guild(self, invite_link: str) -> bool:
        """Join a guild using an invite link"""
        if not self.bot or not self.bot.is_ready():
            return False
        
        try:
            invite = await self.bot.fetch_invite(invite_link)
            await invite.accept()
            self.logger.info(f"Joined guild: {invite.guild.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error joining guild with invite {invite_link}: {e}")
            return False
    
    async def search_messages_in_channel(self, channel_id: int, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for messages containing a query in a specific channel"""
        if not self.bot or not self.bot.is_ready():
            return []
        
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return []
            
            found_messages = []
            message_count = 0
            
            async for message in channel.history(limit=limit):
                if message_count >= limit:
                    break
                
                if query.lower() in message.content.lower():
                    processed_message = await self._process_discord_message(message)
                    if processed_message:
                        found_messages.append(processed_message)
                
                message_count += 1
            
            return found_messages
            
        except Exception as e:
            self.logger.error(f"Error searching messages in channel {channel_id}: {e}")
            return []
    
    async def stop_monitoring(self):
        """Stop Discord monitoring"""
        if self.bot and self.is_running:
            await self.bot.close()
            self.is_running = False
            self.logger.info("Discord monitoring stopped")
    
    def is_connected(self) -> bool:
        """Check if Discord bot is connected"""
        return self.bot and self.bot.is_ready() if self.bot else False
    
    async def get_bot_guilds(self) -> List[Dict[str, Any]]:
        """Get list of guilds the bot is in"""
        if not self.bot or not self.bot.is_ready():
            return []
        
        guilds = []
        for guild in self.bot.guilds:
            guilds.append({
                'id': guild.id,
                'name': guild.name,
                'member_count': guild.member_count,
                'created_at': guild.created_at.isoformat(),
                'owner_id': guild.owner_id
            })
        
        return guilds
