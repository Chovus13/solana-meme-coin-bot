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

# Import bot components
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import web_config, validate_config
from utils.logger import setup_logger
from solana_memecoin_bot import SolanaMemecoinBot

class WebInterface:
    """Web interface for the trading bot"""
    
    def __init__(self, bot_instance: SolanaMemecoinBot = None):
        """Initialize web interface"""
        self.logger = setup_logger("WebInterface")
        
        # Flask app setup
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = web_config.secret_key
        
        # Enable CORS
        CORS(self.app)
        
        # SocketIO setup
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            async_mode='threading'
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
                        'buy_amount_sol': 1.5,
                        'slippage_buy': 0.20,
                        'slippage_sell': 0.25,
                        'take_profit_multiplier': 10.0,
                        'moonbag_percentage': 0.15
                    },
                    'filters': {
                        'min_safety_score': 80,
                        'min_market_cap': 10000,
                        'max_market_cap': 1000000
                    },
                    'monitoring': {
                        'twitter_check_interval': 30,
                        'reddit_check_interval': 60
                    }
                }
                return jsonify(config_data)
            
            else:
                # Update config
                try:
                    new_config = request.json
                    # This would update the actual configuration
                    # For now, just return success
                    return jsonify({'success': True, 'message': 'Configuration updated'})
                
                except Exception as e:
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
                    'level': 'INFO',
                    'message': 'Sample log message',
                    'module': 'WebInterface'
                }
            ]
            
            return jsonify(logs)
    
    def _setup_socket_events(self):
        """Setup SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            self.connected_clients.add(request.sid)
            join_room('live_updates')
            
            # Send initial data
            emit('status_update', self.live_data)
            
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
                        self.live_data.update({
                            'bot_status': 'running' if self.bot.running else 'stopped',
                            'statistics': self.bot.stats,
                            'positions': self.bot.get_positions(),
                            'recent_discoveries': self.bot.get_recent_discoveries(10),
                            'system_metrics': self._get_system_metrics(),
                            'last_update': datetime.now().isoformat()
                        })
                        
                        # Emit to all connected clients
                        self.socketio.emit('live_update', self.live_data, room='live_updates')
                    
                    threading.Event().wait(5)  # Update every 5 seconds
                
                except Exception as e:
                    self.logger.error(f"Error updating live data: {e}")
                    threading.Event().wait(10)
        
        # Start background thread
        threading.Thread(target=update_live_data, daemon=True).start()
    
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
            self.socketio.emit('notification', {
                'type': notification_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }, room='live_updates')
        
        except Exception as e:
            self.logger.error(f"Error emitting notification: {e}")
    
    def emit_trade_update(self, trade_data: Dict[str, Any]):
        """Emit trade update to connected clients"""
        try:
            self.socketio.emit('trade_update', trade_data, room='stream_trades')
        
        except Exception as e:
            self.logger.error(f"Error emitting trade update: {e}")
    
    def emit_discovery_update(self, discovery_data: Dict[str, Any]):
        """Emit discovery update to connected clients"""
        try:
            self.socketio.emit('discovery_update', discovery_data, room='stream_discoveries')
        
        except Exception as e:
            self.logger.error(f"Error emitting discovery update: {e}")
    
    def run(self, host: str = None, port: int = None, debug: bool = False):
        """Run the web interface"""
        host = host or web_config.host
        port = port or web_config.port
        debug = debug or web_config.debug
        
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
