"""Notification service for push notifications and email alerts.

This module provides notification functionality using:
- Firebase Cloud Messaging (FCM) for push notifications
- Email service for email notifications
- Database storage for notification history
"""

import logging
from typing import Any

from firebase_admin import credentials, initialize_app, messaging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import DeviceToken, Notification, NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications via FCM and email."""

    def __init__(self):
        """Initialize notification service.

        Note: Firebase Admin SDK should be initialized at app startup,
        not in this __init__ method.
        """
        self.initialized = False

    @classmethod
    def initialize_firebase(cls, credentials_path: str | None = None):
        """Initialize Firebase Admin SDK.

        Args:
            credentials_path: Path to Firebase service account JSON file.
                            If None, uses default credentials.

        Note: This should be called once at app startup.
        """
        try:
            if credentials_path:
                cred = credentials.Certificate(credentials_path)
                initialize_app(cred)
            else:
                # Use default credentials from environment
                initialize_app()
            logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            raise

    async def send_notification(
        self,
        db: AsyncSession,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send notification to a single user.

        Args:
            db: Database session
            user_id: UUID of the user to notify
            notification_type: Type of notification
            title: Notification title
            body: Notification body text
            data: Additional data payload for navigation/actions

        Returns:
            True if notification was sent successfully, False otherwise
        """
        try:
            # Create notification record in database
            notification = Notification(
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                body=body,
                data=data or {},
            )
            db.add(notification)
            await db.commit()

            # Get user's FCM tokens
            result = await db.execute(select(DeviceToken).where(DeviceToken.user_id == user_id))
            device_tokens = result.scalars().all()

            if not device_tokens:
                logger.info(f"No device tokens found for user {user_id}")
                return True  # Still consider successful (notification stored)

            # Extract FCM tokens
            fcm_tokens = [token.fcm_token for token in device_tokens]

            # Send push notification
            success = await self.send_push(fcm_tokens, title, body, data or {})

            # TODO: Send email notification if user has email_enabled preference
            # await self.send_email_notification(user_id, title, body)

            return success

        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
            return False

    async def send_push(
        self,
        fcm_tokens: list[str],
        title: str,
        body: str,
        data: dict[str, Any],
    ) -> bool:
        """Send push notification via FCM to multiple tokens.

        Args:
            fcm_tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Additional data payload

        Returns:
            True if at least one message was sent successfully
        """
        try:
            # Create FCM message
            message_data = {
                "notification": messaging.Notification(
                    title=title,
                    body=body,
                ),
                "data": {k: str(v) for k, v in data.items()},  # FCM requires string values
            }

            # Send to multiple devices (multicast)
            multicast_message = messaging.MulticastMessage(
                tokens=fcm_tokens,
                notification=message_data["notification"],
                data=message_data["data"],
            )

            response = messaging.send_multicast(multicast_message)

            logger.info(
                f"FCM multicast sent: {response.success_count} successful, "
                f"{response.failure_count} failed out of {len(fcm_tokens)} tokens"
            )

            # TODO: Handle invalid tokens (remove from database)
            # for idx, result in enumerate(response.responses):
            #     if not result.success:
            #         # Log or remove invalid token
            #         pass

            return response.success_count > 0

        except Exception as e:
            logger.error(f"Error sending FCM push notification: {e}")
            return False

    async def send_bulk_notification(
        self,
        db: AsyncSession,
        user_ids: list[str],
        notification_type: NotificationType,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        """Send notification to multiple users.

        Args:
            db: Database session
            user_ids: List of user UUIDs
            notification_type: Type of notification
            title: Notification title
            body: Notification body
            data: Additional data payload

        Returns:
            Dictionary with success and failure counts
        """
        success_count = 0
        failure_count = 0

        for user_id in user_ids:
            result = await self.send_notification(
                db=db,
                user_id=user_id,
                notification_type=notification_type,
                title=title,
                body=body,
                data=data,
            )

            if result:
                success_count += 1
            else:
                failure_count += 1

        logger.info(f"Bulk notification sent: {success_count} successful, {failure_count} failed")

        return {
            "success": success_count,
            "failed": failure_count,
            "total": len(user_ids),
        }

    async def send_email_notification(
        self,
        user_email: str,
        subject: str,
        body: str,
    ) -> bool:
        """Send email notification.

        Args:
            user_email: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)

        Returns:
            True if email was sent successfully

        Note: Implement with your email service (e.g., SendGrid, AWS SES)
        """
        # TODO: Implement email service integration
        logger.info(f"Email notification to {user_email}: {subject}")
        return True


# Global notification service instance
notification_service = NotificationService()
