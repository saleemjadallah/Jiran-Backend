"""
Analytics service for tracking events and calculating metrics.
Provides seller analytics, product analytics, and admin dashboard metrics.
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.models.transaction import Transaction
from app.models.product import Product
from app.models.stream import Stream
from app.models.user import User
from app.models.follow import Follow

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics and metrics calculation"""

    @staticmethod
    async def track_event(
        user_id: str,
        event_type: str,
        event_data: Dict,
        redis_client=None
    ) -> None:
        """
        Track user event for analytics

        Args:
            user_id: User ID
            event_type: Type of event (product_viewed, stream_viewed, etc.)
            event_data: Event metadata
            redis_client: Redis client for storage
        """
        try:
            if redis_client:
                # Store event in Redis with timestamp
                event_key = f"events:{user_id}:{event_type}"
                timestamp = datetime.utcnow().isoformat()

                await redis_client.zadd(
                    event_key,
                    {f"{timestamp}:{event_data}": datetime.utcnow().timestamp()}
                )

                # Set expiry (30 days)
                await redis_client.expire(event_key, 30 * 24 * 60 * 60)

        except Exception as e:
            logger.error(f"Error tracking event: {e}")

    @staticmethod
    async def calculate_seller_metrics(
        seller_id: str,
        start_date: date,
        end_date: date,
        db: AsyncSession
    ) -> Dict:
        """
        Calculate comprehensive seller metrics for date range

        Args:
            seller_id: Seller user ID
            start_date: Start date
            end_date: End date (inclusive)
            db: Database session

        Returns:
            dict: Seller metrics
        """
        try:
            # Convert dates to datetime for comparison
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # 1. Sales metrics
            sales_query = select(
                func.count(Transaction.id).label("total_orders"),
                func.sum(Transaction.amount).label("total_revenue"),
                func.avg(Transaction.amount).label("avg_order_value"),
                func.sum(Transaction.platform_fee).label("platform_fees")
            ).where(
                and_(
                    Transaction.seller_id == seller_id,
                    Transaction.status == "completed",
                    Transaction.created_at >= start_datetime,
                    Transaction.created_at <= end_datetime
                )
            )

            sales_result = await db.execute(sales_query)
            sales_data = sales_result.first()

            total_orders = sales_data.total_orders or 0
            total_revenue = float(sales_data.total_revenue or 0)
            avg_order_value = float(sales_data.avg_order_value or 0)
            platform_fees = float(sales_data.platform_fees or 0)

            # 2. Traffic metrics
            products_query = select(
                func.sum(Product.view_count).label("product_views")
            ).where(
                and_(
                    Product.seller_id == seller_id,
                    Product.created_at >= start_datetime,
                    Product.created_at <= end_datetime
                )
            )

            products_result = await db.execute(products_query)
            products_data = products_result.first()
            product_views = products_data.product_views or 0

            # Stream views
            streams_query = select(
                func.sum(Stream.total_views).label("stream_views")
            ).where(
                and_(
                    Stream.user_id == seller_id,
                    Stream.created_at >= start_datetime,
                    Stream.created_at <= end_datetime
                )
            )

            streams_result = await db.execute(streams_query)
            streams_data = streams_result.first()
            stream_views = streams_data.stream_views or 0

            # 3. Engagement metrics
            # New followers in period
            followers_query = select(
                func.count(Follow.id).label("new_followers")
            ).where(
                and_(
                    Follow.following_id == seller_id,
                    Follow.created_at >= start_datetime,
                    Follow.created_at <= end_datetime
                )
            )

            followers_result = await db.execute(followers_query)
            new_followers = followers_result.scalar() or 0

            # Get seller info for rating
            seller_query = select(User).where(User.id == seller_id)
            seller_result = await db.execute(seller_query)
            seller = seller_result.scalar_one_or_none()
            average_rating = float(seller.rating) if seller and seller.rating else 0.0

            # 4. Top products
            top_products_query = select(
                Product.id,
                Product.title,
                Product.price,
                Product.view_count,
                Product.like_count,
                func.count(Transaction.id).label("sales_count"),
                func.sum(Transaction.amount).label("revenue")
            ).outerjoin(
                Transaction,
                and_(
                    Transaction.product_id == Product.id,
                    Transaction.status == "completed"
                )
            ).where(
                and_(
                    Product.seller_id == seller_id,
                    Product.created_at >= start_datetime,
                    Product.created_at <= end_datetime
                )
            ).group_by(
                Product.id
            ).order_by(
                func.count(Transaction.id).desc()
            ).limit(10)

            top_products_result = await db.execute(top_products_query)
            top_products = [
                {
                    "id": str(row.id),
                    "title": row.title,
                    "price": float(row.price),
                    "view_count": row.view_count,
                    "like_count": row.like_count,
                    "sales_count": row.sales_count or 0,
                    "revenue": float(row.revenue or 0)
                }
                for row in top_products_result.all()
            ]

            # 5. Top categories
            top_categories_query = select(
                Product.category,
                func.count(Product.id).label("product_count"),
                func.count(Transaction.id).label("sales_count"),
                func.sum(Transaction.amount).label("revenue")
            ).outerjoin(
                Transaction,
                and_(
                    Transaction.product_id == Product.id,
                    Transaction.status == "completed"
                )
            ).where(
                and_(
                    Product.seller_id == seller_id,
                    Product.created_at >= start_datetime,
                    Product.created_at <= end_datetime
                )
            ).group_by(
                Product.category
            ).order_by(
                func.count(Transaction.id).desc()
            ).limit(10)

            top_categories_result = await db.execute(top_categories_query)
            top_categories = [
                {
                    "category": row.category,
                    "product_count": row.product_count,
                    "sales_count": row.sales_count or 0,
                    "revenue": float(row.revenue or 0)
                }
                for row in top_categories_result.all()
            ]

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "sales": {
                    "total_orders": total_orders,
                    "total_revenue": total_revenue,
                    "average_order_value": round(avg_order_value, 2),
                    "platform_fees": round(platform_fees, 2)
                },
                "traffic": {
                    "product_views": int(product_views),
                    "stream_views": int(stream_views),
                    "total_views": int(product_views + stream_views)
                },
                "engagement": {
                    "new_followers": new_followers,
                    "average_rating": round(average_rating, 2)
                },
                "top_products": top_products,
                "top_categories": top_categories
            }

        except Exception as e:
            logger.error(f"Error calculating seller metrics: {e}")
            raise

    @staticmethod
    async def calculate_conversion_rate(
        seller_id: str,
        start_date: date,
        end_date: date,
        db: AsyncSession
    ) -> float:
        """
        Calculate conversion rate: sales / total views

        Args:
            seller_id: Seller ID
            start_date: Start date
            end_date: End date
            db: Database session

        Returns:
            float: Conversion rate (0.0 to 1.0)
        """
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # Get total sales
            sales_query = select(
                func.count(Transaction.id)
            ).where(
                and_(
                    Transaction.seller_id == seller_id,
                    Transaction.status == "completed",
                    Transaction.created_at >= start_datetime,
                    Transaction.created_at <= end_datetime
                )
            )

            sales_result = await db.execute(sales_query)
            total_sales = sales_result.scalar() or 0

            # Get total views (products + streams)
            products_query = select(
                func.sum(Product.view_count)
            ).where(
                and_(
                    Product.seller_id == seller_id,
                    Product.created_at >= start_datetime,
                    Product.created_at <= end_datetime
                )
            )

            products_result = await db.execute(products_query)
            product_views = products_result.scalar() or 0

            streams_query = select(
                func.sum(Stream.total_views)
            ).where(
                and_(
                    Stream.user_id == seller_id,
                    Stream.created_at >= start_datetime,
                    Stream.created_at <= end_datetime
                )
            )

            streams_result = await db.execute(streams_query)
            stream_views = streams_result.scalar() or 0

            total_views = product_views + stream_views

            if total_views == 0:
                return 0.0

            return round(total_sales / total_views, 4)

        except Exception as e:
            logger.error(f"Error calculating conversion rate: {e}")
            return 0.0

    @staticmethod
    async def get_product_analytics(
        product_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Get detailed analytics for a specific product

        Args:
            product_id: Product ID
            db: Database session

        Returns:
            dict: Product analytics
        """
        try:
            # Get product
            product_query = select(Product).where(Product.id == product_id)
            product_result = await db.execute(product_query)
            product = product_result.scalar_one_or_none()

            if not product:
                return {}

            # Get sales data
            sales_query = select(
                func.count(Transaction.id).label("total_sales"),
                func.sum(Transaction.amount).label("total_revenue")
            ).where(
                and_(
                    Transaction.product_id == product_id,
                    Transaction.status == "completed"
                )
            )

            sales_result = await db.execute(sales_query)
            sales_data = sales_result.first()

            total_sales = sales_data.total_sales or 0
            total_revenue = float(sales_data.total_revenue or 0)

            # Calculate conversion rate
            conversion_rate = 0.0
            if product.view_count > 0:
                conversion_rate = round(total_sales / product.view_count, 4)

            return {
                "product_id": str(product.id),
                "title": product.title,
                "price": float(product.price),
                "views": {
                    "total_views": product.view_count,
                    "unique_viewers": product.view_count  # TODO: Track unique viewers
                },
                "engagement": {
                    "likes": product.like_count,
                    "saves": 0  # TODO: Implement saves tracking
                },
                "sales": {
                    "total_sales": total_sales,
                    "total_revenue": total_revenue,
                    "conversion_rate": conversion_rate
                },
                "created_at": product.created_at.isoformat() if product.created_at else None
            }

        except Exception as e:
            logger.error(f"Error getting product analytics: {e}")
            raise

    @staticmethod
    async def get_stream_analytics(
        stream_id: str,
        db: AsyncSession
    ) -> Dict:
        """
        Get detailed analytics for a specific stream

        Args:
            stream_id: Stream ID
            db: Database session

        Returns:
            dict: Stream analytics
        """
        try:
            # Get stream
            stream_query = select(Stream).where(Stream.id == stream_id)
            stream_result = await db.execute(stream_query)
            stream = stream_result.scalar_one_or_none()

            if not stream:
                return {}

            # Calculate duration
            duration_seconds = 0
            if stream.started_at and stream.ended_at:
                duration_seconds = int((stream.ended_at - stream.started_at).total_seconds())

            return {
                "stream_id": str(stream.id),
                "title": stream.title,
                "status": stream.status,
                "duration_seconds": duration_seconds,
                "viewers": {
                    "peak_concurrent": stream.viewer_count,  # Current or peak
                    "total_unique": stream.total_views,
                    "average_watch_time": 0  # TODO: Implement watch time tracking
                },
                "engagement": {
                    "chat_messages": 0,  # TODO: Implement chat message tracking
                    "reactions": 0,  # TODO: Implement reactions tracking
                    "likes": 0  # TODO: Implement stream likes
                },
                "products": {
                    "products_tagged": 0,  # TODO: Get from stream_products table
                    "product_clicks": 0,  # TODO: Track product clicks
                    "sales_from_stream": 0  # TODO: Track sales attribution
                },
                "started_at": stream.started_at.isoformat() if stream.started_at else None,
                "ended_at": stream.ended_at.isoformat() if stream.ended_at else None
            }

        except Exception as e:
            logger.error(f"Error getting stream analytics: {e}")
            raise

    @staticmethod
    async def get_admin_overview(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        db: AsyncSession = None
    ) -> Dict:
        """
        Get platform-wide admin overview metrics

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            db: Database session

        Returns:
            dict: Admin overview metrics
        """
        try:
            # Default to last 30 days if not specified
            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())

            # Total users by role
            users_query = select(
                User.role,
                func.count(User.id).label("count")
            ).group_by(User.role)

            users_result = await db.execute(users_query)
            user_counts = {row.role: row.count for row in users_result.all()}

            # Total products
            products_query = select(func.count(Product.id))
            products_result = await db.execute(products_query)
            total_products = products_result.scalar() or 0

            # Total transactions
            transactions_query = select(
                func.count(Transaction.id).label("total_transactions"),
                func.sum(Transaction.amount).label("gmv"),
                func.sum(Transaction.platform_fee).label("platform_revenue")
            ).where(Transaction.status == "completed")

            transactions_result = await db.execute(transactions_query)
            trans_data = transactions_result.first()

            total_transactions = trans_data.total_transactions or 0
            gmv = float(trans_data.gmv or 0)
            platform_revenue = float(trans_data.platform_revenue or 0)

            # Active users (users who created content or made transactions in period)
            active_users_query = select(func.count(func.distinct(User.id))).select_from(User).join(
                Product, Product.seller_id == User.id, isouter=True
            ).where(
                or_(
                    and_(
                        Product.created_at >= start_datetime,
                        Product.created_at <= end_datetime
                    ),
                    User.last_login_at >= start_datetime
                )
            )

            active_users_result = await db.execute(active_users_query)
            active_users = active_users_result.scalar() or 0

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "users": {
                    "total": sum(user_counts.values()),
                    "by_role": user_counts,
                    "active": active_users
                },
                "content": {
                    "total_products": total_products,
                    "total_streams": 0  # TODO: Add streams count
                },
                "transactions": {
                    "total": total_transactions,
                    "gmv": gmv,
                    "platform_revenue": platform_revenue
                }
            }

        except Exception as e:
            logger.error(f"Error getting admin overview: {e}")
            raise


# Global analytics service instance
analytics_service = AnalyticsService()
