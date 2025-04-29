# Copyright © 2025 Simone Montanari. All Rights Reserved.
# This file is part of HiKingsRome and may not be used or distributed without written permission.

from datetime import datetime, timedelta
from collections import defaultdict

class RateLimiter:
    """Class to limit request rates from users"""
    
    def __init__(self, max_requests=5, time_window=60):  # Default: 5 requests per minute
        """
        Initialize a rate limiter
        
        Args:
            max_requests (int): Maximum number of requests allowed in the time window
            time_window (int): Time window in seconds
        """
        self.requests = defaultdict(list)
        self.max_requests = max_requests
        self.time_window = time_window

    def is_allowed(self, user_id):
        """
        Check if a new request from the user is allowed
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            bool: True if request is allowed, False otherwise
        """
        now = datetime.now()
        
        # Remove old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if now - req_time < timedelta(seconds=self.time_window)
        ]
        
        # Check if user can make a new request
        if len(self.requests[user_id]) < self.max_requests:
            self.requests[user_id].append(now)
            return True
            
        return False
