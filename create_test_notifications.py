"""
Create test notifications in the database for testing the notifications page.
"""
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select
from app.database import async_session_maker
from app.models.notification import Notification, NotificationType
from app.models.user import User


async def create_test_notifications():
    """Create sample notifications for testing."""
    async with async_session_maker() as db:
        # Get all users
        result = await db.execute(select(User))
        users = result.scalars().all()

        if not users:
            print("❌ No users found in database!")
            return

        print(f"✅ Found {len(users)} users")

        # Create notifications for each user
        notification_templates = [
            {
                "type": NotificationType.NEW_FOLLOWER,
                "title": "New Follower",
                "body": "Sarah Johnson started following you",
                "data": {"follower_id": "user123", "follower_name": "Sarah Johnson"}
            },
            {
                "type": NotificationType.NEW_MESSAGE,
                "title": "New Message",
                "body": "You have a new message from Ahmed",
                "data": {"conversation_id": "conv456", "sender_name": "Ahmed"}
            },
            {
                "type": NotificationType.NEW_OFFER,
                "title": "New Offer Received",
                "body": "Someone offered AED 450 for your iPhone 13 Pro",
                "data": {"offer_id": "offer789", "amount": 450, "product_name": "iPhone 13 Pro"}
            },
            {
                "type": NotificationType.PRODUCT_SOLD,
                "title": "Product Sold! 🎉",
                "body": "Your Nike Air Jordan 1 has been sold",
                "data": {"product_id": "prod123", "product_name": "Nike Air Jordan 1"}
            },
            {
                "type": NotificationType.STREAM_STARTED,
                "title": "Live Stream Started",
                "body": "TechDeals UAE just went live with exclusive gadgets!",
                "data": {"stream_id": "stream999", "streamer_name": "TechDeals UAE"}
            },
            {
                "type": NotificationType.PRICE_DROP,
                "title": "Price Drop Alert! 📉",
                "body": "MacBook Pro M2 price dropped by 20%",
                "data": {"product_id": "prod456", "product_name": "MacBook Pro M2", "old_price": 5000, "new_price": 4000}
            },
            {
                "type": NotificationType.VERIFICATION_APPROVED,
                "title": "Verification Approved ✅",
                "body": "Congratulations! Your seller verification has been approved",
                "data": {"verification_type": "seller"}
            },
            {
                "type": NotificationType.REVIEW_RECEIVED,
                "title": "New Review",
                "body": "You received a 5-star review from a buyer",
                "data": {"review_id": "review123", "rating": 5}
            },
            {
                "type": NotificationType.TRANSACTION_COMPLETED,
                "title": "Transaction Complete",
                "body": "Your payment of AED 850 has been processed",
                "data": {"transaction_id": "txn789", "amount": 850}
            },
            {
                "type": NotificationType.OFFER_ACCEPTED,
                "title": "Offer Accepted! 🎉",
                "body": "Your offer of AED 450 was accepted by the seller",
                "data": {"offer_id": "offer789", "amount": 450}
            }
        ]

        created_count = 0

        for user in users:
            print(f"\n📬 Creating notifications for {user.email}...")

            # Create 5 notifications per user (mix of read and unread)
            for i, template in enumerate(notification_templates[:5]):
                # First user gets all unread, others get mix
                is_read = False if user.email == users[0].email else (i % 2 == 0)

                # Vary the timestamps
                created_at = datetime.utcnow() - timedelta(hours=i * 2, minutes=i * 15)

                notification = Notification(
                    user_id=user.id,
                    notification_type=template["type"],
                    title=template["title"],
                    body=template["body"],
                    data=template.get("data"),
                    is_read=is_read,
                    read_at=datetime.utcnow() - timedelta(hours=1) if is_read else None,
                    created_at=created_at
                )
                db.add(notification)
                created_count += 1

                status = "📖 READ" if is_read else "🆕 UNREAD"
                print(f"  {status} - {template['title']}")

        await db.commit()

        print(f"\n✅ Successfully created {created_count} test notifications!")
        print(f"\n📊 Summary:")

        # Show counts per user
        for user in users:
            result = await db.execute(
                select(Notification)
                .where(Notification.user_id == user.id)
            )
            user_notifications = result.scalars().all()
            unread = sum(1 for n in user_notifications if not n.is_read)

            print(f"  {user.email[:30]:30} - Total: {len(user_notifications)}, Unread: {unread}")


if __name__ == "__main__":
    print("🚀 Creating test notifications...")
    asyncio.run(create_test_notifications())
