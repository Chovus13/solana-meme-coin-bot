"""
Solana trading module for automated memecoin trading
"""

import asyncio
import logging
import json
import time
from decimal import Decimal
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    from solana.rpc.async_api import AsyncClient
    from solana.rpc.commitment import Commitment
    from solana.rpc.types import TxOpts
    from solana.keypair import Keypair
    from solana.transaction import Transaction
    from solana.system_program import transfer, TransferParams
    from solana.publickey import PublicKey
    from solders.signature import Signature
    from solders.pubkey import Pubkey
    from solders.keypair import Keypair as SoldersKeypair
    from solders.transaction import VersionedTransaction
    from spl.token.instructions import get_associated_token_address, create_associated_token_account
    from spl.token.constants import TOKEN_PROGRAM_ID
    HAS_SOLANA = True
except ImportError:
    HAS_SOLANA = False

try:
    import requests
    import aiohttp
except ImportError:
    requests = None
    aiohttp = None

@dataclass
class TradeResult:
    """Result of a trading operation"""
    success: bool
    transaction_id: Optional[str] = None
    price: Optional[float] = None
    amount_in: Optional[float] = None
    amount_out: Optional[float] = None
    tokens_received: Optional[float] = None
    sol_received: Optional[float] = None
    gas_used: Optional[float] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

