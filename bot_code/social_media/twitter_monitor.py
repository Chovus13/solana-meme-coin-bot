"""
Twitter monitoring module for discovering memecoin mentions and ticker symbols
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import tweepy
import aiohttp
import json

class TwitterMonitor:
    """Monitor Twitter for memecoin-related content"""
    
    def __init__(self, api_keys):
        """Initialize Twitter monitor with API keys"""
        self.logger = logging.getLogger(__name__)
        self.api_keys = api_keys
        
        # Initialize Twitter API client
        if api_keys.twitter_bearer_token:
            self.client = tweepy.Client(
                bearer_token=api_keys.twitter_bearer_token,
                consumer_key=api_keys.twitter_api_key,
                consumer_secret=api_keys.twitter_api_secret,
                access_token=api_keys.twitter_access_token,
                access_token_secret=api_keys.twitter_access_secret,
                wait_on_rate_limit=True
            )
        else:
            self.client = None
            self.logger.warning("No Twitter API credentials provided")
        
        # Compiled regex patterns for efficiency
        self.contract_pattern = re.compile(r'[A-HJ-NP-Z1-9]{32,44}')
        self.ticker_pattern = re.compile(r'\$([A-Z]{2,10})\b')
        self.ca_pattern = re.compile(r'CA:?\s*([A-HJ-NP-Z1-9]{32,44})')
        
        # Track processed tweets to avoid duplicates
        self.processed_tweets = set()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Minimum seconds between requests
    
    async def get_recent_tweets(self, username: str, keywords: List[str], hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get recent tweets from a specific user"""
        if not self.client:
            return []
        
        try:
            # Remove @ if present
            username = username.lstrip('@')
            
            # Calculate start time
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Get user ID
            user = self.client.get_user(username=username)
            if not user.data:
                self.logger.warning(f"User not found: {username}")
                return []
            
            user_id = user.data.id
            
            # Get recent tweets
            tweets = self.client.get_users_tweets(
                id=user_id,
                start_time=start_time,
                max_results=100,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'context_annotations'],
                exclude=['retweets', 'replies']
            )
            
            if not tweets.data:
                return []
            
            # Process tweets
            processed_tweets = []
            for tweet in tweets.data:
                if self._contains_keywords(tweet.text, keywords):
                    processed_tweet = self._process_tweet(tweet, username)
                    if processed_tweet:
                        processed_tweets.append(processed_tweet)
            
            self.logger.info(f"Found {len(processed_tweets)} relevant tweets from @{username}")
            return processed_tweets
            
        except Exception as e:
            self.logger.error(f"Error getting tweets from {username}: {e}")
            return []
    
    async def search_tweets(self, keywords: List[str], limit: int = 100, hours_back: int = 6) -> List[Dict[str, Any]]:
        """Search for tweets containing specific keywords"""
        if not self.client:
            return []
        
        try:
            # Construct search query
            query_parts = []
            
            # Add memecoin-related keywords
            memecoin_keywords = ['memecoin', 'pump', 'moon', 'gem', '$', 'CA:', 'solana']
            for keyword in memecoin_keywords:
                query_parts.append(keyword)
            
            # Combine with OR
            query = ' OR '.join(query_parts)
            
            # Add filters
            query += ' -is:retweet -is:reply lang:en'
            
            # Calculate start time
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Search tweets
            tweets = self.client.search_recent_tweets(
                query=query,
                start_time=start_time,
                max_results=min(limit, 100),  # API limit
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'context_annotations'],
                user_fields=['username', 'verified', 'public_metrics']
            )
            
            if not tweets.data:
                return []
            
            # Process tweets
            processed_tweets = []
            for tweet in tweets.data:
                if self._contains_keywords(tweet.text, keywords):
                    # Get author info
                    author_username = 'unknown'
                    if tweets.includes and 'users' in tweets.includes:
                        for user in tweets.includes['users']:
                            if user.id == tweet.author_id:
                                author_username = user.username
                                break
                    
                    processed_tweet = self._process_tweet(tweet, author_username)
                    if processed_tweet:
                        processed_tweets.append(processed_tweet)
            
            self.logger.info(f"Found {len(processed_tweets)} relevant tweets from search")
            return processed_tweets
            
        except Exception as e:
            self.logger.error(f"Error searching tweets: {e}")
            return []
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the specified keywords"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    def _process_tweet(self, tweet, author_username: str) -> Optional[Dict[str, Any]]:
        """Process a tweet and extract relevant information"""
        try:
            tweet_id = str(tweet.id)
            
            # Skip if already processed
            if tweet_id in self.processed_tweets:
                return None
            
            self.processed_tweets.add(tweet_id)
            
            # Extract token information
            contract_addresses = self.contract_pattern.findall(tweet.text)
            ticker_symbols = self.ticker_pattern.findall(tweet.text.upper())
            ca_addresses = self.ca_pattern.findall(tweet.text)
            
            # Combine contract addresses
            all_contracts = list(set(contract_addresses + ca_addresses))
            
            # Calculate engagement score
            metrics = tweet.public_metrics if hasattr(tweet, 'public_metrics') else {}
            engagement_score = self._calculate_engagement_score(metrics)
            
            # Determine if this looks like a memecoin promotion
            is_memecoin_related = self._is_memecoin_related(tweet.text)
            
            processed_tweet = {
                'id': tweet_id,
                'text': tweet.text,
                'author': author_username,
                'created_at': tweet.created_at.isoformat() if tweet.created_at else datetime.utcnow().isoformat(),
                'url': f"https://twitter.com/{author_username}/status/{tweet_id}",
                'contract_addresses': all_contracts,
                'ticker_symbols': ticker_symbols,
                'engagement_score': engagement_score,
                'is_memecoin_related': is_memecoin_related,
                'metrics': metrics
            }
            
            return processed_tweet
            
        except Exception as e:
            self.logger.error(f"Error processing tweet: {e}")
            return None
    
    def _calculate_engagement_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate engagement score based on tweet metrics"""
        try:
            retweets = metrics.get('retweet_count', 0)
            likes = metrics.get('like_count', 0)
            replies = metrics.get('reply_count', 0)
            quotes = metrics.get('quote_count', 0)
            
            # Weighted engagement score
            score = (retweets * 3) + (likes * 1) + (replies * 2) + (quotes * 2)
            
            # Normalize to 0-1 scale (logarithmic)
            import math
            normalized_score = math.log(max(score + 1, 1)) / 10
            
            return min(normalized_score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating engagement score: {e}")
            return 0.0
    
    def _is_memecoin_related(self, text: str) -> bool:
        """Determine if tweet is memecoin-related"""
        text_lower = text.lower()
        
        # Positive indicators
        positive_keywords = [
            'pump', 'moon', 'gem', 'new token', 'just launched', 'fair launch',
            'presale', 'memecoin', 'altcoin', 'defi', 'dex', 'raydium', 'jupiter',
            'pumpfun', 'solana', 'contract', 'ca:', 'ticker', 'symbol'
        ]
        
        # Negative indicators
        negative_keywords = [
            'scam', 'rug', 'avoid', 'warning', 'caution', 'fake', 'honeypot'
        ]
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
        
        # Check for contract addresses or tickers
        has_contract = bool(self.contract_pattern.search(text) or self.ca_pattern.search(text))
        has_ticker = bool(self.ticker_pattern.search(text))
        
        # Scoring logic
        if negative_count > 0:
            return False
        
        if has_contract or has_ticker:
            return True
        
        return positive_count >= 2
    
    async def get_user_timeline(self, username: str, count: int = 50) -> List[Dict[str, Any]]:
        """Get user's timeline"""
        if not self.client:
            return []
        
        try:
            username = username.lstrip('@')
            
            # Get user
            user = self.client.get_user(username=username)
            if not user.data:
                return []
            
            # Get timeline
            tweets = self.client.get_users_tweets(
                id=user.data.id,
                max_results=min(count, 100),
                tweet_fields=['created_at', 'public_metrics']
            )
            
            if not tweets.data:
                return []
            
            timeline = []
            for tweet in tweets.data:
                timeline.append({
                    'id': str(tweet.id),
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat(),
                    'author': username,
                    'url': f"https://twitter.com/{username}/status/{tweet.id}"
                })
            
            return timeline
            
        except Exception as e:
            self.logger.error(f"Error getting timeline for {username}: {e}")
            return []
    
    async def get_trending_hashtags(self, woeid: int = 1) -> List[str]:
        """Get trending hashtags (requires API v1.1)"""
        # This would require v1.1 API which is deprecated
        # Placeholder for now
        return []
    
    def is_kol_account(self, username: str, metrics: Dict[str, Any]) -> bool:
        """Determine if account is a Key Opinion Leader (KOL)"""
        try:
            followers = metrics.get('followers_count', 0)
            following = metrics.get('following_count', 0)
            tweets = metrics.get('tweet_count', 0)
            
            # KOL criteria
            has_many_followers = followers > 1000
            good_ratio = followers > following * 2 if following > 0 else True
            active_account = tweets > 100
            
            # Known KOL usernames (can be expanded)
            known_kols = [
                'solanafm', 'solanafloor', 'raydiumprotocol', 'jupiterexchange',
                'pumpdotfun', 'solanamobile', 'solanalabs'
            ]
            
            is_known_kol = username.lower() in known_kols
            
            return is_known_kol or (has_many_followers and good_ratio and active_account)
            
        except Exception as e:
            self.logger.error(f"Error checking KOL status: {e}")
            return False
    
    async def monitor_real_time(self, keywords: List[str], callback):
        """Monitor real-time tweets (simplified version)"""
        if not self.client:
            self.logger.warning("No Twitter client available for real-time monitoring")
            return
        
        # This is a simplified version - real implementation would use Streaming API
        while True:
            try:
                tweets = await self.search_tweets(keywords, limit=20, hours_back=1)
                
                for tweet in tweets:
                    await callback(tweet, 'twitter')
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in real-time monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
