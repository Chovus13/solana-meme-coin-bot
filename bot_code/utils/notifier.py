"""
Notification management module for sending alerts and updates
"""

import asyncio
import logging
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class NotificationLevel(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Notification:
    """Notification data structure"""
    title: str
    message: str
    level: NotificationLevel
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None

class NotificationManager:
    """Manages notifications via multiple channels"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """Initialize notification manager"""
        self.logger = logging.getLogger(__name__)
        self.webhook_url = webhook_url
        
        # Notification history
        self.notification_history = []
        self.max_history = 1000
        
        # Rate limiting
        self.last_notification_time = {}
        self.min_interval = {
            NotificationLevel.LOW: 300,      # 5 minutes
            NotificationLevel.MEDIUM: 120,   # 2 minutes
            NotificationLevel.HIGH: 60,      # 1 minute
            NotificationLevel.CRITICAL: 0    # No limit
        }
        
        # Notification channels
        self.channels = {
            'webhook': self._send_webhook_notification,
            'telegram': self._send_telegram_notification,
            'discord': self._send_discord_notification,
            'email': self._send_email_notification
        }
        
        # Channel configurations
        self.channel_configs = {}
        
        self.logger.info("Notification manager initialized")
    
    async def send_notification(self, message: str, title: str = "Trading Bot Alert", 
                              level: NotificationLevel = NotificationLevel.MEDIUM,
                              data: Optional[Dict[str, Any]] = None,
                              channels: Optional[List[str]] = None) -> bool:
        """Send notification via specified channels"""
        try:
            notification = Notification(
                title=title,
                message=message,
                level=level,
                timestamp=datetime.now(),
                data=data
            )
            
            # Check rate limiting
            if not self._check_rate_limit(level):
                self.logger.debug(f"Rate limited notification: {title}")
                return False
            
            # Default to webhook if no channels specified
            if not channels:
                channels = ['webhook'] if self.webhook_url else []
            
            # Send to all specified channels
            success = True
            for channel in channels:
                if channel in self.channels:
                    try:
                        await self.channels[channel](notification)
                    except Exception as e:
                        self.logger.error(f"Error sending to {channel}: {e}")
                        success = False
                else:
                    self.logger.warning(f"Unknown notification channel: {channel}")
            
            # Store in history
            self._store_notification(notification)
            
            return success
        
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False
    
    async def send_trade_alert(self, trade_type: str, symbol: str, amount: float, 
                             price: float, pnl: Optional[float] = None,
                             level: NotificationLevel = NotificationLevel.HIGH) -> bool:
        """Send trading-specific alert"""
        try:
            emoji_map = {
                'BUY': '🟢',
                'SELL': '🔴',
                'PARTIAL_SELL': '🟡'
            }
            
            emoji = emoji_map.get(trade_type.upper(), '⚪')
            
            if trade_type.upper() == 'BUY':
                title = f"{emoji} Position Opened"
                message = (
                    f"**Token:** {symbol}\n"
                    f"**Action:** {trade_type}\n"
                    f"**Amount:** {amount} SOL\n"
                    f"**Price:** ${price:.8f}\n"
                    f"**Time:** {datetime.now().strftime('%H:%M:%S')}"
                )
            else:
                pnl_text = f"\n**PnL:** {pnl:+.2f}%" if pnl is not None else ""
                title = f"{emoji} Position {'Closed' if trade_type.upper() == 'SELL' else 'Partially Closed'}"
                message = (
                    f"**Token:** {symbol}\n"
                    f"**Action:** {trade_type}\n"
                    f"**Price:** ${price:.8f}{pnl_text}\n"
                    f"**Time:** {datetime.now().strftime('%H:%M:%S')}"
                )
            
            return await self.send_notification(
                message=message,
                title=title,
                level=level,
                data={
                    'type': 'trade_alert',
                    'trade_type': trade_type,
                    'symbol': symbol,
                    'amount': amount,
                    'price': price,
                    'pnl': pnl
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error sending trade alert: {e}")
            return False
    
    async def send_discovery_alert(self, symbol: str, contract_address: str, 
                                 source: str, confidence: float,
                                 level: NotificationLevel = NotificationLevel.MEDIUM) -> bool:
        """Send token discovery alert"""
        try:
            title = "🔍 New Token Discovered"
            message = (
                f"**Symbol:** {symbol}\n"
                f"**Source:** {source.title()}\n"
                f"**Confidence:** {confidence:.1%}\n"
                f"**Contract:** `{contract_address}`\n"
                f"**Time:** {datetime.now().strftime('%H:%M:%S')}"
            )
            
            return await self.send_notification(
                message=message,
                title=title,
                level=level,
                data={
                    'type': 'discovery_alert',
                    'symbol': symbol,
                    'contract_address': contract_address,
                    'source': source,
                    'confidence': confidence
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error sending discovery alert: {e}")
            return False
    
    async def send_analysis_alert(self, symbol: str, safety_score: int, 
                                recommendation: str, ai_prediction: float,
                                level: NotificationLevel = NotificationLevel.MEDIUM) -> bool:
        """Send token analysis alert"""
        try:
            # Determine emoji based on recommendation
            emoji_map = {
                'BUY': '🚀',
                'MONITOR': '👀',
                'PASS': '⏭️'
            }
            
            emoji = emoji_map.get(recommendation, '📊')
            
            title = f"{emoji} Analysis Complete"
            message = (
                f"**Token:** {symbol}\n"
                f"**Safety Score:** {safety_score}/100\n"
                f"**AI Prediction:** {ai_prediction:.1%}\n"
                f"**Recommendation:** {recommendation}\n"
                f"**Time:** {datetime.now().strftime('%H:%M:%S')}"
            )
            
            return await self.send_notification(
                message=message,
                title=title,
                level=level,
                data={
                    'type': 'analysis_alert',
                    'symbol': symbol,
                    'safety_score': safety_score,
                    'recommendation': recommendation,
                    'ai_prediction': ai_prediction
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error sending analysis alert: {e}")
            return False
    
    async def send_error_alert(self, error_type: str, error_message: str,
                             level: NotificationLevel = NotificationLevel.HIGH) -> bool:
        """Send error alert"""
        try:
            title = "❌ Bot Error"
            message = (
                f"**Error Type:** {error_type}\n"
                f"**Message:** {error_message}\n"
                f"**Time:** {datetime.now().strftime('%H:%M:%S')}"
            )
            
            return await self.send_notification(
                message=message,
                title=title,
                level=level,
                data={
                    'type': 'error_alert',
                    'error_type': error_type,
                    'error_message': error_message
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error sending error alert: {e}")
            return False
    
    async def send_status_update(self, stats: Dict[str, Any],
                               level: NotificationLevel = NotificationLevel.LOW) -> bool:
        """Send bot status update"""
        try:
            title = "📊 Bot Status Update"
            message = (
                f"**Uptime:** {stats.get('uptime', 'Unknown')}\n"
                f"**Active Positions:** {stats.get('active_positions', 0)}\n"
                f"**Total PnL:** {stats.get('total_pnl', 0.0):+.4f} SOL\n"
                f"**Win Rate:** {stats.get('win_rate', 0.0):.1f}%\n"
                f"**Tokens Discovered:** {stats.get('tokens_discovered', 0)}\n"
                f"**Tokens Analyzed:** {stats.get('tokens_analyzed', 0)}\n"
                f"**Time:** {datetime.now().strftime('%H:%M:%S')}"
            )
            
            return await self.send_notification(
                message=message,
                title=title,
                level=level,
                data={
                    'type': 'status_update',
                    'stats': stats
                }
            )
        
        except Exception as e:
            self.logger.error(f"Error sending status update: {e}")
            return False
    
    async def _send_webhook_notification(self, notification: Notification) -> bool:
        """Send notification via webhook"""
        try:
            if not self.webhook_url:
                return False
            
            # Format for Discord webhook (can be adapted for other services)
            payload = {
                "embeds": [{
                    "title": notification.title,
                    "description": notification.message,
                    "color": self._get_color_for_level(notification.level),
                    "timestamp": notification.timestamp.isoformat(),
                    "footer": {
                        "text": "Solana Memecoin Bot"
                    }
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 204:  # Discord success
                        return True
                    else:
                        self.logger.error(f"Webhook failed: {response.status}")
                        return False
        
        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {e}")
            return False
    
    async def _send_telegram_notification(self, notification: Notification) -> bool:
        """Send notification via Telegram"""
        try:
            # This would require Telegram bot configuration
            # Placeholder implementation
            self.logger.info(f"Telegram notification: {notification.title}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error sending Telegram notification: {e}")
            return False
    
    async def _send_discord_notification(self, notification: Notification) -> bool:
        """Send notification via Discord"""
        try:
            # This would require Discord bot configuration
            # Placeholder implementation
            self.logger.info(f"Discord notification: {notification.title}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error sending Discord notification: {e}")
            return False
    
    async def _send_email_notification(self, notification: Notification) -> bool:
        """Send notification via email"""
        try:
            # This would require email configuration
            # Placeholder implementation
            self.logger.info(f"Email notification: {notification.title}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error sending email notification: {e}")
            return False
    
    def _check_rate_limit(self, level: NotificationLevel) -> bool:
        """Check if notification should be rate limited"""
        try:
            current_time = datetime.now().timestamp()
            level_key = level.value
            
            if level_key not in self.last_notification_time:
                self.last_notification_time[level_key] = current_time
                return True
            
            time_since_last = current_time - self.last_notification_time[level_key]
            min_interval = self.min_interval[level]
            
            if time_since_last >= min_interval:
                self.last_notification_time[level_key] = current_time
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error checking rate limit: {e}")
            return True  # Allow notification on error
    
    def _get_color_for_level(self, level: NotificationLevel) -> int:
        """Get color code for notification level"""
        color_map = {
            NotificationLevel.LOW: 0x808080,      # Gray
            NotificationLevel.MEDIUM: 0x0099ff,   # Blue
            NotificationLevel.HIGH: 0xff9900,     # Orange
            NotificationLevel.CRITICAL: 0xff0000  # Red
        }
        return color_map.get(level, 0x808080)
    
    def _store_notification(self, notification: Notification):
        """Store notification in history"""
        try:
            self.notification_history.append(notification)
            
            # Keep only the most recent notifications
            if len(self.notification_history) > self.max_history:
                self.notification_history = self.notification_history[-self.max_history:]
        
        except Exception as e:
            self.logger.error(f"Error storing notification: {e}")
    
    def get_notification_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent notification history"""
        try:
            recent_notifications = self.notification_history[-limit:]
            
            return [
                {
                    'title': notif.title,
                    'message': notif.message,
                    'level': notif.level.value,
                    'timestamp': notif.timestamp.isoformat(),
                    'data': notif.data
                }
                for notif in recent_notifications
            ]
        
        except Exception as e:
            self.logger.error(f"Error getting notification history: {e}")
            return []
    
    def configure_channel(self, channel: str, config: Dict[str, Any]):
        """Configure a notification channel"""
        try:
            self.channel_configs[channel] = config
            self.logger.info(f"Configured notification channel: {channel}")
        
        except Exception as e:
            self.logger.error(f"Error configuring channel {channel}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        try:
            total_notifications = len(self.notification_history)
            
            # Count by level
            level_counts = {}
            for notif in self.notification_history:
                level = notif.level.value
                level_counts[level] = level_counts.get(level, 0) + 1
            
            # Count by type
            type_counts = {}
            for notif in self.notification_history:
                if notif.data and 'type' in notif.data:
                    notif_type = notif.data['type']
                    type_counts[notif_type] = type_counts.get(notif_type, 0) + 1
            
            return {
                'total_notifications': total_notifications,
                'level_distribution': level_counts,
                'type_distribution': type_counts,
                'configured_channels': list(self.channel_configs.keys()),
                'webhook_configured': bool(self.webhook_url)
            }
        
        except Exception as e:
            self.logger.error(f"Error getting notification stats: {e}")
            return {}
