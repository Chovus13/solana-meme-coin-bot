"""
Web interface for monitoring and controlling the Solana Memecoin Trading Bot
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import threading
import os

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

# Custom JSON encoder for datetime objects
class DateTimeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Import bot components
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import web_config, validate_config, api_keys, trading_config, monitoring_config, filter_config # Import individual config objects
from solana_memecoin_bot import SolanaMemecoinBot
from utils.logger import setup_logger

class WebInterface:
    """Web interface for the trading bot"""
    
    def __init__(self, bot_instance: SolanaMemecoinBot = None):
        """Initialize web interface"""
        self.logger = setup_logger("WebInterface")
        
        # Flask app setup
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = web_config['secret_key']
        self.app.json_encoder = DateTimeJSONEncoder
        
        # Enable CORS
        CORS(self.app)
        
        # SocketIO setup with custom JSON encoder
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            async_mode='threading',
            json=json  # Use standard json module with our custom encoder
        )
        
        # Bot reference
        self.bot = bot_instance
        
        # Web interface state
        self.connected_clients = set()
        self.last_update = datetime.now()
        
        # Real-time data
        self.live_data = {
            'bot_status': 'stopped',
            'statistics': {},
            'positions': [],
            'recent_discoveries': [],
            'recent_trades': [],
            'system_metrics': {}
        }
        
        # Setup routes and socket events
        self._setup_routes()
        self._setup_socket_events()
        
        # Start background tasks
        self._start_background_tasks()
        
        self.logger.info("Web interface initialized")
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard"""
            return render_template('dashboard.html')
        
        @self.app.route('/positions')
        def positions():
            """Positions page"""
            return render_template('positions.html')
        
        @self.app.route('/discoveries')
        def discoveries():
            """Token discoveries page"""
            return render_template('discoveries.html')
        
        @self.app.route('/analytics')
        def analytics():
            """Analytics page"""
            return render_template('analytics.html')
        
        @self.app.route('/settings')
        def settings():
            """Settings page"""
            return render_template('settings.html')
        
        @self.app.route('/api/status')
        def api_status():
            """Get bot status"""
            if self.bot:
                status = self.bot.get_status()
            else:
                status = {'running': False, 'message': 'Bot not initialized'}
            
            return jsonify(status)
        
        @self.app.route('/api/positions')
        def api_positions():
            """Get current positions"""
            if self.bot:
                positions = self.bot.get_positions()
            else:
                positions = []
            
            return jsonify(positions)
        
        @self.app.route('/api/discoveries')
        def api_discoveries():
            """Get recent discoveries"""
            limit = request.args.get('limit', 50, type=int)
            
            if self.bot:
                discoveries = self.bot.get_recent_discoveries(limit)
            else:
                discoveries = []
            
            return jsonify(discoveries)
        
        @self.app.route('/api/statistics')
        def api_statistics():
            """Get bot statistics"""
            if self.bot:
                stats = self.bot.stats
            else:
                stats = {}
            
            return jsonify(stats)
        
        @self.app.route('/api/control/<action>', methods=['POST'])
        def api_control(action):
            """Control bot operations"""
            if not self.bot:
                return jsonify({'success': False, 'error': 'Bot not initialized'}), 400
            
            try:
                if action == 'start':
                    # Start bot in background
                    if not self.bot.running:
                        threading.Thread(target=self._run_bot_async, daemon=True).start()
                        return jsonify({'success': True, 'message': 'Bot starting'})
                    else:
                        return jsonify({'success': False, 'error': 'Bot already running'})
                
                elif action == 'stop':
                    if self.bot.running:
                        self.bot.stop()
                        return jsonify({'success': True, 'message': 'Bot stopped'})
                    else:
                        return jsonify({'success': False, 'error': 'Bot not running'})
                
                elif action == 'pause':
                    if self.bot.running and not self.bot.paused:
                        self.bot.pause()
                        return jsonify({'success': True, 'message': 'Bot paused'})
                    else:
                        return jsonify({'success': False, 'error': 'Bot not running or already paused'})
                
                elif action == 'resume':
                    if self.bot.running and self.bot.paused:
                        self.bot.resume()
                        return jsonify({'success': True, 'message': 'Bot resumed'})
                    else:
                        return jsonify({'success': False, 'error': 'Bot not paused'})
                
                else:
                    return jsonify({'success': False, 'error': f'Unknown action: {action}'}), 400
            
            except Exception as e:
                self.logger.error(f"Error controlling bot: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/config', methods=['GET', 'POST'])
        def api_config():
            """Get or update configuration"""
            if request.method == 'GET':
                # Return current config (sanitized)
                config_data = {
                    'trading': {
                        'buy_amount_sol': trading_config.buy_amount_sol,
                        'max_positions': trading_config.max_positions,
                        'position_size_percentage': trading_config.position_size_percentage,
                        'buy_slippage': trading_config.buy_slippage,
                        'sell_slippage': trading_config.sell_slippage,
                        'priority_fee_lamports': trading_config.priority_fee_lamports,
                        'take_profit_multiplier': trading_config.take_profit_multiplier,
                        'stop_loss_percentage': trading_config.stop_loss_percentage,
                        'moonbag_percentage': trading_config.moonbag_percentage,
                        'max_position_age_hours': trading_config.max_position_age_hours,
                        # 'trade_weekends': trading_config.trade_weekends, # Add if you implement in TradingConfig
                        # 'trading_start_time': trading_config.trading_start_time, # Add if you implement
                        # 'trading_end_time': trading_config.trading_end_time,     # Add if you implement
                    },
                    'filters': {
                        'min_safety_score': filter_config.min_safety_score,
                        'min_market_cap': filter_config.min_market_cap,
                        'max_market_cap': filter_config.max_market_cap,
                        'min_liquidity': filter_config.min_liquidity,
                        'require_locked_liquidity': filter_config.require_locked_liquidity,
                        'require_verified_contract': filter_config.require_verified_contract,
                        'require_disabled_mint': filter_config.require_disabled_mint,
                        'min_social_score': filter_config.min_social_score,
                        'min_mentions_count': filter_config.min_mentions_count,
                        'min_volume_24h': filter_config.min_volume_24h,
                        'max_age_hours': filter_config.max_age_hours,
                        'min_age_minutes': filter_config.min_age_minutes,
                    },
                    'monitoring': {
                        'twitter_check_interval': monitoring_config.twitter_check_interval,
                        'reddit_check_interval': monitoring_config.reddit_check_interval,
                        'discord_check_interval': monitoring_config.discord_check_interval,
                        'telegram_check_interval': monitoring_config.telegram_check_interval,
                        'tiktok_check_interval': monitoring_config.tiktok_check_interval,
                        'memecoin_keywords': monitoring_config.memecoin_keywords,
                        'exclude_keywords': monitoring_config.exclude_keywords,
                        'twitter_accounts': monitoring_config.twitter_accounts,
                        'reddit_subreddits': monitoring_config.reddit_subreddits,
                        'discord_channels': list(monitoring_config.discord_channels) if monitoring_config.discord_channels else [],
                        'telegram_channels': monitoring_config.telegram_channels,
                    },
                    'notifications': {
                        'discord_webhook': os.getenv('DISCORD_WEBHOOK_URL', ''),
                        'slack_webhook': os.getenv('SLACK_WEBHOOK_URL', ''),
                        # Add email settings if you implement them in .env and Config
                    },
                    'security': {
                        'max_daily_loss_percentage': trading_config.max_daily_loss_percentage,
                        'emergency_stop_loss_percentage': trading_config.emergency_stop_loss_percentage,
                        'emergency_stop_enabled': os.getenv('EMERGENCY_STOP_ENABLED', 'false').lower() == 'true',
                        # 'blacklisted_tokens': self.bot.config.blacklist # You'd need to add a blacklist to Config
                    }
                }
                return jsonify(config_data)

            else:  # POST request
                try:
                    new_config = request.json

                    # --- Trading Config ---
                    if 'trading' in new_config:
                        trading_data = new_config['trading']
                        for key, value in trading_data.items():
                            if hasattr(trading_config, key):
                                # Convert percentage values from UI (0-100) to float (0.0-1.0)
                                if 'percentage' in key or 'slippage' in key:
                                    setattr(trading_config, key, float(value) / 100.0)
                                else:
                                    # Convert to the correct type from the dataclass definition
                                    field_type = trading_config.__annotations__[key]
                                    setattr(trading_config, key, field_type(value))

                    # --- Filter Config ---
                    if 'filters' in new_config:
                        filter_data = new_config['filters']
                        for key, value in filter_data.items():
                            if hasattr(filter_config, key):
                                # Convert social score
                                if key == 'min_social_score':
                                     setattr(filter_config, key, float(value) / 100.0)
                                else:
                                    field_type = filter_config.__annotations__[key]
                                    setattr(filter_config, key, field_type(value))

                    # --- Monitoring Config ---
                    if 'monitoring' in new_config:
                        monitoring_data = new_config['monitoring']
                        for key, value in monitoring_data.items():
                            if hasattr(monitoring_config, key):
                                # Handle lists from textareas
                                if key in ['memecoin_keywords', 'twitter_accounts', 'reddit_subreddits', 'telegram_channels', 'discord_channels']:
                                     setattr(monitoring_config, key, value)
                                else:
                                    field_type = monitoring_config.__annotations__[key]
                                    setattr(monitoring_config, key, field_type(value))

                    # --- Security Config ---
                    if 'security' in new_config:
                        security_data = new_config['security']
                        # These map back to the trading_config object
                        if 'max_daily_loss_percentage' in security_data:
                            trading_config.max_daily_loss_percentage = float(security_data['max_daily_loss_percentage']) / 100.0
                        if 'emergency_stop_loss_percentage' in security_data:
                            trading_config.emergency_stop_loss_percentage = float(security_data['emergency_stop_loss_percentage']) / 100.0
                        # Note: emergency_stop_enabled requires restart as it's from .env

                    # Re-validate the config
                    if not validate_config():
                        self.logger.warning("Updated configuration failed validation.")
                        # The bot will continue with the last valid config, but the UI might show the invalid one.
                        return jsonify({'success': False, 'error': 'Configuration updated but is invalid. Check bot logs.'}), 400

                    self.logger.info("Configuration updated successfully from web interface.")
                    return jsonify({'success': True, 'message': 'Configuration updated successfully'})

                except Exception as e:
                    self.logger.error(f"Error updating configuration: {e}", exc_info=True)
                    return jsonify({'success': False, 'error': str(e)}), 400
        
        @self.app.route('/api/logs')
        def api_logs():
            """Get recent logs"""
            log_type = request.args.get('type', 'all')
            limit = request.args.get('limit', 100, type=int)
            
            # This would read from log files
            # For now, return sample data
            logs = [
                {
                    'timestamp': datetime.now().isoformat(),
                    'level': 'DEBUG',
                    'message': 'Sample log message',
                    'module': 'WebInterface'
                }
            ]
            
            return jsonify(logs)
        
        @self.app.route('/api/analytics')
        def api_analytics():
            """Get analytics data"""
            try:
                if self.bot:
                    # Calculate analytics from bot data
                    analytics_data = {
                        'total_pnl': sum(pos.get('pnl', 0) for pos in self.bot.get_positions()),
                        'win_rate': self._calculate_win_rate(),
                        'avg_hold_time': self._calculate_avg_hold_time(),
                        'best_trade': self._get_best_trade(),
                        'pnl_history': self._get_pnl_history(),
                        'discovery_sources': self._get_discovery_sources(),
                        'recent_trades': self._get_recent_trades(),
                        'top_tokens': self._get_top_tokens()
                    }
                else:
                    # Return default values when bot is not running
                    analytics_data = {
                        'total_pnl': 0.0,
                        'win_rate': 0.0,
                        'avg_hold_time': '0h 0m',
                        'best_trade': 0.0,
                        'pnl_history': [],
                        'discovery_sources': {'twitter': 0, 'reddit': 0, 'discord': 0, 'telegram': 0, 'tiktok': 0},
                        'recent_trades': [],
                        'top_tokens': []
                    }
                
                return jsonify(analytics_data)
            except Exception as e:
                self.logger.error(f"Error getting analytics data: {e}")
                return jsonify({'error': 'Failed to load analytics data'}), 500
    
    def _calculate_win_rate(self):
        """Calculate win rate from completed trades"""
        try:
            completed_trades = [pos for pos in self.bot.get_positions() if pos.get('status') == 'closed']
            if not completed_trades:
                return 0.0
            winning_trades = [pos for pos in completed_trades if pos.get('pnl', 0) > 0]
            return (len(winning_trades) / len(completed_trades)) * 100
        except:
            return 0.0
    
    def _calculate_avg_hold_time(self):
        """Calculate average holding time"""
        try:
            completed_trades = [pos for pos in self.bot.get_positions() if pos.get('status') == 'closed']
            if not completed_trades:
                return '0h 0m'
            
            total_seconds = sum(pos.get('hold_time_seconds', 0) for pos in completed_trades)
            avg_seconds = total_seconds / len(completed_trades)
            
            hours = int(avg_seconds // 3600)
            minutes = int((avg_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        except:
            return '0h 0m'
    
    def _get_best_trade(self):
        """Get best trade return percentage"""
        try:
            completed_trades = [pos for pos in self.bot.get_positions() if pos.get('status') == 'closed']
            if not completed_trades:
                return 0.0
            
            best_return = max(pos.get('return_percentage', 0) for pos in completed_trades)
            return best_return
        except:
            return 0.0
    
    def _get_pnl_history(self):
        """Get P&L history for charting"""
        # This would ideally come from stored historical data
        # For now, return sample data
        return [
            {'time': '12:00', 'pnl': 0.5},
            {'time': '13:00', 'pnl': 1.2},
            {'time': '14:00', 'pnl': 0.8},
            {'time': '15:00', 'pnl': 2.1}
        ]
    
    def _get_discovery_sources(self):
        """Get discovery source statistics"""
        try:
            discoveries = self.bot.get_recent_discoveries(100)
            sources = {'twitter': 0, 'reddit': 0, 'discord': 0, 'telegram': 0, 'tiktok': 0}
            
            for disc in discoveries:
                source = disc.get('source', '').lower()
                if source in sources:
                    sources[source] += 1
            
            return sources
        except:
            return {'twitter': 0, 'reddit': 0, 'discord': 0, 'telegram': 0, 'tiktok': 0}
    
    def _get_recent_trades(self):
        """Get recent trading history"""
        try:
            completed_trades = [pos for pos in self.bot.get_positions() if pos.get('status') == 'closed']
            recent = sorted(completed_trades, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
            
            formatted_trades = []
            for trade in recent:
                formatted_trades.append({
                    'date': trade.get('created_at', ''),
                    'token': trade.get('symbol', 'Unknown'),
                    'action': 'BUY' if trade.get('side') == 'buy' else 'SELL',
                    'amount': trade.get('amount', 0),
                    'price': trade.get('price', 0),
                    'pnl': trade.get('pnl', 0),
                    'source': trade.get('source', 'Unknown')
                })
            
            return formatted_trades
        except:
            return []
    
    def _get_top_tokens(self):
        """Get top performing tokens"""
        try:
            completed_trades = [pos for pos in self.bot.get_positions() if pos.get('status') == 'closed']
            profitable = [pos for pos in completed_trades if pos.get('return_percentage', 0) > 0]
            top = sorted(profitable, key=lambda x: x.get('return_percentage', 0), reverse=True)[:5]
            
            formatted_tokens = []
            for token in top:
                formatted_tokens.append({
                    'symbol': token.get('symbol', 'Unknown'),
                    'entry_price': token.get('entry_price', 0),
                    'exit_price': token.get('exit_price', 0),
                    'return': token.get('return_percentage', 0),
                    'hold_time': token.get('hold_time', '0h 0m'),
                    'source': token.get('source', 'Unknown')
                })
            
            return formatted_tokens
        except:
            return []
    
    def _setup_socket_events(self):
        """Setup SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect(auth=None):
            """Handle client connection"""
            self.connected_clients.add(request.sid)
            join_room('live_updates')
            
            # Send initial data with proper JSON serialization
            try:
                initial_data = json.loads(json.dumps(self.live_data, cls=DateTimeJSONEncoder))
                emit('status_update', initial_data)
            except Exception as e:
                self.logger.error(f"Error sending initial data: {e}")
                emit('status_update', {'status': 'connected'})
            
            self.logger.info(f"Client connected: {request.sid}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            self.connected_clients.discard(request.sid)
            leave_room('live_updates')
            
            self.logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('subscribe')
        def handle_subscribe(data):
            """Handle subscription to specific data streams"""
            stream = data.get('stream')
            if stream:
                join_room(f'stream_{stream}')
                self.logger.info(f"Client {request.sid} subscribed to {stream}")
        
        @self.socketio.on('unsubscribe')
        def handle_unsubscribe(data):
            """Handle unsubscription from data streams"""
            stream = data.get('stream')
            if stream:
                leave_room(f'stream_{stream}')
                self.logger.info(f"Client {request.sid} unsubscribed from {stream}")
        
        @self.socketio.on('manual_action')
        def handle_manual_action(data):
            """Handle manual actions from UI"""
            action = data.get('action')
            params = data.get('params', {})
            
            try:
                result = self._process_manual_action(action, params)
                emit('action_result', result)
            
            except Exception as e:
                emit('action_result', {
                    'success': False,
                    'error': str(e)
                })
    
    def _process_manual_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process manual action from UI"""
        if not self.bot:
            return {'success': False, 'error': 'Bot not initialized'}
        
        try:
            if action == 'force_sell_position':
                token_address = params.get('token_address')
                if not token_address:
                    return {'success': False, 'error': 'Token address required'}
                
                # This would trigger a manual sell
                # For now, just return success
                return {'success': True, 'message': f'Manual sell initiated for {token_address}'}
            
            elif action == 'blacklist_token':
                token_address = params.get('token_address')
                if not token_address:
                    return {'success': False, 'error': 'Token address required'}
                
                # Add to blacklist
                return {'success': True, 'message': f'Token {token_address} blacklisted'}
            
            elif action == 'analyze_token':
                token_address = params.get('token_address')
                if not token_address:
                    return {'success': False, 'error': 'Token address required'}
                
                # Trigger manual analysis
                return {'success': True, 'message': f'Analysis initiated for {token_address}'}
            
            else:
                return {'success': False, 'error': f'Unknown action: {action}'}
        
        except Exception as e:
            self.logger.error(f"Error processing manual action: {e}")
            return {'success': False, 'error': str(e)}
    
    def _start_background_tasks(self):
        """Start background tasks for real-time updates"""
        
        def update_live_data():
            """Update live data periodically"""
            while True:
                try:
                    if self.bot and len(self.connected_clients) > 0:
                        # Update live data
                        live_data_update = {
                            'bot_status': 'running' if self.bot.running else 'stopped',
                            'statistics': self.bot.stats,
                            'positions': self._serialize_positions(self.bot.get_positions()),
                            'recent_discoveries': self._serialize_discoveries(self.bot.get_recent_discoveries(10)),
                            'system_metrics': self._get_system_metrics(),
                            'last_update': datetime.now().isoformat()
                        }
                        
                        self.live_data.update(live_data_update)
                        
                        # Emit to all connected clients with proper JSON serialization
                        self.socketio.emit('live_update', json.loads(json.dumps(live_data_update, cls=DateTimeJSONEncoder)), room='live_updates')
                    
                    threading.Event().wait(5)  # Update every 5 seconds
                
                except Exception as e:
                    self.logger.error(f"Error updating live data: {e}")
                    threading.Event().wait(10)
        
        # Start background thread
        threading.Thread(target=update_live_data, daemon=True).start()
    
    def _serialize_positions(self, positions):
        """Serialize positions data for JSON"""
        if not positions:
            return []
        
        serialized = []
        for pos in positions:
            if hasattr(pos, '__dict__'):
                pos_dict = pos.__dict__.copy()
                # Convert datetime objects to ISO format
                for key, value in pos_dict.items():
                    if isinstance(value, datetime):
                        pos_dict[key] = value.isoformat()
                serialized.append(pos_dict)
            else:
                serialized.append(pos)
        return serialized
    
    def _serialize_discoveries(self, discoveries):
        """Serialize discoveries data for JSON"""
        if not discoveries:
            return []
        
        serialized = []
        for disc in discoveries:
            if hasattr(disc, '__dict__'):
                disc_dict = disc.__dict__.copy()
                # Convert datetime objects to ISO format
                for key, value in disc_dict.items():
                    if isinstance(value, datetime):
                        disc_dict[key] = value.isoformat()
                serialized.append(disc_dict)
            else:
                serialized.append(disc)
        return serialized

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            import psutil
            
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'timestamp': datetime.now().isoformat()
            }
        
        except ImportError:
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def _run_bot_async(self):
        """Run bot in async context"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.start())
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
    
    def emit_notification(self, notification_type: str, data: Dict[str, Any]):
        """Emit notification to connected clients"""
        try:
            notification_data = {
                'type': notification_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }
            # Serialize to ensure no datetime issues
            serialized_data = json.loads(json.dumps(notification_data, cls=DateTimeJSONEncoder))
            self.socketio.emit('notification', serialized_data, room='live_updates')
        
        except Exception as e:
            self.logger.error(f"Error emitting notification: {e}")
    
    def emit_trade_update(self, trade_data: Dict[str, Any]):
        """Emit trade update to connected clients"""
        try:
            # Serialize trade data to ensure no datetime issues
            serialized_data = json.loads(json.dumps(trade_data, cls=DateTimeJSONEncoder))
            self.socketio.emit('trade_update', serialized_data, room='stream_trades')
        
        except Exception as e:
            self.logger.error(f"Error emitting trade update: {e}")
    
    def emit_discovery_update(self, discovery_data: Dict[str, Any]):
        """Emit discovery update to connected clients"""
        try:
            # Serialize discovery data to ensure no datetime issues
            serialized_data = json.loads(json.dumps(discovery_data, cls=DateTimeJSONEncoder))
            self.socketio.emit('discovery_update', serialized_data, room='stream_discoveries')
        
        except Exception as e:
            self.logger.error(f"Error emitting discovery update: {e}")
    
    def run(self, host: str = None, port: int = None, debug: bool = False):
        """Run the web interface"""
        host = host or web_config['host']
        port = port or web_config['port']
        debug = debug or web_config['debug']
        
        self.logger.info(f"Starting web interface on {host}:{port}")
        
        try:
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                debug=debug,
                allow_unsafe_werkzeug=True
            )
        
        except Exception as e:
            self.logger.error(f"Error running web interface: {e}")
            raise

def create_web_interface(bot_instance: SolanaMemecoinBot = None) -> WebInterface:
    """Factory function to create web interface"""
    return WebInterface(bot_instance)

def create_app(bot_instance: SolanaMemecoinBot = None) -> Flask:
    """Factory function to create Flask app - for main.py compatibility"""
    web_interface = WebInterface(bot_instance)
    return web_interface.app

# Create a default instance and export socketio for main.py compatibility
_default_interface = WebInterface()
socketio = _default_interface.socketio

def main():
    """Main entry point for standalone web interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Solana Memecoin Bot Web Interface')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--with-bot', action='store_true', help='Start with bot instance')
    
    args = parser.parse_args()
    
    # Create bot instance if requested
    bot = None
    if args.with_bot:
        try:
            if validate_config():
                bot = SolanaMemecoinBot()
            else:
                print("Configuration validation failed. Starting without bot.")
        except Exception as e:
            print(f"Error creating bot instance: {e}")
    
    # Create and run web interface
    web_interface = create_web_interface(bot)
    
    try:
        web_interface.run(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
    except KeyboardInterrupt:
        print("\\nShutting down web interface...")
    except Exception as e:
        print(f"Error running web interface: {e}")

if __name__ == '__main__':
    main()
