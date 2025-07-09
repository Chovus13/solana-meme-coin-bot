"""
Telegram monitoring module using Telethon for discovering memecoin mentions
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import json

class TelegramMonitor:
    """Monitor Telegram channels and groups for memecoin-related content"""
    
    def __init__(self, api_keys):
        """Initialize Telegram monitor with API credentials"""
        self.logger = logging.getLogger(__name__)
        self.api_keys = api_keys
        
        # Initialize Telegram client
        if api_keys.telegram_api_id and api_keys.telegram_api_hash:
            self.client = TelegramClient(
                'memecoin_bot_session',
                api_keys.telegram_api_id,
                api_keys.telegram_api_hash
            )
            self.authenticated = False
        else:
            self.client = None
            self.logger.warning("No Telegram API credentials provided")
        
        # Compiled regex patterns
        self.contract_pattern = re.compile(r'[A-HJ-NP-Z1-9]{32,44}')
        self.ticker_pattern = re.compile(r'\\$([A-Z]{2,10})\\b')
        self.ca_pattern = re.compile(r'CA:?\\s*([A-HJ-NP-Z1-9]{32,44})')
        
        # Track processed messages
        self.processed_messages = set()
        
        # Monitoring state
        self.is_monitoring = False
        self.monitored_channels = set()
        self.message_callback = None
    
    async def authenticate(self) -> bool:
        """Authenticate with Telegram"""
        if not self.client:
            return False
        
        try:
            await self.client.start(phone=self.api_keys.telegram_phone)
            
            if not await self.client.is_user_authorized():
                self.logger.error("Telegram authentication failed")
                return False
            
            self.authenticated = True
            self.logger.info("Telegram authentication successful")
            return True
            
        except SessionPasswordNeededError:
            self.logger.error("Two-factor authentication enabled. Please disable or provide password.")
            return False
        except Exception as e:
            self.logger.error(f"Error authenticating with Telegram: {e}")
            return False
    
    async def get_channel_messages(self, channel_usernames: List[str], keywords: List[str], 
                                 hours_back: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent messages from specified channels"""
        if not self.client or not self.authenticated:
            return []
        
        messages = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        for channel_username in channel_usernames:
            try:
                # Get channel entity
                entity = await self.client.get_entity(channel_username)
                
                # Get messages
                channel_messages = []
                async for message in self.client.iter_messages(entity, limit=limit):
                    if message.date < cutoff_time:
                        break
                    
                    if message.text and self._contains_keywords(message.text, keywords):
                        processed_message = await self._process_telegram_message(message, entity)
                        if processed_message:
                            channel_messages.append(processed_message)
                
                messages.extend(channel_messages)
                self.logger.info(f"Found {len(channel_messages)} messages in {channel_username}")
                
            except FloodWaitError as e:
                self.logger.warning(f"Rate limited for {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                self.logger.error(f"Error getting messages from {channel_username}: {e}")
                continue
        
        self.logger.info(f"Total Telegram messages found: {len(messages)}")
        return messages
    
    async def search_channels(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for Telegram channels"""
        if not self.client or not self.authenticated:
            return []
        
        try:
            # Search for channels
            results = await self.client.get_dialogs(limit=limit)
            matching_channels = []
            
            for dialog in results:
                if isinstance(dialog.entity, Channel):
                    if query.lower() in dialog.title.lower():
                        channel_info = {
                            'id': dialog.entity.id,
                            'title': dialog.title,
                            'username': dialog.entity.username,
                            'participants_count': getattr(dialog.entity, 'participants_count', 0),
                            'description': getattr(dialog.entity, 'about', ''),
                            'is_megagroup': getattr(dialog.entity, 'megagroup', False)
                        }
                        matching_channels.append(channel_info)
            
            return matching_channels
            
        except Exception as e:
            self.logger.error(f"Error searching channels: {e}")
            return []
    
    async def join_channel(self, channel_username: str) -> bool:
        """Join a Telegram channel"""
        if not self.client or not self.authenticated:
            return False
        
        try:
            # Join channel
            await self.client(JoinChannelRequest(channel_username))
            self.logger.info(f"Joined channel: {channel_username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error joining channel {channel_username}: {e}")
            return False
    
    async def get_channel_info(self, channel_username: str) -> Dict[str, Any]:
        """Get information about a Telegram channel"""
        if not self.client or not self.authenticated:
            return {}
        
        try:
            entity = await self.client.get_entity(channel_username)
            
            if isinstance(entity, Channel):
                return {
                    'id': entity.id,
                    'title': entity.title,
                    'username': entity.username,
                    'participants_count': getattr(entity, 'participants_count', 0),
                    'description': getattr(entity, 'about', ''),
                    'is_megagroup': getattr(entity, 'megagroup', False),
                    'created_date': entity.date.isoformat() if entity.date else None,
                    'verified': getattr(entity, 'verified', False)
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error getting channel info for {channel_username}: {e}")
            return {}
    
    async def monitor_channels_realtime(self, channel_usernames: List[str], keywords: List[str], callback):
        """Monitor channels in real-time for new messages"""
        if not self.client or not self.authenticated:
            return
        
        self.monitored_channels = set(channel_usernames)
        self.message_callback = callback
        self.is_monitoring = True
        
        # Add event handler for new messages
        @self.client.on(events.NewMessage)
        async def handle_new_message(event):
            try:
                if not self.is_monitoring:
                    return
                
                # Check if message is from a monitored channel
                if hasattr(event.chat, 'username') and event.chat.username in self.monitored_channels:
                    if event.text and self._contains_keywords(event.text, keywords):
                        processed_message = await self._process_telegram_message(event.message, event.chat)
                        if processed_message and self.message_callback:
                            await self.message_callback(processed_message, 'telegram')
            
            except Exception as e:
                self.logger.error(f"Error handling new Telegram message: {e}")
        
        try:
            self.logger.info(f"Started real-time monitoring of {len(channel_usernames)} Telegram channels")
            await self.client.run_until_disconnected()
        except Exception as e:
            self.logger.error(f"Error in real-time Telegram monitoring: {e}")
    
    async def get_user_messages(self, username: str, keywords: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages from a specific user"""
        if not self.client or not self.authenticated:
            return []
        
        try:
            entity = await self.client.get_entity(username)
            messages = []
            
            # Get user's messages from their chat
            async for message in self.client.iter_messages(entity, limit=limit):
                if message.text and self._contains_keywords(message.text, keywords):
                    processed_message = await self._process_telegram_message(message, entity)
                    if processed_message:
                        messages.append(processed_message)
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Error getting messages from user {username}: {e}")
            return []
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the specified keywords"""
        if not text:
            return False
        
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    async def _process_telegram_message(self, message, entity) -> Optional[Dict[str, Any]]:
        """Process a Telegram message and extract relevant information"""
        try:
            message_id = str(message.id)
            
            # Skip if already processed
            if message_id in self.processed_messages:
                return None
            
            self.processed_messages.add(message_id)
            
            # Get message text
            text = message.text or ""
            
            # Extract token information
            contract_addresses = self.contract_pattern.findall(text)
            ticker_symbols = self.ticker_pattern.findall(text.upper())
            ca_addresses = self.ca_pattern.findall(text)
            
            # Combine contract addresses
            all_contracts = list(set(contract_addresses + ca_addresses))
            
            # Calculate engagement score
            engagement_score = self._calculate_engagement_score(message)
            
            # Determine if this is memecoin-related
            is_memecoin_related = self._is_memecoin_related(text)
            
            # Get message age
            age_hours = (datetime.utcnow() - message.date).total_seconds() / 3600
            
            # Get sender info
            sender_info = {}
            if message.sender:
                if isinstance(message.sender, User):
                    sender_info = {
                        'id': message.sender.id,
                        'username': message.sender.username,
                        'first_name': message.sender.first_name,
                        'last_name': message.sender.last_name,
                        'is_bot': message.sender.bot,
                        'is_verified': getattr(message.sender, 'verified', False)
                    }
            
            # Get channel info
            channel_info = {}
            if isinstance(entity, Channel):
                channel_info = {
                    'id': entity.id,
                    'title': entity.title,
                    'username': entity.username,
                    'is_megagroup': getattr(entity, 'megagroup', False)
                }
            elif isinstance(entity, Chat):
                channel_info = {
                    'id': entity.id,
                    'title': entity.title,
                    'is_group': True
                }
            
            # Get forwarded info
            forward_info = {}
            if message.forward:
                forward_info = {
                    'from_id': message.forward.from_id,
                    'from_name': message.forward.from_name,
                    'date': message.forward.date.isoformat() if message.forward.date else None
                }
            
            processed_message = {
                'id': message_id,
                'text': text,
                'content': text,  # Alias for compatibility
                'author': sender_info.get('username', sender_info.get('first_name', 'unknown')),
                'sender_info': sender_info,
                'channel_info': channel_info,
                'forward_info': forward_info,
                'created_at': message.date.isoformat(),
                'url': self._get_message_url(entity, message),
                'contract_addresses': all_contracts,
                'ticker_symbols': ticker_symbols,
                'engagement_score': engagement_score,
                'is_memecoin_related': is_memecoin_related,
                'age_hours': age_hours,
                'has_media': bool(message.media),
                'views': getattr(message, 'views', 0),
                'replies': getattr(message, 'replies', {}).get('replies', 0) if getattr(message, 'replies', None) else 0,
                'type': 'telegram_message'
            }
            
            return processed_message
            
        except Exception as e:
            self.logger.error(f"Error processing Telegram message: {e}")
            return None
    
    def _calculate_engagement_score(self, message) -> float:
        """Calculate engagement score for a Telegram message"""
        try:
            score = 0.0
            
            # Views count
            views = getattr(message, 'views', 0)
            if views > 0:
                import math
                score += math.log(views + 1) / 10
            
            # Replies count
            replies = getattr(message, 'replies', {})
            if replies and hasattr(replies, 'replies'):
                score += replies.replies * 0.1
            
            # Forward count (if available)
            forwards = getattr(message, 'forwards', 0)
            score += forwards * 0.2
            
            # Message length bonus
            text_length = len(message.text) if message.text else 0
            length_score = min(text_length / 500, 1.0)
            score += length_score * 0.3
            
            # Media bonus
            if message.media:
                score += 0.5
            
            # Normalize to 0-1 scale
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating engagement score: {e}")
            return 0.0
    
    def _is_memecoin_related(self, text: str) -> bool:
        """Determine if Telegram message is memecoin-related"""
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
            'diamond hands', 'to the moon', 'lambo', 'hodl', 'buy now',
            'early gem', 'next 100x', 'moonshot', 'rocket', '🚀', '💎'
        ]
        
        # Negative indicators
        negative_keywords = [
            'scam', 'rug', 'rugpull', 'avoid', 'warning', 'caution', 'fake',
            'honeypot', 'suspicious', 'fraud', 'dump', 'exit scam', 'beware',
            'ponzi', 'pyramid'
        ]
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
        
        # Check for contract addresses or tickers
        has_contract = bool(self.contract_pattern.search(text) or self.ca_pattern.search(text))
        has_ticker = bool(self.ticker_pattern.search(text))
        
        # Check for emojis that are commonly used in crypto
        crypto_emojis = ['🚀', '💎', '🌙', '💰', '🔥', '⚡', '🌟']
        has_crypto_emojis = any(emoji in text for emoji in crypto_emojis)
        
        # Scoring logic
        if negative_count > positive_count:
            return False
        
        if has_contract or has_ticker:
            return True
        
        if has_crypto_emojis and positive_count >= 1:
            return True
        
        return positive_count >= 2
    
    def _get_message_url(self, entity, message) -> str:
        """Generate URL for a Telegram message"""
        try:
            if isinstance(entity, Channel) and entity.username:
                return f"https://t.me/{entity.username}/{message.id}"
            else:
                return f"https://t.me/c/{entity.id}/{message.id}"
        except:
            return ""
    
    async def get_channel_members(self, channel_username: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get members of a Telegram channel (if accessible)"""
        if not self.client or not self.authenticated:
            return []
        
        try:
            entity = await self.client.get_entity(channel_username)
            members = []
            
            # This only works for small groups or if you're an admin
            async for user in self.client.iter_participants(entity, limit=limit):
                if isinstance(user, User):
                    member_info = {
                        'id': user.id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_bot': user.bot,
                        'is_verified': getattr(user, 'verified', False)
                    }
                    members.append(member_info)
            
            return members
            
        except Exception as e:
            self.logger.error(f"Error getting channel members for {channel_username}: {e}")
            return []
    
    async def search_messages_in_channel(self, channel_username: str, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for messages containing a query in a specific channel"""
        if not self.client or not self.authenticated:
            return []
        
        try:
            entity = await self.client.get_entity(channel_username)
            found_messages = []
            
            async for message in self.client.iter_messages(entity, search=query, limit=limit):
                processed_message = await self._process_telegram_message(message, entity)
                if processed_message:
                    found_messages.append(processed_message)
            
            return found_messages
            
        except Exception as e:
            self.logger.error(f"Error searching messages in {channel_username}: {e}")
            return []
    
    async def stop_monitoring(self):
        """Stop Telegram monitoring"""
        self.is_monitoring = False
        if self.client:
            await self.client.disconnect()
        self.logger.info("Telegram monitoring stopped")
    
    def is_connected(self) -> bool:
        """Check if Telegram client is connected"""
        return self.client and self.client.is_connected() if self.client else False
    
    async def get_dialogs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of user's dialogs (chats/channels)"""
        if not self.client or not self.authenticated:
            return []
        
        try:
            dialogs = await self.client.get_dialogs(limit=limit)
            dialog_list = []
            
            for dialog in dialogs:
                dialog_info = {
                    'id': dialog.entity.id,
                    'title': dialog.title,
                    'is_channel': isinstance(dialog.entity, Channel),
                    'is_group': isinstance(dialog.entity, Chat),
                    'is_user': isinstance(dialog.entity, User),
                    'unread_count': dialog.unread_count,
                    'last_message_date': dialog.date.isoformat() if dialog.date else None
                }
                
                if hasattr(dialog.entity, 'username'):
                    dialog_info['username'] = dialog.entity.username
                
                dialog_list.append(dialog_info)
            
            return dialog_list
            
        except Exception as e:
            self.logger.error(f"Error getting dialogs: {e}")
            return []
