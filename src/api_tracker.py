"""
API Usage Tracker Module
Tracks and limits API calls to prevent quota exhaustion
Version: 1.0.0
"""

import time
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from src.logging_config import get_logger

logger = get_logger(__name__)

class APIUsageTracker:
    """Track API usage and enforce limits to prevent quota exhaustion"""

    def __init__(self, tracker_file="api_usage.json"):
        self.tracker_file = Path(tracker_file)
        self.usage_data = self._load_usage_data()

        # Daily limits (adjust based on your RapidAPI plan)
        self.daily_limit = int(os.getenv('RAPIDAPI_DAILY_LIMIT', 100))
        self.hourly_limit = int(os.getenv('RAPIDAPI_HOURLY_LIMIT', 20))

        # Rate limiting
        self.min_request_interval = 2  # Minimum seconds between requests
        self.last_request_time = 0

    def _load_usage_data(self):
        """Load usage data from file"""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'daily_count': 0,
            'hourly_count': 0,
            'last_reset_day': datetime.now().strftime('%Y-%m-%d'),
            'last_reset_hour': datetime.now().strftime('%Y-%m-%d %H'),
            'total_requests': 0,
            'failed_requests': 0
        }

    def _save_usage_data(self):
        """Save usage data to file"""
        try:
            with open(self.tracker_file, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save API usage data: {e}")

    def _reset_counters_if_needed(self):
        """Reset daily/hourly counters if time period has passed"""
        now = datetime.now()
        current_day = now.strftime('%Y-%m-%d')
        current_hour = now.strftime('%Y-%m-%d %H')

        # Reset daily counter
        if self.usage_data['last_reset_day'] != current_day:
            logger.info(f"Resetting daily API counter. Previous: {self.usage_data['daily_count']}")
            self.usage_data['daily_count'] = 0
            self.usage_data['last_reset_day'] = current_day

        # Reset hourly counter
        if self.usage_data['last_reset_hour'] != current_hour:
            logger.info(f"Resetting hourly API counter. Previous: {self.usage_data['hourly_count']}")
            self.usage_data['hourly_count'] = 0
            self.usage_data['last_reset_hour'] = current_hour

        self._save_usage_data()

    def can_make_request(self):
        """Check if we can make an API request without exceeding limits"""
        self._reset_counters_if_needed()

        # Check daily limit
        if self.usage_data['daily_count'] >= self.daily_limit:
            logger.warning(f"Daily API limit reached: {self.usage_data['daily_count']}/{self.daily_limit}")
            return False, "Daily API limit reached. Please try again tomorrow."

        # Check hourly limit
        if self.usage_data['hourly_count'] >= self.hourly_limit:
            logger.warning(f"Hourly API limit reached: {self.usage_data['hourly_count']}/{self.hourly_limit}")
            return False, "Hourly API limit reached. Please try again in the next hour."

        # Check rate limiting (minimum interval between requests)
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            logger.info(f"Rate limiting: waiting {wait_time:.1f}s")
            time.sleep(wait_time)

        return True, "OK"

    def record_request(self, success=True):
        """Record that an API request was made"""
        self._reset_counters_if_needed()

        self.usage_data['daily_count'] += 1
        self.usage_data['hourly_count'] += 1
        self.usage_data['total_requests'] += 1

        if not success:
            self.usage_data['failed_requests'] += 1

        self.last_request_time = time.time()
        self._save_usage_data()

        logger.info(
            f"API request recorded. "
            f"Daily: {self.usage_data['daily_count']}/{self.daily_limit}, "
            f"Hourly: {self.usage_data['hourly_count']}/{self.hourly_limit}, "
            f"Total: {self.usage_data['total_requests']}"
        )

    def get_usage_stats(self):
        """Get current usage statistics"""
        self._reset_counters_if_needed()
        return {
            'daily': {
                'used': self.usage_data['daily_count'],
                'limit': self.daily_limit,
                'remaining': max(0, self.daily_limit - self.usage_data['daily_count'])
            },
            'hourly': {
                'used': self.usage_data['hourly_count'],
                'limit': self.hourly_limit,
                'remaining': max(0, self.hourly_limit - self.usage_data['hourly_count'])
            },
            'total_requests': self.usage_data['total_requests'],
            'failed_requests': self.usage_data['failed_requests'],
            'success_rate': (
                ((self.usage_data['total_requests'] - self.usage_data['failed_requests']) /
                 self.usage_data['total_requests'] * 100)
                if self.usage_data['total_requests'] > 0 else 0
            )
        }

# Global tracker instance
api_tracker = APIUsageTracker()