class SolanaTrader:
    """Solana-based trading implementation"""
    
    def __init__(self, api_keys, trading_config):
        """Initialize Solana trader"""
        self.logger = logging.getLogger(__name__)
        self.api_keys = api_keys
        self.config = trading_config
        
        # Initialize Solana client
        self.client = None
        self.wallet = None
        
        if HAS_SOLANA and api_keys.solana_private_key:
            try:
                # Initialize client
                self.client = AsyncClient(api_keys.solana_rpc_url, commitment=Commitment("confirmed"))
                
                # Initialize wallet
                private_key_bytes = bytes.fromhex(api_keys.solana_private_key)
                self.wallet = SoldersKeypair.from_bytes(private_key_bytes)
                
                self.logger.info(f"Solana trader initialized with wallet: {self.wallet.pubkey()}")
            except Exception as e:
                self.logger.error(f"Failed to initialize Solana trader: {e}")
                self.client = None
                self.wallet = None
        else:
            self.logger.warning("Solana dependencies not available or no private key provided")
        
        # DEX configurations
        self.dex_configs = {
            'raydium': {
                'program_id': 'RVKd61ztZW9GUwhRbbLoYVRE5Xf1B2tVscKqwZqXgEr',
                'fee_rate': 0.0025  # 0.25%
            },
            'jupiter': {
                'api_url': 'https://quote-api.jup.ag/v6',
                'fee_rate': 0.0003  # Dynamic
            },
            'pumpfun': {
                'program_id': '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P',
                'fee_rate': 0.01  # 1%
            }
        }
        
        # SOL mint address
        self.SOL_MINT = "So11111111111111111111111111111111111111112"
        self.WSOL_MINT = "So11111111111111111111111111111111111111112"
        
        # Price cache
        self.price_cache = {}
        self.cache_duration = 30  # 30 seconds
        
        # Transaction history
        self.transaction_history = []
    
    async def buy_token(self, token_address: str, amount_sol: float, slippage: float = 0.20) -> Dict[str, Any]:
        """Buy a token with SOL"""
        try:
            if not self.client or not self.wallet:
                return TradeResult(
                    success=False,
                    error="Solana client not initialized"
                ).__dict__
            
            self.logger.info(f"Attempting to buy {token_address} with {amount_sol} SOL")
            
            # Get quote first
            quote = await self._get_buy_quote(token_address, amount_sol, slippage)
            if not quote:
                return TradeResult(
                    success=False,
                    error="Failed to get quote"
                ).__dict__
            
            # Check SOL balance
            sol_balance = await self._get_sol_balance()
            if sol_balance < amount_sol:
                return TradeResult(
                    success=False,
                    error=f"Insufficient SOL balance: {sol_balance} < {amount_sol}"
                ).__dict__
            
            # Execute trade based on the best available DEX
            trade_result = await self._execute_buy_trade(token_address, amount_sol, slippage, quote)
            
            # Log transaction
            if trade_result['success']:
                self._log_transaction('BUY', token_address, trade_result)
            
            return trade_result
        
        except Exception as e:
            self.logger.error(f"Error buying token {token_address}: {e}")
            return TradeResult(
                success=False,
                error=str(e)
            ).__dict__
    
    async def sell_token(self, token_address: str, amount_tokens: float, slippage: float = 0.25) -> Dict[str, Any]:
        """Sell tokens for SOL"""
        try:
            if not self.client or not self.wallet:
                return TradeResult(
                    success=False,
                    error="Solana client not initialized"
                ).__dict__
            
            self.logger.info(f"Attempting to sell {amount_tokens} of {token_address}")
            
            # Check token balance
            token_balance = await self._get_token_balance(token_address)
            if token_balance < amount_tokens:
                return TradeResult(
                    success=False,
                    error=f"Insufficient token balance: {token_balance} < {amount_tokens}"
                ).__dict__
            
            # Get quote
            quote = await self._get_sell_quote(token_address, amount_tokens, slippage)
            if not quote:
                return TradeResult(
                    success=False,
                    error="Failed to get quote"
                ).__dict__
            
            # Execute trade
            trade_result = await self._execute_sell_trade(token_address, amount_tokens, slippage, quote)
            
            # Log transaction
            if trade_result['success']:
                self._log_transaction('SELL', token_address, trade_result)
            
            return trade_result
        
        except Exception as e:
            self.logger.error(f"Error selling token {token_address}: {e}")
            return TradeResult(
                success=False,
                error=str(e)
            ).__dict__
    
    async def _get_buy_quote(self, token_address: str, amount_sol: float, slippage: float) -> Optional[Dict[str, Any]]:
        """Get quote for buying tokens"""
        try:
            # Try Jupiter first (usually best rates)
            jupiter_quote = await self._get_jupiter_quote(
                input_mint=self.SOL_MINT,
                output_mint=token_address,
                amount=int(amount_sol * 10**9),  # Convert to lamports
                slippage_bps=int(slippage * 10000)
            )
            
            if jupiter_quote:
                return {
                    'dex': 'jupiter',
                    'quote': jupiter_quote,
                    'estimated_output': float(jupiter_quote['outAmount']) / (10**jupiter_quote.get('outputDecimals', 9))
                }
            
            # Fallback to Raydium
            raydium_quote = await self._get_raydium_quote(token_address, amount_sol, 'buy')
            if raydium_quote:
                return {
                    'dex': 'raydium',
                    'quote': raydium_quote,
                    'estimated_output': raydium_quote['estimated_output']
                }
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting buy quote: {e}")
            return None
    
    async def _get_sell_quote(self, token_address: str, amount_tokens: float, slippage: float) -> Optional[Dict[str, Any]]:
        """Get quote for selling tokens"""
        try:
            # Get token decimals
            token_decimals = await self._get_token_decimals(token_address)
            
            # Try Jupiter first
            jupiter_quote = await self._get_jupiter_quote(
                input_mint=token_address,
                output_mint=self.SOL_MINT,
                amount=int(amount_tokens * 10**token_decimals),
                slippage_bps=int(slippage * 10000)
            )
            
            if jupiter_quote:
                return {
                    'dex': 'jupiter',
                    'quote': jupiter_quote,
                    'estimated_output': float(jupiter_quote['outAmount']) / 10**9  # Convert to SOL
                }
            
            # Fallback to Raydium
            raydium_quote = await self._get_raydium_quote(token_address, amount_tokens, 'sell')
            if raydium_quote:
                return {
                    'dex': 'raydium',
                    'quote': raydium_quote,
                    'estimated_output': raydium_quote['estimated_output']
                }
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting sell quote: {e}")
            return None
    
    async def _get_jupiter_quote(self, input_mint: str, output_mint: str, amount: int, slippage_bps: int) -> Optional[Dict[str, Any]]:
        """Get quote from Jupiter DEX"""
        try:
            if not aiohttp:
                return None
            
            async with aiohttp.ClientSession() as session:
                # Get quote
                quote_url = f"{self.dex_configs['jupiter']['api_url']}/quote"
                params = {
                    'inputMint': input_mint,
                    'outputMint': output_mint,
                    'amount': amount,
                    'slippageBps': slippage_bps
                }
                
                async with session.get(quote_url, params=params) as response:
                    if response.status == 200:
                        quote_data = await response.json()
                        return quote_data
                    else:
                        self.logger.warning(f"Jupiter quote failed: {response.status}")
                        return None
        
        except Exception as e:
            self.logger.error(f"Error getting Jupiter quote: {e}")
            return None
    
    async def _get_raydium_quote(self, token_address: str, amount: float, direction: str) -> Optional[Dict[str, Any]]:
        """Get quote from Raydium (simplified)"""
        try:
            # This is a simplified implementation
            # Real implementation would need to interact with Raydium pools
            
            # Get current price
            price = await self.get_token_price(token_address)
            if not price:
                return None
            
            if direction == 'buy':
                estimated_output = amount / price
            else:
                estimated_output = amount * price
            
            return {
                'price': price,
                'estimated_output': estimated_output,
                'impact': 0.01  # Simplified
            }
        
        except Exception as e:
            self.logger.error(f"Error getting Raydium quote: {e}")
            return None
    
    async def _execute_buy_trade(self, token_address: str, amount_sol: float, slippage: float, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Execute buy trade"""
        try:
            dex = quote['dex']
            
            if dex == 'jupiter':
                return await self._execute_jupiter_swap(quote['quote'])
            elif dex == 'raydium':
                return await self._execute_raydium_swap(token_address, amount_sol, 'buy', quote)
            else:
                return TradeResult(
                    success=False,
                    error=f"Unsupported DEX: {dex}"
                ).__dict__
        
        except Exception as e:
            self.logger.error(f"Error executing buy trade: {e}")
            return TradeResult(
                success=False,
                error=str(e)
            ).__dict__
    
    async def _execute_sell_trade(self, token_address: str, amount_tokens: float, slippage: float, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Execute sell trade"""
        try:
            dex = quote['dex']
            
            if dex == 'jupiter':
                return await self._execute_jupiter_swap(quote['quote'])
            elif dex == 'raydium':
                return await self._execute_raydium_swap(token_address, amount_tokens, 'sell', quote)
            else:
                return TradeResult(
                    success=False,
                    error=f"Unsupported DEX: {dex}"
                ).__dict__
        
        except Exception as e:
            self.logger.error(f"Error executing sell trade: {e}")
            return TradeResult(
                success=False,
                error=str(e)
            ).__dict__
    
    async def _execute_jupiter_swap(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Execute swap through Jupiter"""
        try:
            if not aiohttp:
                return TradeResult(
                    success=False,
                    error="aiohttp not available"
                ).__dict__
            
            async with aiohttp.ClientSession() as session:
                # Get swap transaction
                swap_url = f"{self.dex_configs['jupiter']['api_url']}/swap"
                swap_data = {
                    'quoteResponse': quote,
                    'userPublicKey': str(self.wallet.pubkey()),
                    'wrapAndUnwrapSol': True,
                    'prioritizationFeeLamports': self.config.priority_fee_lamports
                }
                
                async with session.post(swap_url, json=swap_data) as response:
                    if response.status == 200:
                        swap_response = await response.json()
                        
                        # Deserialize and sign transaction
                        transaction_bytes = bytes.fromhex(swap_response['swapTransaction'])
                        transaction = VersionedTransaction.from_bytes(transaction_bytes)
                        
                        # Sign transaction
                        transaction.sign([self.wallet])
                        
                        # Send transaction
                        result = await self.client.send_transaction(
                            transaction,
                            opts=TxOpts(skip_confirmation=False, preflight_commitment=Commitment("confirmed"))
                        )
                        
                        if result.value:
                            # Wait for confirmation
                            await self._wait_for_confirmation(str(result.value))
                            
                            return TradeResult(
                                success=True,
                                transaction_id=str(result.value),
                                price=float(quote['inAmount']) / float(quote['outAmount']),
                                amount_in=float(quote['inAmount']),
                                amount_out=float(quote['outAmount']),
                                timestamp=datetime.now()
                            ).__dict__
                        else:
                            return TradeResult(
                                success=False,
                                error="Transaction failed to send"
                            ).__dict__
                    else:
                        error_text = await response.text()
                        return TradeResult(
                            success=False,
                            error=f"Jupiter swap failed: {error_text}"
                        ).__dict__
        
        except Exception as e:
            self.logger.error(f"Error executing Jupiter swap: {e}")
            return TradeResult(
                success=False,
                error=str(e)
            ).__dict__
    
    async def _execute_raydium_swap(self, token_address: str, amount: float, direction: str, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Execute swap through Raydium (simplified)"""
        try:
            # This is a placeholder implementation
            # Real Raydium integration would require complex pool interaction
            
            await asyncio.sleep(2)  # Simulate transaction time
            
            # Simulate successful trade
            if direction == 'buy':
                return TradeResult(
                    success=True,
                    transaction_id=f"raydium_buy_{int(time.time())}",
                    price=quote['quote']['price'],
                    amount_in=amount,
                    tokens_received=quote['quote']['estimated_output'],
                    timestamp=datetime.now()
                ).__dict__
            else:
                return TradeResult(
                    success=True,
                    transaction_id=f"raydium_sell_{int(time.time())}",
                    price=quote['quote']['price'],
                    amount_in=amount,
                    sol_received=quote['quote']['estimated_output'],
                    timestamp=datetime.now()
                ).__dict__
        
        except Exception as e:
            self.logger.error(f"Error executing Raydium swap: {e}")
            return TradeResult(
                success=False,
                error=str(e)
            ).__dict__
    
    async def get_token_price(self, token_address: str) -> Optional[float]:
        """Get current token price"""
        try:
            # Check cache first
            cache_key = f"price_{token_address}"
            if cache_key in self.price_cache:
                cache_entry = self.price_cache[cache_key]
                if time.time() - cache_entry['timestamp'] < self.cache_duration:
                    return cache_entry['price']
            
            # Try Jupiter price API
            price = await self._get_jupiter_price(token_address)
            
            if price:
                # Cache the price
                self.price_cache[cache_key] = {
                    'price': price,
                    'timestamp': time.time()
                }
                return price
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting token price: {e}")
            return None
    
    async def _get_jupiter_price(self, token_address: str) -> Optional[float]:
        """Get token price from Jupiter"""
        try:
            if not aiohttp:
                return None
            
            async with aiohttp.ClientSession() as session:
                # Use Jupiter price API
                price_url = f"{self.dex_configs['jupiter']['api_url']}/price"
                params = {
                    'ids': token_address,
                    'vsToken': self.SOL_MINT
                }
                
                async with session.get(price_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'data' in data and token_address in data['data']:
                            return float(data['data'][token_address]['price'])
            
            return None
        
        except Exception as e:
            self.logger.error(f"Error getting Jupiter price: {e}")
            return None
    
    async def _get_sol_balance(self) -> float:
        """Get SOL balance of the wallet"""
        try:
            if not self.client or not self.wallet:
                return 0.0
            
            balance = await self.client.get_balance(self.wallet.pubkey())
            return float(balance.value) / 10**9  # Convert lamports to SOL
        
        except Exception as e:
            self.logger.error(f"Error getting SOL balance: {e}")
            return 0.0
    
    async def _get_token_balance(self, token_address: str) -> float:
        """Get token balance"""
        try:
            if not self.client or not self.wallet:
                return 0.0
            
            # Get associated token account
            token_mint = Pubkey.from_string(token_address)
            associated_token_account = get_associated_token_address(
                self.wallet.pubkey(),
                token_mint
            )
            
            # Get token account balance
            balance = await self.client.get_token_account_balance(associated_token_account)
            
            if balance.value:
                return float(balance.value.amount) / (10 ** balance.value.decimals)
            
            return 0.0
        
        except Exception as e:
            self.logger.error(f"Error getting token balance: {e}")
            return 0.0
    
    async def _get_token_decimals(self, token_address: str) -> int:
        """Get token decimals"""
        try:
            if not self.client:
                return 9  # Default
            
            token_mint = Pubkey.from_string(token_address)
            mint_info = await self.client.get_account_info(token_mint)
            
            if mint_info.value:
                # Parse mint data to get decimals
                # This is simplified - real implementation would parse the account data
                return 9  # Default for most tokens
            
            return 9
        
        except Exception as e:
            self.logger.error(f"Error getting token decimals: {e}")
            return 9
    
    async def _wait_for_confirmation(self, transaction_id: str, timeout: int = 60):
        """Wait for transaction confirmation"""
        try:
            signature = Signature.from_string(transaction_id)
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                status = await self.client.get_signature_status(signature)
                
                if status.value and status.value.confirmation_status:
                    if status.value.confirmation_status in ["confirmed", "finalized"]:
                        self.logger.info(f"Transaction {transaction_id} confirmed")
                        return True
                    elif status.value.err:
                        self.logger.error(f"Transaction {transaction_id} failed: {status.value.err}")
                        return False
                
                await asyncio.sleep(2)
            
            self.logger.warning(f"Transaction {transaction_id} timeout")
            return False
        
        except Exception as e:
            self.logger.error(f"Error waiting for confirmation: {e}")
            return False
    
    def _log_transaction(self, trade_type: str, token_address: str, result: Dict[str, Any]):
        """Log transaction details"""
        transaction_log = {
            'timestamp': datetime.now().isoformat(),
            'type': trade_type,
            'token_address': token_address,
            'result': result
        }
        
        self.transaction_history.append(transaction_log)
        
        # Keep only last 1000 transactions
        if len(self.transaction_history) > 1000:
            self.transaction_history = self.transaction_history[-1000:]
    
    async def get_portfolio_value(self) -> Dict[str, Any]:
        """Get current portfolio value"""
        try:
            portfolio = {
                'sol_balance': await self._get_sol_balance(),
                'tokens': {},
                'total_value_sol': 0.0,
                'last_updated': datetime.now().isoformat()
            }
            
            # This would require tracking all token holdings
            # For now, just return SOL balance
            portfolio['total_value_sol'] = portfolio['sol_balance']
            
            return portfolio
        
        except Exception as e:
            self.logger.error(f"Error getting portfolio value: {e}")
            return {}
    
    async def get_transaction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent transaction history"""
        return self.transaction_history[-limit:]
    
    def is_connected(self) -> bool:
        """Check if trader is connected"""
        return self.client is not None and self.wallet is not None
    
    async def close(self):
        """Close connections"""
        if self.client:
            await self.client.close()
