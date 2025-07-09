import asyncio
import logging  # <<< CRITICAL: This must be at the module level (top of file)
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import praw
#from praw.exceptions import RedditAPIException, InvalidImplicitAuth, PrawcoreException # Using more specific exceptions
from praw.exceptions import RedditAPIException, InvalidImplicitAuth, PRAWException # Corrected import
import json

# This is for the __main__ test block, not essential for fixing the UnboundLocalError
# try:
#     from config import APIKeys 
# except ImportError:
#     APIKeys = None

class RedditMonitor:
    """Monitor Reddit for memecoin-related content"""
    
    def __init__(self, api_keys):
        """Initialize Reddit monitor with API keys"""
        # Your existing debug prints that show received keys - KEEP THESE:
        print(f"[DEBUG] RedditMonitor.__init__ received api_keys.reddit_client_id: {getattr(api_keys, 'reddit_client_id', 'NOT_FOUND')}")
        print(f"[DEBUG] RedditMonitor.__init__ received api_keys.reddit_client_secret: {'********' if getattr(api_keys, 'reddit_client_secret', None) else 'NOT_FOUND'}")
        print(f"[DEBUG] RedditMonitor.__init__ received api_keys.reddit_username: {getattr(api_keys, 'reddit_username', 'NOT_FOUND')}")

        # Assign to self.api_keys first
        self.api_keys = api_keys 

        # NEW PRINT STATEMENTS FOR THE CONDITION ITSELF
        client_id_val = getattr(self.api_keys, 'reddit_client_id', None)
        client_secret_val = getattr(self.api_keys, 'reddit_client_secret', None)
        print(f"[DEBUG] RedditMonitor: Value of client_id_val for condition check: '{client_id_val}' (Type: {type(client_id_val)})")
        print(f"[DEBUG] RedditMonitor: Value of client_secret_val for condition check (presence): {'PRESENT' if client_secret_val else 'None or Empty'}")

        condition_is_true = bool(client_id_val and client_secret_val)
        print(f"[DEBUG] RedditMonitor: Result of 'bool(client_id_val and client_secret_val)' is: {condition_is_true}")

        self.logger = logging.getLogger(__name__)
        self.reddit = None # Initialize self.reddit before the temporary handler uses self.logger

        # Temporary direct console handler (as before)
        if not self.logger.handlers:
            # ... (formatter, console_handler setup) ...
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.DEBUG) 
            self.logger.addHandler(console_handler)
            self.logger.propagate = False 
            self.logger.info("Added temporary direct console handler to RedditMonitor logger with DEBUG level.")
        
        self.logger.info("Attempting to initialize RedditMonitor (after explicit checks)...")
        
        if condition_is_true: # Use the explicitly evaluated condition
            print("[DEBUG] RedditMonitor: Entering PRAW initialization try block (condition was True).")
            self.logger.info("Condition for PRAW init met. Attempting PRAW setup...")
            try:
                self.logger.info("Attempting to connect to Reddit API...")
                self.reddit = praw.Reddit(
                    client_id=self.api_keys.reddit_client_id, 
                    client_secret=self.api_keys.reddit_client_secret,
                    username=self.api_keys.reddit_username,
                    password=self.api_keys.reddit_password,
                    user_agent=self.api_keys.reddit_user_agent,
                    check_for_async=False
                )
                self.logger.info("PRAW client initialized. Testing connection...")
                user = self.reddit.user.me()
                if user and user.name:
                    self.logger.info(f"Reddit API connection established successfully. Logged in as: {user.name}")
                else:
                    self.logger.error("Reddit API connection test failed: self.reddit.user.me() returned None or user without a name.")
                    raise Exception("PRAW self.reddit.user.me() failed to return a valid user.")
            # ... (Your existing except blocks that log and then 'raise' Exception) ...
            except InvalidImplicitAuth as e: 
                self.logger.error(f"Failed to initialize Reddit API (InvalidImplicitAuth): {e}.")
                self.reddit = None 
                raise  
            except PRAWException as e: 
                self.logger.error(f"Failed to initialize Reddit API (PRAWException): {e}.")
                self.reddit = None 
                raise 
            except Exception as e:
                self.logger.error(f"An UNEXPECTED error occurred during PRAW init: {e}", exc_info=True)
                self.reddit = None
                raise
        else:
            print("[DEBUG] RedditMonitor: SKIPPING PRAW initialization try block (condition was False).")
            self.logger.warning("No Reddit API client_id or client_secret provided (explicitly checked as missing/empty). Reddit monitoring will be disabled.")
            self.reddit = None # self.reddit is already None, but being explicit

            # Optionally raise Exception here if Reddit is critical

        # Regex patterns and other initializations
        self.contract_pattern = re.compile(r'[A-HJ-NP-Z1-9]{32,44}')
        self.ticker_pattern = re.compile(r'\$([A-Z]{2,10})\b')
        self.ca_pattern = re.compile(r'CA:?\s*([A-HJ-NP-Z1-9]{32,44})')
        self.processed_posts = set()
        self.processed_comments = set()
    
    async def get_hot_posts(self, subreddit_name: str, keywords: List[str], limit: int = 25) -> List[Dict[str, Any]]:
        """Get hot posts from a subreddit"""
        if not self.reddit:
            return []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            hot_posts = []
            
            for submission in subreddit.hot(limit=limit):
                # Check if post contains keywords
                if self._contains_keywords(submission.title + " " + submission.selftext, keywords):
                    processed_post = await self._process_submission(submission, subreddit_name)
                    if processed_post:
                        hot_posts.append(processed_post)
            
            self.logger.info(f"Found {len(hot_posts)} relevant hot posts in r/{subreddit_name}")
            return hot_posts
            
        except Exception as e:
            self.logger.error(f"Error getting hot posts from r/{subreddit_name}: {e}")
            return []
    
    async def get_new_posts(self, subreddit_name: str, keywords: List[str], limit: int = 50) -> List[Dict[str, Any]]:
        """Get new posts from a subreddit"""
        if not self.reddit:
            return []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            new_posts = []
            
            for submission in subreddit.new(limit=limit):
                # Check if post is recent (last 24 hours)
                post_time = datetime.fromtimestamp(submission.created_utc)
                if (datetime.now() - post_time).total_seconds() > 86400:  # 24 hours
                    continue
                
                # Check if post contains keywords
                if self._contains_keywords(submission.title + " " + submission.selftext, keywords):
                    processed_post = await self._process_submission(submission, subreddit_name)
                    if processed_post:
                        new_posts.append(processed_post)
            
            self.logger.info(f"Found {len(new_posts)} relevant new posts in r/{subreddit_name}")
            return new_posts
            
        except Exception as e:
            self.logger.error(f"Error getting new posts from r/{subreddit_name}: {e}")
            return []
    
    async def search_posts(self, query: str, subreddit_names: List[str], limit: int = 25) -> List[Dict[str, Any]]:
        """Search for posts across multiple subreddits"""
        if not self.reddit:
            return []
        
        search_results = []
        
        for subreddit_name in subreddit_names:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                for submission in subreddit.search(query, sort='new', time_filter='day', limit=limit):
                    processed_post = await self._process_submission(submission, subreddit_name)
                    if processed_post:
                        search_results.append(processed_post)
                
            except Exception as e:
                self.logger.error(f"Error searching in r/{subreddit_name}: {e}")
                continue
        
        self.logger.info(f"Found {len(search_results)} posts from search")
        return search_results
    
    async def get_post_comments(self, post_id: str, keywords: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """Get comments from a specific post"""
        if not self.reddit:
            return []
        
        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)  # Remove "more comments" objects
            
            relevant_comments = []
            
            for comment in submission.comments.list():
                if hasattr(comment, 'body') and self._contains_keywords(comment.body, keywords):
                    processed_comment = await self._process_comment(comment, submission.subreddit.display_name)
                    if processed_comment:
                        relevant_comments.append(processed_comment)
            
            return relevant_comments[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting comments for post {post_id}: {e}")
            return []
    
    async def monitor_user(self, username: str, keywords: List[str], limit: int = 25) -> List[Dict[str, Any]]:
        """Monitor a specific user's posts and comments"""
        if not self.reddit:
            return []
        
        try:
            user = self.reddit.redditor(username)
            user_content = []
            
            # Get user's submissions
            for submission in user.submissions.new(limit=limit):
                if self._contains_keywords(submission.title + " " + submission.selftext, keywords):
                    processed_post = await self._process_submission(submission, submission.subreddit.display_name)
                    if processed_post:
                        user_content.append(processed_post)
            
            # Get user's comments
            for comment in user.comments.new(limit=limit):
                if hasattr(comment, 'body') and self._contains_keywords(comment.body, keywords):
                    processed_comment = await self._process_comment(comment, comment.subreddit.display_name)
                    if processed_comment:
                        user_content.append(processed_comment)
            
            return user_content
            
        except Exception as e:
            self.logger.error(f"Error monitoring user u/{username}: {e}")
            return []
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the specified keywords"""
        if not text:
            return False
        
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    async def _process_submission(self, submission, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """Process a Reddit submission"""
        try:
            post_id = submission.id
            
            # Skip if already processed
            if post_id in self.processed_posts:
                return None
            
            self.processed_posts.add(post_id)
            
            # Extract token information
            full_text = submission.title + " " + submission.selftext
            contract_addresses = self.contract_pattern.findall(full_text)
            ticker_symbols = self.ticker_pattern.findall(full_text.upper())
            ca_addresses = self.ca_pattern.findall(full_text)
            
            # Combine contract addresses
            all_contracts = list(set(contract_addresses + ca_addresses))
            
            # Calculate engagement score
            engagement_score = self._calculate_post_engagement(submission)
            
            # Determine if this is memecoin-related
            is_memecoin_related = self._is_memecoin_related(full_text)
            
            # Get post age
            post_time = datetime.fromtimestamp(submission.created_utc)
            age_hours = (datetime.now() - post_time).total_seconds() / 3600
            
            processed_post = {
                'id': post_id,
                'title': submission.title,
                'content': submission.selftext,
                'text': full_text,  # Combined for analysis
                'author': str(submission.author) if submission.author else '[deleted]',
                'subreddit': subreddit_name,
                'created_at': post_time.isoformat(),
                'url': f"https://reddit.com{submission.permalink}",
                'score': submission.score,
                'upvote_ratio': submission.upvote_ratio,
                'num_comments': submission.num_comments,
                'contract_addresses': all_contracts,
                'ticker_symbols': ticker_symbols,
                'engagement_score': engagement_score,
                'is_memecoin_related': is_memecoin_related,
                'age_hours': age_hours,
                'flair': submission.link_flair_text,
                'is_self': submission.is_self,
                'type': 'post'
            }
            
            return processed_post
            
        except Exception as e:
            self.logger.error(f"Error processing submission: {e}")
            return None
    
    async def _process_comment(self, comment, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """Process a Reddit comment"""
        try:
            comment_id = comment.id
            
            # Skip if already processed
            if comment_id in self.processed_comments:
                return None
            
            self.processed_comments.add(comment_id)
            
            # Skip if comment is deleted or removed
            if not hasattr(comment, 'body') or comment.body in ['[deleted]', '[removed]']:
                return None
            
            # Extract token information
            contract_addresses = self.contract_pattern.findall(comment.body)
            ticker_symbols = self.ticker_pattern.findall(comment.body.upper())
            ca_addresses = self.ca_pattern.findall(comment.body)
            
            # Combine contract addresses
            all_contracts = list(set(contract_addresses + ca_addresses))
            
            # Calculate engagement score
            engagement_score = self._calculate_comment_engagement(comment)
            
            # Determine if this is memecoin-related
            is_memecoin_related = self._is_memecoin_related(comment.body)
            
            # Get comment age
            comment_time = datetime.fromtimestamp(comment.created_utc)
            age_hours = (datetime.now() - comment_time).total_seconds() / 3600
            
            processed_comment = {
                'id': comment_id,
                'text': comment.body,
                'content': comment.body,
                'author': str(comment.author) if comment.author else '[deleted]',
                'subreddit': subreddit_name,
                'created_at': comment_time.isoformat(),
                'url': f"https://reddit.com{comment.permalink}",
                'score': comment.score,
                'contract_addresses': all_contracts,
                'ticker_symbols': ticker_symbols,
                'engagement_score': engagement_score,
                'is_memecoin_related': is_memecoin_related,
                'age_hours': age_hours,
                'parent_id': comment.parent_id,
                'type': 'comment'
            }
            
            return processed_comment
            
        except Exception as e:
            self.logger.error(f"Error processing comment: {e}")
            return None
    
    def _calculate_post_engagement(self, submission) -> float:
        """Calculate engagement score for a post"""
        try:
            score = submission.score
            num_comments = submission.num_comments
            upvote_ratio = submission.upvote_ratio
            
            # Weighted engagement calculation
            engagement = (score * upvote_ratio) + (num_comments * 2)
            
            # Normalize using logarithmic scale
            import math
            normalized = math.log(max(engagement + 1, 1)) / 15
            
            return min(normalized, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating post engagement: {e}")
            return 0.0
    
    def _calculate_comment_engagement(self, comment) -> float:
        """Calculate engagement score for a comment"""
        try:
            score = comment.score
            
            # Simple engagement for comments
            import math
            normalized = math.log(max(score + 1, 1)) / 10
            
            return min(normalized, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating comment engagement: {e}")
            return 0.0
    
    def _is_memecoin_related(self, text: str) -> bool:
        """Determine if content is memecoin-related"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Positive indicators
        positive_keywords = [
            'pump', 'moon', 'gem', 'new token', 'just launched', 'fair launch',
            'presale', 'memecoin', 'meme coin', 'altcoin', 'defi', 'dex',
            'raydium', 'jupiter', 'pumpfun', 'pump.fun', 'solana', 'sol',
            'contract', 'ca:', 'ticker', 'symbol', 'address', 'stealth launch',
            'dev doxxed', 'liquidity locked', 'renounced', 'safu'
        ]
        
        # Negative indicators
        negative_keywords = [
            'scam', 'rug', 'rugpull', 'avoid', 'warning', 'caution', 'fake',
            'honeypot', 'suspicious', 'fraud', 'dump', 'exit scam'
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
    
    async def get_subreddit_info(self, subreddit_name: str) -> Dict[str, Any]:
        """Get information about a subreddit"""
        if not self.reddit:
            return {}
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            return {
                'name': subreddit.display_name,
                'title': subreddit.title,
                'description': subreddit.description,
                'subscribers': subreddit.subscribers,
                'active_users': subreddit.accounts_active,
                'created_utc': subreddit.created_utc,
                'over18': subreddit.over18,
                'public_description': subreddit.public_description
            }
            
        except Exception as e:
            self.logger.error(f"Error getting subreddit info for r/{subreddit_name}: {e}")
            return {}
    
    async def get_trending_posts(self, subreddit_names: List[str], hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get trending posts from multiple subreddits"""
        if not self.reddit:
            return []
        
        trending_posts = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for subreddit_name in subreddit_names:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                for submission in subreddit.hot(limit=10):
                    post_time = datetime.fromtimestamp(submission.created_utc)
                    
                    if post_time > cutoff_time:
                        # Calculate trending score
                        age_hours = (datetime.now() - post_time).total_seconds() / 3600
                        trending_score = submission.score / max(age_hours, 1)
                        
                        if trending_score > 10:  # Threshold for trending
                            processed_post = await self._process_submission(submission, subreddit_name)
                            if processed_post:
                                processed_post['trending_score'] = trending_score
                                trending_posts.append(processed_post)
                
            except Exception as e:
                self.logger.error(f"Error getting trending posts from r/{subreddit_name}: {e}")
                continue
        
        # Sort by trending score
        trending_posts.sort(key=lambda x: x.get('trending_score', 0), reverse=True)
        
        return trending_posts
    
    async def monitor_real_time(self, subreddit_names: List[str], keywords: List[str], callback):
        """Monitor subreddits in real-time for new posts"""
        if not self.reddit:
            self.logger.warning("No Reddit client available for monitoring")
            return
        
        # Create combined subreddit string
        subreddit_string = '+'.join(subreddit_names)
        
        try:
            subreddit = self.reddit.subreddit(subreddit_string)
            
            # Stream new submissions
            for submission in subreddit.stream.submissions(skip_existing=True, pause_after=0):
                if submission is None:
                    await asyncio.sleep(1)
                    continue
                
                try:
                    # Check if submission contains keywords
                    full_text = submission.title + " " + submission.selftext
                    if self._contains_keywords(full_text, keywords):
                        processed_post = await self._process_submission(submission, submission.subreddit.display_name)
                        if processed_post:
                            await callback(processed_post, 'reddit')
                
                except Exception as e:
                    self.logger.error(f"Error processing streamed submission: {e}")
                    continue
                
        except Exception as e:
            self.logger.error(f"Error in Reddit real-time monitoring: {e}")
            # Fallback to periodic checking
            await self._fallback_monitoring(subreddit_names, keywords, callback)
    
    async def _fallback_monitoring(self, subreddit_names: List[str], keywords: List[str], callback):
        """Fallback monitoring method using periodic checks"""
        while True:
            try:
                for subreddit_name in subreddit_names:
                    posts = await self.get_new_posts(subreddit_name, keywords, limit=10)
                    
                    for post in posts:
                        await callback(post, 'reddit')
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in fallback monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
