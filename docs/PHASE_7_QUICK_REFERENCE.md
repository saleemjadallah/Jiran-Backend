# Phase 7: Quick Reference Guide
## Social Features API - Cheat Sheet

---

## 🔗 Follow System

### Follow User
```bash
POST /api/v1/users/{user_id}/follow
Authorization: Bearer {token}

Response: { "following": true }
```

### Unfollow User
```bash
DELETE /api/v1/users/{user_id}/follow
Authorization: Bearer {token}

Response: { "following": false }
```

### Get Followers
```bash
GET /api/v1/users/{user_id}/followers?page=1&per_page=20&search=john
Authorization: Bearer {token}
```

### Get Following
```bash
GET /api/v1/users/{user_id}/following?page=1&per_page=20
Authorization: Bearer {token}
```

### Check Relationship
```bash
GET /api/v1/users/{user_id}/relationship
Authorization: Bearer {token}

Response: {
  "following": true,
  "followed_by": false,
  "blocked": false,
  "can_message": true
}
```

---

## 🔔 Notifications

### Get Notifications
```bash
GET /api/v1/notifications?unread_only=false&page=1&per_page=20
Authorization: Bearer {token}
```

### Get Unread Count
```bash
GET /api/v1/notifications/unread-count
Authorization: Bearer {token}

Response: { "unread_count": 7 }
```

### Mark as Read
```bash
PATCH /api/v1/notifications/{notification_id}/read
Authorization: Bearer {token}
```

### Mark All as Read
```bash
PATCH /api/v1/notifications/read-all
Authorization: Bearer {token}
```

### Register Device for Push
```bash
POST /api/v1/notifications/register-device
Authorization: Bearer {token}
Content-Type: application/json

{
  "fcm_token": "dXvY9z...",
  "platform": "ios",
  "device_id": "unique-device-id"
}
```

### Unregister Device
```bash
DELETE /api/v1/notifications/unregister-device
Authorization: Bearer {token}
Content-Type: application/json

{ "device_id": "unique-device-id" }
```

---

## 📱 Notification Types

| Type | Description | Navigate To |
|------|-------------|-------------|
| `new_follower` | Someone followed you | User profile |
| `new_message` | New message received | Conversation |
| `new_offer` | New offer on product | Product detail |
| `offer_accepted` | Offer accepted | Transaction |
| `stream_started` | User went live | Live stream |
| `product_sold` | Product sold | Transaction |
| `review_received` | Got a review | Profile |
| `price_drop` | Wishlist price drop | Product detail |

---

## 📊 Activity Feed

### Get Activity Feed
```bash
GET /api/v1/activity?page=1&per_page=20
Authorization: Bearer {token}

# Returns activities from users you follow
```

### Get Personal Activity
```bash
GET /api/v1/activity/me?page=1&per_page=20
Authorization: Bearer {token}

# Returns your own activities
```

### Activity Types

| Type | Description |
|------|-------------|
| `went_live` | User started streaming |
| `stream_ended` | User ended stream |
| `new_product` | User posted product |
| `product_sold` | User sold product |
| `new_follower` | User got follower |
| `review_received` | User got 5-star review |
| `milestone` | User hit milestone |

---

## 🔧 Flutter Setup Checklist

### Dependencies
```yaml
dependencies:
  firebase_messaging: ^14.7.9
  firebase_core: ^2.24.2
  flutter_local_notifications: ^16.3.0
  flutter_riverpod: ^2.4.9
  dio: ^5.4.0
  freezed_annotation: ^2.4.1
```

### Firebase Setup
1. ✅ Add `google-services.json` to `android/app/`
2. ✅ Add `GoogleService-Info.plist` to `ios/Runner/`
3. ✅ Generate Firebase service account key
4. ✅ Set `FIREBASE_CREDENTIALS_PATH` in backend `.env`
5. ✅ Initialize Firebase in `main.dart`

### Backend Migration
```bash
cd backend
alembic upgrade head
```

---

## 📝 Flutter Code Templates

### Follow Button
```dart
FollowButton(
  userId: "user_uuid",
  onFollowStateChanged: () {
    // Refresh UI if needed
  },
)
```

### Notification Badge
```dart
Consumer(
  builder: (context, ref, child) {
    final unreadCount = ref.watch(unreadNotificationCountProvider);
    return Badge(
      label: Text('$unreadCount'),
      isLabelVisible: unreadCount > 0,
      child: Icon(Icons.notifications),
    );
  },
)
```

### Activity Feed
```dart
final activitiesAsync = ref.watch(activityFeedProvider());

activitiesAsync.when(
  data: (activities) => ListView.builder(...),
  loading: () => CircularProgressIndicator(),
  error: (error, stack) => Text('Error: $error'),
)
```

---

## 🧪 Testing Endpoints with cURL

### Follow User
```bash
curl -X POST http://localhost:8000/api/v1/users/{user_id}/follow \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Notifications
```bash
curl -X GET "http://localhost:8000/api/v1/notifications?page=1&per_page=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Unread Count
```bash
curl -X GET http://localhost:8000/api/v1/notifications/unread-count \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Register Device
```bash
curl -X POST http://localhost:8000/api/v1/notifications/register-device \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fcm_token": "test_token_123",
    "platform": "ios",
    "device_id": "test_device_456"
  }'
```

### Get Activity Feed
```bash
curl -X GET "http://localhost:8000/api/v1/activity?page=1&per_page=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🐛 Common Issues & Solutions

### Issue: FCM token not received
**Solution:**
- Check Firebase configuration files
- Verify Firebase SDK initialization
- Check iOS permissions in Info.plist
- Check Android permissions in AndroidManifest.xml

### Issue: Notifications not showing
**Solution:**
- Request notification permissions (iOS)
- Check notification channel (Android)
- Verify device token registered with backend
- Check backend FCM credentials

### Issue: Follow count not updating
**Solution:**
```dart
// Invalidate provider cache
ref.invalidate(followStateProvider(userId));
ref.invalidate(followersProvider);
```

### Issue: 401 Unauthorized
**Solution:**
- Check if access token is expired
- Refresh token if needed
- Ensure token included in Authorization header

---

## 📞 Support

**Backend URL:** `http://localhost:8000/api/v1`
**API Docs:** `http://localhost:8000/docs`
**Migration File:** `alembic/versions/be5f12795a69_phase_7_social_features_follow_.py`

---

**Last Updated:** October 18, 2025
