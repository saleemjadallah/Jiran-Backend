"""Standardized cache key naming conventions for Redis.

Provides consistent key naming across the application to prevent
conflicts and enable efficient pattern-based invalidation.

Key Format: {namespace}:{entity}:{identifier}:{field}
Examples:
    - user:profile:abc123
    - feed:discover:page:1
    - product:abc123:reviews
"""

from typing import Optional


class CacheKeys:
    """Cache key generator with standardized naming conventions.

    All methods return string keys for Redis operations.
    Use pattern methods (ending with _pattern) for cache invalidation.
    """

    # ========== User Keys ==========

    @staticmethod
    def user_session(user_id: str) -> str:
        """User session data key.

        TTL: 7 days
        Type: Hash
        """
        return f"session:{user_id}"

    @staticmethod
    def user_profile(user_id: str) -> str:
        """User profile cache key.

        TTL: 1 hour
        Type: String (JSON)
        """
        return f"user:profile:{user_id}"

    @staticmethod
    def user_pattern(user_id: str) -> str:
        """Pattern to match all user-related keys."""
        return f"user:{user_id}:*"

    # ========== Authentication Keys ==========

    @staticmethod
    def access_token(token: str) -> str:
        """Access token validation key.

        TTL: 15 minutes
        Type: String (user_id)
        """
        return f"token:{token}"

    @staticmethod
    def refresh_token(token: str) -> str:
        """Refresh token validation key.

        TTL: 7 days
        Type: String (user_id)
        """
        return f"token:refresh:{token}"

    @staticmethod
    def rate_limit(user_id: str, endpoint: str) -> str:
        """Rate limiting counter key.

        TTL: 1 minute
        Type: Counter
        """
        return f"ratelimit:{user_id}:{endpoint}"

    # ========== Feed Keys ==========

    @staticmethod
    def discover_feed(page: int) -> str:
        """Discover feed page key.

        TTL: 5 minutes
        Type: List (stream IDs)
        """
        return f"feed:discover:page:{page}"

    @staticmethod
    def community_feed(location: str, page: int) -> str:
        """Community feed page key (location-based).

        TTL: 5 minutes
        Type: List (stream IDs)
        """
        return f"feed:community:{location}:page:{page}"

    @staticmethod
    def feed_pattern() -> str:
        """Pattern to match all feed keys."""
        return "feed:*"

    # ========== Product Keys ==========

    @staticmethod
    def product(product_id: str) -> str:
        """Product details key.

        TTL: 15 minutes
        Type: String (JSON)
        """
        return f"product:{product_id}"

    @staticmethod
    def product_reviews(product_id: str) -> str:
        """Product reviews key.

        TTL: 10 minutes
        Type: List (review objects)
        """
        return f"product:{product_id}:reviews"

    @staticmethod
    def product_pattern(product_id: str) -> str:
        """Pattern to match all product-related keys."""
        return f"product:{product_id}:*"

    # ========== Search Keys ==========

    @staticmethod
    def search_results(query_hash: str, page: int) -> str:
        """Search results cache key.

        TTL: 10 minutes
        Type: List (product IDs)
        """
        return f"search:results:{query_hash}:page:{page}"

    @staticmethod
    def search_pattern() -> str:
        """Pattern to match all search keys."""
        return "search:*"

    # ========== Live Stream Keys ==========

    @staticmethod
    def stream_viewers(stream_id: str) -> str:
        """Live stream viewers tracking.

        TTL: None (cleared when stream ends)
        Type: Sorted Set (user_id with join timestamp as score)
        """
        return f"live:stream:{stream_id}:viewers"

    @staticmethod
    def stream_active_location(neighborhood: str) -> str:
        """Active streams by location.

        TTL: None (cleared when stream ends)
        Type: Set (stream IDs)
        """
        return f"live:active:location:{neighborhood}"

    # ========== Presence & Real-Time Keys ==========

    @staticmethod
    def user_presence(user_id: str) -> str:
        """User online presence status.

        TTL: 5 minutes (refreshed every 30s)
        Type: String ("online" | "away" | "offline")
        """
        return f"presence:{user_id}"

    @staticmethod
    def typing_indicator(conversation_id: str, user_id: str) -> str:
        """Typing indicator status.

        TTL: 3 seconds
        Type: String (timestamp)
        """
        return f"typing:{conversation_id}:{user_id}"

    # ========== Counters Keys ==========

    @staticmethod
    def unread_messages(user_id: str) -> str:
        """Unread message count.

        TTL: None (manual clear)
        Type: Counter
        """
        return f"unread:{user_id}:messages"

    @staticmethod
    def unread_notifications(user_id: str) -> str:
        """Unread notification count.

        TTL: None (manual clear)
        Type: Counter
        """
        return f"unread:{user_id}:notifications"

    @staticmethod
    def view_count(product_id: str) -> str:
        """Product view counter (buffered before DB write).

        TTL: 5 minutes (synced then deleted)
        Type: Counter
        """
        return f"views:{product_id}"

    @staticmethod
    def like_count(product_id: str) -> str:
        """Product like counter (buffered before DB write).

        TTL: 5 minutes
        Type: Counter
        """
        return f"likes:{product_id}"

    # ========== Aggregated Data Keys ==========

    @staticmethod
    def trending_searches() -> str:
        """Trending search queries.

        TTL: 1 hour
        Type: Sorted Set (query with search_count as score)
        """
        return "trending:searches"

    @staticmethod
    def popular_categories() -> str:
        """Popular product categories.

        TTL: 1 hour
        Type: Sorted Set (category_id with view_count as score)
        """
        return "popular:categories"

    @staticmethod
    def recommendations(user_id: str) -> str:
        """User product recommendations.

        TTL: 1 hour
        Type: List (product IDs)
        """
        return f"recommendations:{user_id}"

    @staticmethod
    def seller_analytics(seller_id: str) -> str:
        """Seller analytics data.

        TTL: 5 minutes
        Type: Hash (total_sales, avg_rating, total_views, etc.)
        """
        return f"analytics:seller:{seller_id}"

    # ========== Offers Keys ==========

    @staticmethod
    def offers_expiring() -> str:
        """Offer expiration tracking queue.

        TTL: None (background job processes)
        Type: Sorted Set (offer_id with expires_at timestamp as score)
        """
        return "offers:expiring"

    @staticmethod
    def offer_expires_at(offer_id: str) -> str:
        """Offer expiration timestamp.

        TTL: Until offer expires or is accepted
        Type: String (ISO timestamp)
        """
        return f"offer:{offer_id}:expires_at"

    # ========== Conversation Keys ==========

    @staticmethod
    def conversations_list(user_id: str) -> str:
        """User's conversation list.

        TTL: 5 minutes
        Type: List (conversation objects)
        """
        return f"conversations:{user_id}:list"

    @staticmethod
    def conversation(conversation_id: str) -> str:
        """Conversation details.

        TTL: 10 minutes
        Type: String (JSON)
        """
        return f"conversation:{conversation_id}"

    @staticmethod
    def conversation_messages(conversation_id: str) -> str:
        """Conversation messages.

        TTL: 5 minutes
        Type: List (message objects)
        """
        return f"conversation:{conversation_id}:messages"

    # ========== Temporary State Keys ==========

    @staticmethod
    def payment_session(session_id: str) -> str:
        """Payment session data.

        TTL: 30 minutes
        Type: Hash (amount, user_id, product_id, status)
        """
        return f"payment:session:{session_id}"

    @staticmethod
    def otp_code(phone_number: str) -> str:
        """OTP verification code.

        TTL: 5 minutes
        Type: String (code)
        """
        return f"otp:{phone_number}"

    @staticmethod
    def upload_progress(user_id: str, upload_id: str) -> str:
        """Video upload progress tracking.

        TTL: 24 hours
        Type: Hash (progress, status, file_path)
        """
        return f"upload:{user_id}:{upload_id}"

    # ========== Notification Keys ==========

    @staticmethod
    def notifications_list(user_id: str) -> str:
        """User's notification list.

        TTL: 5 minutes
        Type: List (notification objects)
        """
        return f"notifications:{user_id}:list"

    # ========== Helper Methods ==========

    @staticmethod
    def seller_products(seller_id: str, page: Optional[int] = None) -> str:
        """Seller's product list.

        TTL: 10 minutes
        Type: List (product IDs)
        """
        if page is not None:
            return f"seller:{seller_id}:products:page:{page}"
        return f"seller:{seller_id}:products"

    @staticmethod
    def seller_products_pattern(seller_id: str) -> str:
        """Pattern to match all seller product keys."""
        return f"seller:{seller_id}:products:*"

    @staticmethod
    def category_products(category: str, page: int) -> str:
        """Category product list.

        TTL: 10 minutes
        Type: List (product IDs)
        """
        return f"category:{category}:products:page:{page}"

    @staticmethod
    def category_pattern(category: str) -> str:
        """Pattern to match all category keys."""
        return f"category:{category}:*"
