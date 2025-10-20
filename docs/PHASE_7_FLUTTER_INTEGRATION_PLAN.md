# Phase 7: Flutter Frontend Integration Plan
## Social Features - Follow System, Notifications, Activity Feed

**Last Updated:** October 18, 2025
**Backend Version:** Phase 7 Complete
**Flutter Implementation:** Ready for Development

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [API Endpoints Reference](#api-endpoints-reference)
4. [Data Models](#data-models)
5. [Feature Implementation Guide](#feature-implementation-guide)
6. [Firebase Cloud Messaging Setup](#firebase-cloud-messaging-setup)
7. [Testing Checklist](#testing-checklist)
8. [Best Practices](#best-practices)

---

## Overview

Phase 7 adds social features to Souk Loop:
- **Follow System**: Follow/unfollow users, view followers/following
- **Notifications**: Push notifications + in-app notification center
- **Activity Feed**: See what users you follow are doing

### Backend Status
✅ All models created
✅ All endpoints implemented
✅ Database migration generated
✅ FCM service configured

### Frontend Tasks
- [ ] Implement Follow/Unfollow UI
- [ ] Build Notification Center
- [ ] Create Activity Feed
- [ ] Setup FCM in Flutter
- [ ] Add notification handlers

---

## Prerequisites

### 1. Backend Setup
```bash
# Apply database migration
cd backend
alembic upgrade head

# Verify migration applied
alembic current
# Should show: be5f12795a69 (head) - Phase 7: Social features
```

### 2. Environment Variables
Add to `backend/.env`:
```bash
# Firebase Cloud Messaging (for push notifications)
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-service-account.json
```

### 3. Flutter Dependencies
Add to `frontend/pubspec.yaml`:
```yaml
dependencies:
  # Existing dependencies...

  # For push notifications
  firebase_messaging: ^14.7.9
  firebase_core: ^2.24.2

  # For local notifications
  flutter_local_notifications: ^16.3.0

  # For state management (if not already added)
  flutter_riverpod: ^2.4.9
  riverpod_annotation: ^2.3.3

  # For HTTP requests (if not already added)
  dio: ^5.4.0
  retrofit: ^4.0.3

  # For JSON serialization (if not already added)
  freezed_annotation: ^2.4.1
  json_annotation: ^4.8.1

dev_dependencies:
  # Code generation
  build_runner: ^2.4.7
  freezed: ^2.4.6
  json_serializable: ^6.7.1
  retrofit_generator: ^8.0.6
```

---

## API Endpoints Reference

### Follow System Endpoints

#### 1. Follow User
```http
POST /api/v1/users/{user_id}/follow
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully followed user",
  "following": true
}
```

**Use Cases:**
- Follow button on user profile
- Follow from search results
- Follow from activity feed

---

#### 2. Unfollow User
```http
DELETE /api/v1/users/{user_id}/follow
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Successfully unfollowed user",
  "following": false
}
```

---

#### 3. Get Followers List
```http
GET /api/v1/users/{user_id}/followers?page=1&per_page=20&search=john
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "user": {
        "id": "uuid",
        "username": "johndoe",
        "full_name": "John Doe",
        "avatar_url": "https://...",
        "is_verified": true,
        "neighborhood": "Dubai Marina",
        "follower_count": 1234,
        "following_count": 567
      },
      "followed_at": "2025-10-15T12:00:00Z",
      "is_mutual": true
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 20,
  "has_more": true
}
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)
- `search`: Filter by username (optional)

**Use Cases:**
- Followers list screen
- Search within followers
- Mutual followers indicator

---

#### 4. Get Following List
```http
GET /api/v1/users/{user_id}/following?page=1&per_page=20&search=jane
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "user": {
        "id": "uuid",
        "username": "janedoe",
        "full_name": "Jane Doe",
        "avatar_url": "https://...",
        "is_verified": true,
        "neighborhood": "JBR",
        "follower_count": 890,
        "following_count": 234
      },
      "followed_at": "2025-10-14T10:30:00Z",
      "follows_back": false
    }
  ],
  "total": 45,
  "page": 1,
  "per_page": 20,
  "has_more": true
}
```

**Use Cases:**
- Following list screen
- Check who follows back
- Unfollow from list

---

#### 5. Get Relationship Status
```http
GET /api/v1/users/{user_id}/relationship
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "following": true,
    "followed_by": false,
    "blocked": false,
    "blocked_by": false,
    "can_message": true
  }
}
```

**Use Cases:**
- Determine follow button state (Follow/Following/Follow Back)
- Check if user can send messages
- Show relationship badges

---

### Notification Endpoints

#### 6. Get Notifications
```http
GET /api/v1/notifications?unread_only=false&page=1&per_page=20
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "notif_uuid",
      "user_id": "user_uuid",
      "notification_type": "new_follower",
      "title": "New Follower",
      "body": "johndoe started following you",
      "data": {
        "type": "new_follower",
        "follower_id": "uuid",
        "follower_username": "johndoe"
      },
      "is_read": false,
      "read_at": null,
      "created_at": "2025-10-18T14:30:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "per_page": 20,
  "has_more": true
}
```

**Notification Types:**
- `new_follower` - Someone followed you
- `new_message` - New message received
- `new_offer` - New offer on your product
- `offer_accepted` - Your offer was accepted
- `offer_declined` - Your offer was declined
- `offer_countered` - Seller countered your offer
- `product_sold` - Your product sold
- `transaction_completed` - Transaction completed
- `review_received` - Someone reviewed you
- `stream_started` - Someone you follow went live
- `stream_ended` - Stream ended
- `price_drop` - Product on wishlist had price drop
- `verification_approved` - Verification approved
- `verification_rejected` - Verification rejected
- `system_announcement` - System announcements

---

#### 7. Get Unread Count
```http
GET /api/v1/notifications/unread-count
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "unread_count": 7
}
```

**Use Cases:**
- Notification badge on bottom navigation
- Header notification icon badge

---

#### 8. Mark Notification as Read
```http
PATCH /api/v1/notifications/{notification_id}/read
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "notif_uuid",
    "is_read": true,
    "read_at": "2025-10-18T15:00:00Z"
  }
}
```

---

#### 9. Mark All as Read
```http
PATCH /api/v1/notifications/read-all
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "All notifications marked as read"
  }
}
```

---

#### 10. Register Device for Push Notifications
```http
POST /api/v1/notifications/register-device
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "fcm_token": "dXvY9z...",
  "platform": "ios",
  "device_id": "unique-device-id"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Device registered successfully"
}
```

**When to Call:**
- After user logs in
- When FCM token refreshes
- On app startup (if user logged in)

---

#### 11. Unregister Device
```http
DELETE /api/v1/notifications/unregister-device
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "device_id": "unique-device-id"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "Device unregistered successfully"
  }
}
```

**When to Call:**
- On user logout
- When user disables notifications

---

#### 12. Get Notification Settings
```http
GET /api/v1/notifications/settings
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "push_enabled": true,
    "email_enabled": true,
    "notification_types": {
      "new_follower": true,
      "new_message": true,
      "new_offer": true,
      "stream_started": true,
      "price_drop": false
    }
  }
}
```

---

#### 13. Update Notification Settings
```http
PATCH /api/v1/notifications/settings
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "push_enabled": true,
  "email_enabled": false,
  "notification_types": {
    "new_follower": true,
    "new_message": true,
    "stream_started": false
  }
}
```

---

### Activity Feed Endpoints

#### 14. Get Activity Feed
```http
GET /api/v1/activity?page=1&per_page=20
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "activity_uuid",
      "user_id": "user_uuid",
      "activity_type": "went_live",
      "related_stream_id": "stream_uuid",
      "meta_data": {
        "stream_title": "Flash Sale!"
      },
      "created_at": "2025-10-18T14:00:00Z",
      "user": {
        "id": "user_uuid",
        "username": "seller123",
        "full_name": "Ahmed Hassan",
        "avatar_url": "https://...",
        "is_verified": true
      },
      "related_stream": {
        "id": "stream_uuid",
        "title": "Flash Sale!",
        "thumbnail_url": "https://...",
        "status": "live"
      }
    }
  ],
  "page": 1,
  "per_page": 20,
  "total": 87,
  "has_more": true
}
```

**Activity Types:**
- `went_live` - User started a live stream
- `stream_ended` - User ended a stream
- `new_product` - User posted a new product
- `product_sold` - User sold a product
- `new_follower` - User got a new follower
- `review_received` - User received a 5-star review
- `milestone` - User achieved a milestone (100 sales, etc.)

---

#### 15. Get Personal Activity History
```http
GET /api/v1/activity/me?page=1&per_page=20
Authorization: Bearer {access_token}
```

**Response:** Same format as activity feed, but only for current user's activities.

---

## Data Models

### Follow Models

```dart
// lib/features/social/models/user_profile_summary.dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'user_profile_summary.freezed.dart';
part 'user_profile_summary.g.dart';

@freezed
class UserProfileSummary with _$UserProfileSummary {
  const factory UserProfileSummary({
    required String id,
    required String username,
    required String fullName,
    String? avatarUrl,
    required bool isVerified,
    String? neighborhood,
    required int followerCount,
    required int followingCount,
  }) = _UserProfileSummary;

  factory UserProfileSummary.fromJson(Map<String, dynamic> json) =>
      _$UserProfileSummaryFromJson(json);
}

@freezed
class FollowerResponse with _$FollowerResponse {
  const factory FollowerResponse({
    required UserProfileSummary user,
    required DateTime followedAt,
    required bool isMutual,
  }) = _FollowerResponse;

  factory FollowerResponse.fromJson(Map<String, dynamic> json) =>
      _$FollowerResponseFromJson(json);
}

@freezed
class FollowingResponse with _$FollowingResponse {
  const factory FollowingResponse({
    required UserProfileSummary user,
    required DateTime followedAt,
    required bool followsBack,
  }) = _FollowingResponse;

  factory FollowingResponse.fromJson(Map<String, dynamic> json) =>
      _$FollowingResponseFromJson(json);
}

@freezed
class RelationshipData with _$RelationshipData {
  const factory RelationshipData({
    required bool following,
    required bool followedBy,
    required bool blocked,
    required bool blockedBy,
    required bool canMessage,
  }) = _RelationshipData;

  factory RelationshipData.fromJson(Map<String, dynamic> json) =>
      _$RelationshipDataFromJson(json);
}
```

### Notification Models

```dart
// lib/features/notifications/models/notification_model.dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'notification_model.freezed.dart';
part 'notification_model.g.dart';

enum NotificationType {
  @JsonValue('new_follower')
  newFollower,
  @JsonValue('new_message')
  newMessage,
  @JsonValue('new_offer')
  newOffer,
  @JsonValue('offer_accepted')
  offerAccepted,
  @JsonValue('offer_declined')
  offerDeclined,
  @JsonValue('offer_countered')
  offerCountered,
  @JsonValue('product_sold')
  productSold,
  @JsonValue('transaction_completed')
  transactionCompleted,
  @JsonValue('review_received')
  reviewReceived,
  @JsonValue('stream_started')
  streamStarted,
  @JsonValue('stream_ended')
  streamEnded,
  @JsonValue('price_drop')
  priceDrop,
  @JsonValue('verification_approved')
  verificationApproved,
  @JsonValue('verification_rejected')
  verificationRejected,
  @JsonValue('system_announcement')
  systemAnnouncement,
}

@freezed
class NotificationModel with _$NotificationModel {
  const factory NotificationModel({
    required String id,
    required String userId,
    required NotificationType notificationType,
    required String title,
    required String body,
    Map<String, dynamic>? data,
    required bool isRead,
    DateTime? readAt,
    required DateTime createdAt,
  }) = _NotificationModel;

  factory NotificationModel.fromJson(Map<String, dynamic> json) =>
      _$NotificationModelFromJson(json);
}
```

### Activity Models

```dart
// lib/features/activity/models/activity_model.dart
import 'package:freezed_annotation/freezed_annotation.dart';

part 'activity_model.freezed.dart';
part 'activity_model.g.dart';

enum ActivityType {
  @JsonValue('went_live')
  wentLive,
  @JsonValue('stream_ended')
  streamEnded,
  @JsonValue('new_product')
  newProduct,
  @JsonValue('product_sold')
  productSold,
  @JsonValue('new_follower')
  newFollower,
  @JsonValue('review_received')
  reviewReceived,
  @JsonValue('milestone')
  milestone,
}

@freezed
class ActivityModel with _$ActivityModel {
  const factory ActivityModel({
    required String id,
    required String userId,
    required ActivityType activityType,
    String? relatedProductId,
    String? relatedStreamId,
    String? relatedUserId,
    Map<String, dynamic>? metaData,
    required DateTime createdAt,
    // Populated from joins
    Map<String, dynamic>? user,
    Map<String, dynamic>? relatedProduct,
    Map<String, dynamic>? relatedStream,
    Map<String, dynamic>? relatedUser,
  }) = _ActivityModel;

  factory ActivityModel.fromJson(Map<String, dynamic> json) =>
      _$ActivityModelFromJson(json);
}
```

---

## Feature Implementation Guide

### Feature 1: Follow/Unfollow System

#### Step 1: Create API Service

```dart
// lib/core/services/social_api_service.dart
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';
import 'package:souk_loop/features/social/models/user_profile_summary.dart';

part 'social_api_service.g.dart';

@RestApi(baseUrl: "https://api.soukloop.com/api/v1")
abstract class SocialApiService {
  factory SocialApiService(Dio dio, {String baseUrl}) = _SocialApiService;

  @POST("/users/{userId}/follow")
  Future<Map<String, dynamic>> followUser(@Path("userId") String userId);

  @DELETE("/users/{userId}/follow")
  Future<Map<String, dynamic>> unfollowUser(@Path("userId") String userId);

  @GET("/users/{userId}/followers")
  Future<Map<String, dynamic>> getFollowers(
    @Path("userId") String userId,
    @Query("page") int page,
    @Query("per_page") int perPage,
    @Query("search") String? search,
  );

  @GET("/users/{userId}/following")
  Future<Map<String, dynamic>> getFollowing(
    @Path("userId") String userId,
    @Query("page") int page,
    @Query("per_page") int perPage,
    @Query("search") String? search,
  );

  @GET("/users/{userId}/relationship")
  Future<Map<String, dynamic>> getRelationship(@Path("userId") String userId);
}
```

#### Step 2: Create Riverpod Provider

```dart
// lib/features/social/providers/social_provider.dart
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:souk_loop/core/services/social_api_service.dart';
import 'package:souk_loop/features/social/models/user_profile_summary.dart';

part 'social_provider.g.dart';

@riverpod
class FollowState extends _$FollowState {
  @override
  Future<RelationshipData?> build(String userId) async {
    final apiService = ref.read(socialApiServiceProvider);
    final response = await apiService.getRelationship(userId);
    return RelationshipData.fromJson(response['data']);
  }

  Future<void> followUser() async {
    final userId = state.value?.userId ?? '';
    final apiService = ref.read(socialApiServiceProvider);

    // Optimistic update
    state = AsyncValue.data(
      state.value!.copyWith(following: true)
    );

    try {
      await apiService.followUser(userId);
    } catch (e) {
      // Revert on error
      state = AsyncValue.data(
        state.value!.copyWith(following: false)
      );
      rethrow;
    }
  }

  Future<void> unfollowUser() async {
    final userId = state.value?.userId ?? '';
    final apiService = ref.read(socialApiServiceProvider);

    // Optimistic update
    state = AsyncValue.data(
      state.value!.copyWith(following: false)
    );

    try {
      await apiService.unfollowUser(userId);
    } catch (e) {
      // Revert on error
      state = AsyncValue.data(
        state.value!.copyWith(following: true)
      );
      rethrow;
    }
  }
}

@riverpod
Future<List<FollowerResponse>> followers(
  FollowersRef ref,
  String userId, {
  int page = 1,
  String? search,
}) async {
  final apiService = ref.read(socialApiServiceProvider);
  final response = await apiService.getFollowers(
    userId,
    page,
    20,
    search,
  );

  return (response['data'] as List)
      .map((json) => FollowerResponse.fromJson(json))
      .toList();
}

@riverpod
Future<List<FollowingResponse>> following(
  FollowingRef ref,
  String userId, {
  int page = 1,
  String? search,
}) async {
  final apiService = ref.read(socialApiServiceProvider);
  final response = await apiService.getFollowing(
    userId,
    page,
    20,
    search,
  );

  return (response['data'] as List)
      .map((json) => FollowingResponse.fromJson(json))
      .toList();
}
```

#### Step 3: Create Follow Button Widget

```dart
// lib/features/social/widgets/follow_button.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:souk_loop/app/theme/app_colors.dart';

class FollowButton extends ConsumerWidget {
  final String userId;
  final VoidCallback? onFollowStateChanged;

  const FollowButton({
    Key? key,
    required this.userId,
    this.onFollowStateChanged,
  }) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final relationshipAsync = ref.watch(followStateProvider(userId));

    return relationshipAsync.when(
      data: (relationship) {
        final isFollowing = relationship.following;
        final followsBack = relationship.followedBy;

        return ElevatedButton(
          onPressed: () async {
            if (isFollowing) {
              await ref.read(followStateProvider(userId).notifier).unfollowUser();
            } else {
              await ref.read(followStateProvider(userId).notifier).followUser();
            }
            onFollowStateChanged?.call();
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: isFollowing
                ? AppColors.trustTeal.withOpacity(0.1)
                : AppColors.soukGold,
            foregroundColor: isFollowing
                ? AppColors.trustTeal
                : Colors.white,
            minimumSize: const Size(100, 36),
            padding: const EdgeInsets.symmetric(horizontal: 20),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(20),
              side: isFollowing
                  ? BorderSide(color: AppColors.trustTeal, width: 1.5)
                  : BorderSide.none,
            ),
          ),
          child: Text(
            isFollowing
                ? (followsBack ? 'Following' : 'Following')
                : (followsBack ? 'Follow Back' : 'Follow'),
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
        );
      },
      loading: () => const SizedBox(
        width: 100,
        height: 36,
        child: Center(
          child: SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
      ),
      error: (error, stack) => const SizedBox.shrink(),
    );
  }
}
```

#### Step 4: Create Followers/Following Screen

```dart
// lib/features/social/screens/followers_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class FollowersScreen extends ConsumerStatefulWidget {
  final String userId;
  final bool isFollowersTab; // true = followers, false = following

  const FollowersScreen({
    Key? key,
    required this.userId,
    this.isFollowersTab = true,
  }) : super(key: key);

  @override
  ConsumerState<FollowersScreen> createState() => _FollowersScreenState();
}

class _FollowersScreenState extends ConsumerState<FollowersScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _searchController = TextEditingController();
  String? _searchQuery;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: 2,
      vsync: this,
      initialIndex: widget.isFollowersTab ? 0 : 1,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Connections'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'Followers'),
            Tab(text: 'Following'),
          ],
        ),
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchQuery != null
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchQuery = null);
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onChanged: (value) {
                setState(() {
                  _searchQuery = value.isEmpty ? null : value;
                });
              },
            ),
          ),
          // Tab content
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _buildFollowersList(),
                _buildFollowingList(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFollowersList() {
    final followersAsync = ref.watch(
      followersProvider(widget.userId, search: _searchQuery),
    );

    return followersAsync.when(
      data: (followers) {
        if (followers.isEmpty) {
          return const Center(
            child: Text('No followers yet'),
          );
        }

        return ListView.builder(
          itemCount: followers.length,
          itemBuilder: (context, index) {
            final follower = followers[index];
            return ListTile(
              leading: CircleAvatar(
                backgroundImage: follower.user.avatarUrl != null
                    ? NetworkImage(follower.user.avatarUrl!)
                    : null,
                child: follower.user.avatarUrl == null
                    ? Text(follower.user.username[0].toUpperCase())
                    : null,
              ),
              title: Row(
                children: [
                  Text(follower.user.username),
                  if (follower.user.isVerified) ...[
                    const SizedBox(width: 4),
                    const Icon(Icons.verified, size: 16, color: Colors.blue),
                  ],
                ],
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(follower.user.fullName),
                  if (follower.isMutual)
                    Text(
                      'Follows you',
                      style: TextStyle(
                        color: AppColors.trustTeal,
                        fontSize: 12,
                      ),
                    ),
                ],
              ),
              trailing: FollowButton(userId: follower.user.id),
              onTap: () {
                // Navigate to user profile
              },
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(
        child: Text('Error: $error'),
      ),
    );
  }

  Widget _buildFollowingList() {
    final followingAsync = ref.watch(
      followingProvider(widget.userId, search: _searchQuery),
    );

    return followingAsync.when(
      data: (following) {
        if (following.isEmpty) {
          return const Center(
            child: Text('Not following anyone yet'),
          );
        }

        return ListView.builder(
          itemCount: following.length,
          itemBuilder: (context, index) {
            final user = following[index];
            return ListTile(
              leading: CircleAvatar(
                backgroundImage: user.user.avatarUrl != null
                    ? NetworkImage(user.user.avatarUrl!)
                    : null,
              ),
              title: Text(user.user.username),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(user.user.fullName),
                  if (user.followsBack)
                    Text(
                      'Follows you back',
                      style: TextStyle(
                        color: AppColors.trustTeal,
                        fontSize: 12,
                      ),
                    ),
                ],
              ),
              trailing: FollowButton(userId: user.user.id),
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(child: Text('Error: $error')),
    );
  }
}
```

---

### Feature 2: Notification Center

#### Step 1: Setup Firebase Cloud Messaging

```dart
// lib/core/services/firebase_messaging_service.dart
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class FirebaseMessagingService {
  final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  Future<void> initialize() async {
    // Request permission (iOS)
    await _firebaseMessaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    // Initialize local notifications
    const initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const initializationSettingsIOS = DarwinInitializationSettings();
    const initializationSettings = InitializationSettings(
      android: initializationSettingsAndroid,
      iOS: initializationSettingsIOS,
    );

    await _localNotifications.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: _onNotificationTapped,
    );

    // Get FCM token
    final token = await _firebaseMessaging.getToken();
    print('FCM Token: $token');

    // TODO: Send token to backend
    // await _registerDeviceToken(token);

    // Listen for token refresh
    _firebaseMessaging.onTokenRefresh.listen((newToken) {
      print('FCM Token refreshed: $newToken');
      // TODO: Update token on backend
    });

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // Handle background messages
    FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

    // Handle notification taps when app is in background
    FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);
  }

  Future<void> _handleForegroundMessage(RemoteMessage message) async {
    print('Received foreground message: ${message.notification?.title}');

    // Show local notification
    await _showLocalNotification(message);
  }

  Future<void> _showLocalNotification(RemoteMessage message) async {
    const androidDetails = AndroidNotificationDetails(
      'souk_loop_notifications',
      'Souk Loop Notifications',
      channelDescription: 'Notifications from Souk Loop',
      importance: Importance.high,
      priority: Priority.high,
    );

    const iosDetails = DarwinNotificationDetails();

    const notificationDetails = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _localNotifications.show(
      message.hashCode,
      message.notification?.title,
      message.notification?.body,
      notificationDetails,
      payload: message.data.toString(),
    );
  }

  void _onNotificationTapped(NotificationResponse response) {
    print('Notification tapped: ${response.payload}');
    // TODO: Navigate to appropriate screen based on notification type
  }

  void _handleNotificationTap(RemoteMessage message) {
    print('Notification opened app: ${message.data}');
    // TODO: Navigate to appropriate screen
  }

  Future<String?> getToken() async {
    return await _firebaseMessaging.getToken();
  }
}

// Top-level function for background message handling
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  print('Handling background message: ${message.messageId}');
}
```

#### Step 2: Register Device Token with Backend

```dart
// Add to social_api_service.dart
@POST("/notifications/register-device")
Future<Map<String, dynamic>> registerDevice(
  @Body() Map<String, dynamic> deviceData,
);

@DELETE("/notifications/unregister-device")
Future<Map<String, dynamic>> unregisterDevice(
  @Body() Map<String, dynamic> deviceData,
);
```

```dart
// Usage in auth flow
Future<void> registerDeviceForNotifications() async {
  final fcmToken = await _messagingService.getToken();
  if (fcmToken == null) return;

  final deviceId = await _getDeviceId(); // Use device_info_plus package

  await _socialApiService.registerDevice({
    'fcm_token': fcmToken,
    'platform': Platform.isIOS ? 'ios' : 'android',
    'device_id': deviceId,
  });
}
```

#### Step 3: Create Notifications API Service

```dart
// Add to social_api_service.dart
@GET("/notifications")
Future<Map<String, dynamic>> getNotifications(
  @Query("unread_only") bool unreadOnly,
  @Query("page") int page,
  @Query("per_page") int perPage,
);

@GET("/notifications/unread-count")
Future<Map<String, dynamic>> getUnreadCount();

@PATCH("/notifications/{notificationId}/read")
Future<Map<String, dynamic>> markAsRead(
  @Path("notificationId") String notificationId,
);

@PATCH("/notifications/read-all")
Future<Map<String, dynamic>> markAllAsRead();
```

#### Step 4: Create Notification Provider

```dart
// lib/features/notifications/providers/notification_provider.dart
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'notification_provider.g.dart';

@riverpod
class UnreadNotificationCount extends _$UnreadNotificationCount {
  @override
  Future<int> build() async {
    final apiService = ref.read(socialApiServiceProvider);
    final response = await apiService.getUnreadCount();
    return response['unread_count'] as int;
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final apiService = ref.read(socialApiServiceProvider);
      final response = await apiService.getUnreadCount();
      return response['unread_count'] as int;
    });
  }
}

@riverpod
Future<List<NotificationModel>> notifications(
  NotificationsRef ref, {
  bool unreadOnly = false,
  int page = 1,
}) async {
  final apiService = ref.read(socialApiServiceProvider);
  final response = await apiService.getNotifications(unreadOnly, page, 20);

  return (response['data'] as List)
      .map((json) => NotificationModel.fromJson(json))
      .toList();
}
```

#### Step 5: Create Notification Center Screen

```dart
// lib/features/notifications/screens/notification_center_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:timeago/timeago.dart' as timeago;

class NotificationCenterScreen extends ConsumerStatefulWidget {
  const NotificationCenterScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<NotificationCenterScreen> createState() =>
      _NotificationCenterScreenState();
}

class _NotificationCenterScreenState
    extends ConsumerState<NotificationCenterScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          TextButton(
            onPressed: () async {
              await ref.read(socialApiServiceProvider).markAllAsRead();
              ref.invalidate(unreadNotificationCountProvider);
              ref.invalidate(notificationsProvider);
            },
            child: const Text('Mark all read'),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(text: 'All'),
            Tab(text: 'Unread'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildNotificationsList(unreadOnly: false),
          _buildNotificationsList(unreadOnly: true),
        ],
      ),
    );
  }

  Widget _buildNotificationsList({required bool unreadOnly}) {
    final notificationsAsync = ref.watch(
      notificationsProvider(unreadOnly: unreadOnly),
    );

    return notificationsAsync.when(
      data: (notifications) {
        if (notifications.isEmpty) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.notifications_none, size: 64, color: Colors.grey),
                const SizedBox(height: 16),
                Text(
                  unreadOnly ? 'No unread notifications' : 'No notifications',
                  style: TextStyle(color: Colors.grey),
                ),
              ],
            ),
          );
        }

        return RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(notificationsProvider);
          },
          child: ListView.separated(
            itemCount: notifications.length,
            separatorBuilder: (context, index) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final notification = notifications[index];
              return _buildNotificationTile(notification);
            },
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(child: Text('Error: $error')),
    );
  }

  Widget _buildNotificationTile(NotificationModel notification) {
    return Dismissible(
      key: Key(notification.id),
      direction: DismissDirection.endToStart,
      background: Container(
        color: Colors.red,
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      onDismissed: (direction) {
        // TODO: Delete notification
      },
      child: ListTile(
        leading: _getNotificationIcon(notification.notificationType),
        title: Text(
          notification.title,
          style: TextStyle(
            fontWeight: notification.isRead ? FontWeight.normal : FontWeight.bold,
          ),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(notification.body),
            const SizedBox(height: 4),
            Text(
              timeago.format(notification.createdAt),
              style: TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
        ),
        trailing: !notification.isRead
            ? Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: AppColors.vividPurple,
                  shape: BoxShape.circle,
                ),
              )
            : null,
        onTap: () async {
          // Mark as read
          if (!notification.isRead) {
            await ref.read(socialApiServiceProvider).markAsRead(notification.id);
            ref.invalidate(unreadNotificationCountProvider);
            ref.invalidate(notificationsProvider);
          }

          // Navigate based on notification type
          _handleNotificationTap(notification);
        },
      ),
    );
  }

  Widget _getNotificationIcon(NotificationType type) {
    IconData icon;
    Color color;

    switch (type) {
      case NotificationType.newFollower:
        icon = Icons.person_add;
        color = AppColors.trustTeal;
        break;
      case NotificationType.newMessage:
        icon = Icons.message;
        color = AppColors.electricPink;
        break;
      case NotificationType.streamStarted:
        icon = Icons.play_circle_filled;
        color = AppColors.errorRed;
        break;
      case NotificationType.offerAccepted:
        icon = Icons.check_circle;
        color = AppColors.trustTeal;
        break;
      default:
        icon = Icons.notifications;
        color = AppColors.vividPurple;
    }

    return CircleAvatar(
      backgroundColor: color.withOpacity(0.1),
      child: Icon(icon, color: color, size: 20),
    );
  }

  void _handleNotificationTap(NotificationModel notification) {
    // Navigate to appropriate screen based on notification type and data
    final data = notification.data;

    switch (notification.notificationType) {
      case NotificationType.newFollower:
        // Navigate to user profile
        final followerId = data?['follower_id'];
        // Navigator.push(...);
        break;
      case NotificationType.streamStarted:
        // Navigate to live stream
        final streamId = data?['stream_id'];
        // Navigator.push(...);
        break;
      // Add other cases...
      default:
        break;
    }
  }
}
```

#### Step 6: Add Notification Badge to Bottom Nav

```dart
// lib/features/home/presentation/screens/home_page.dart

Consumer(
  builder: (context, ref, child) {
    final unreadCountAsync = ref.watch(unreadNotificationCountProvider);
    final unreadCount = unreadCountAsync.maybeWhen(
      data: (count) => count,
      orElse: () => 0,
    );

    return BottomNavigationBarItem(
      icon: Badge(
        label: Text('$unreadCount'),
        isLabelVisible: unreadCount > 0,
        child: const Icon(Icons.notifications),
      ),
      label: 'Notifications',
    );
  },
)
```

---

### Feature 3: Activity Feed

#### Step 1: Create Activity API Service

```dart
// Add to social_api_service.dart
@GET("/activity")
Future<Map<String, dynamic>> getActivityFeed(
  @Query("page") int page,
  @Query("per_page") int perPage,
);

@GET("/activity/me")
Future<Map<String, dynamic>> getPersonalActivity(
  @Query("page") int page,
  @Query("per_page") int perPage,
);
```

#### Step 2: Create Activity Provider

```dart
// lib/features/activity/providers/activity_provider.dart
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'activity_provider.g.dart';

@riverpod
Future<List<ActivityModel>> activityFeed(
  ActivityFeedRef ref, {
  int page = 1,
}) async {
  final apiService = ref.read(socialApiServiceProvider);
  final response = await apiService.getActivityFeed(page, 20);

  return (response['data'] as List)
      .map((json) => ActivityModel.fromJson(json))
      .toList();
}

@riverpod
Future<List<ActivityModel>> personalActivity(
  PersonalActivityRef ref, {
  int page = 1,
}) async {
  final apiService = ref.read(socialApiServiceProvider);
  final response = await apiService.getPersonalActivity(page, 20);

  return (response['data'] as List)
      .map((json) => ActivityModel.fromJson(json))
      .toList();
}
```

#### Step 3: Create Activity Feed Screen

```dart
// lib/features/activity/screens/activity_feed_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class ActivityFeedScreen extends ConsumerWidget {
  const ActivityFeedScreen({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final activitiesAsync = ref.watch(activityFeedProvider());

    return Scaffold(
      appBar: AppBar(
        title: const Text('Activity Feed'),
      ),
      body: activitiesAsync.when(
        data: (activities) {
          if (activities.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.people_outline, size: 64, color: Colors.grey),
                  const SizedBox(height: 16),
                  const Text(
                    'Follow users to see their activity',
                    style: TextStyle(color: Colors.grey),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(activityFeedProvider);
            },
            child: ListView.separated(
              itemCount: activities.length,
              separatorBuilder: (context, index) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final activity = activities[index];
                return _buildActivityTile(activity);
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(child: Text('Error: $error')),
      ),
    );
  }

  Widget _buildActivityTile(ActivityModel activity) {
    final user = activity.user;
    if (user == null) return const SizedBox.shrink();

    return ListTile(
      leading: CircleAvatar(
        backgroundImage: user['avatar_url'] != null
            ? NetworkImage(user['avatar_url'])
            : null,
        child: user['avatar_url'] == null
            ? Text(user['username'][0].toUpperCase())
            : null,
      ),
      title: RichText(
        text: TextSpan(
          style: const TextStyle(color: Colors.black),
          children: [
            TextSpan(
              text: user['username'],
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            TextSpan(text: ' ${_getActivityText(activity)}'),
          ],
        ),
      ),
      subtitle: Text(
        timeago.format(activity.createdAt),
        style: const TextStyle(fontSize: 12),
      ),
      trailing: _getActivityTrailing(activity),
      onTap: () => _handleActivityTap(activity),
    );
  }

  String _getActivityText(ActivityModel activity) {
    switch (activity.activityType) {
      case ActivityType.wentLive:
        return 'went live';
      case ActivityType.newProduct:
        return 'posted a new product';
      case ActivityType.productSold:
        return 'sold a product';
      case ActivityType.reviewReceived:
        return 'received a 5-star review';
      case ActivityType.milestone:
        final milestone = activity.metaData?['milestone'];
        return 'achieved $milestone';
      default:
        return '';
    }
  }

  Widget? _getActivityTrailing(ActivityModel activity) {
    switch (activity.activityType) {
      case ActivityType.wentLive:
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: AppColors.errorRed,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 6,
                height: 6,
                decoration: const BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 4),
              const Text(
                'LIVE',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        );
      case ActivityType.newProduct:
        final relatedProduct = activity.relatedProduct;
        if (relatedProduct != null && relatedProduct['image_urls'] != null) {
          final imageUrl = (relatedProduct['image_urls'] as List).first;
          return ClipRRect(
            borderRadius: BorderRadius.circular(8),
            child: Image.network(
              imageUrl,
              width: 60,
              height: 60,
              fit: BoxFit.cover,
            ),
          );
        }
        return null;
      default:
        return null;
    }
  }

  void _handleActivityTap(ActivityModel activity) {
    // Navigate based on activity type
    switch (activity.activityType) {
      case ActivityType.wentLive:
        // Navigate to live stream
        final streamId = activity.relatedStreamId;
        // Navigator.push(...);
        break;
      case ActivityType.newProduct:
        // Navigate to product detail
        final productId = activity.relatedProductId;
        // Navigator.push(...);
        break;
      default:
        break;
    }
  }
}
```

---

## Firebase Cloud Messaging Setup

### 1. Firebase Console Setup

1. **Create Firebase Project**:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a new project or use existing one
   - Enable Cloud Messaging

2. **Add Android App**:
   - Add Android app with package name: `com.soukloop.app`
   - Download `google-services.json`
   - Place in `android/app/`

3. **Add iOS App**:
   - Add iOS app with bundle ID: `com.soukloop.app`
   - Download `GoogleService-Info.plist`
   - Place in `ios/Runner/`

4. **Generate Service Account Key**:
   - Project Settings → Service Accounts
   - Generate new private key
   - Save as `firebase-service-account.json`
   - Upload to backend server
   - Set `FIREBASE_CREDENTIALS_PATH` in `.env`

### 2. Android Configuration

**android/app/build.gradle:**
```gradle
plugins {
    id "com.android.application"
    id "kotlin-android"
    id "dev.flutter.flutter-gradle-plugin"
    id "com.google.gms.google-services" // Add this
}

dependencies {
    implementation platform('com.google.firebase:firebase-bom:32.7.0')
    implementation 'com.google.firebase:firebase-messaging'
}
```

**android/build.gradle:**
```gradle
buildscript {
    dependencies {
        classpath 'com.google.gms:google-services:4.4.0'
    }
}
```

**android/app/src/main/AndroidManifest.xml:**
```xml
<manifest>
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>

    <application>
        <!-- Firebase Messaging Service -->
        <service
            android:name="com.google.firebase.messaging.FirebaseMessagingService"
            android:exported="false">
            <intent-filter>
                <action android:name="com.google.firebase.MESSAGING_EVENT" />
            </intent-filter>
        </service>

        <!-- Notification channel -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_channel_id"
            android:value="souk_loop_notifications" />
    </application>
</manifest>
```

### 3. iOS Configuration

**ios/Runner/Info.plist:**
```xml
<key>FirebaseAppDelegateProxyEnabled</key>
<false/>
```

**ios/Podfile:**
```ruby
platform :ios, '13.0'

target 'Runner' do
  use_frameworks!
  use_modular_headers!

  flutter_install_all_ios_pods File.dirname(File.realpath(__FILE__))

  # Add Firebase pods
  pod 'Firebase/Messaging'
end
```

### 4. Initialize in Flutter

**lib/main.dart:**
```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:souk_loop/core/services/firebase_messaging_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize Firebase
  await Firebase.initializeApp();

  // Initialize FCM
  final messagingService = FirebaseMessagingService();
  await messagingService.initialize();

  runApp(const MyApp());
}
```

---

## Testing Checklist

### Follow System Testing

- [ ] Follow a user
  - [ ] Follow button changes to "Following"
  - [ ] Follower count increments for followed user
  - [ ] Following count increments for current user
  - [ ] Notification sent to followed user
  - [ ] Activity created for followed user

- [ ] Unfollow a user
  - [ ] Follow button changes to "Follow"
  - [ ] Counts decrement correctly

- [ ] View followers list
  - [ ] Shows all followers
  - [ ] Mutual follow indicator works
  - [ ] Search filters correctly
  - [ ] Pagination works

- [ ] View following list
  - [ ] Shows all following
  - [ ] Follow-back indicator works
  - [ ] Can unfollow from list

- [ ] Check relationship status
  - [ ] Correctly shows following/followed_by
  - [ ] Blocked status works
  - [ ] Can message status accurate

### Notification Testing

- [ ] Receive push notification
  - [ ] Shows when app is in foreground
  - [ ] Shows when app is in background
  - [ ] Shows when app is terminated
  - [ ] Tapping opens correct screen

- [ ] Notification center
  - [ ] Shows all notifications
  - [ ] Shows unread notifications
  - [ ] Mark as read works
  - [ ] Mark all as read works
  - [ ] Delete notification works

- [ ] Unread badge
  - [ ] Shows correct count on bottom nav
  - [ ] Updates when notification marked read
  - [ ] Clears when all read

- [ ] Device registration
  - [ ] Token sent to backend on login
  - [ ] Token updated on refresh
  - [ ] Token removed on logout

### Activity Feed Testing

- [ ] Activity feed
  - [ ] Shows activities from followed users
  - [ ] Displays correct activity text
  - [ ] Shows related content (images, streams)
  - [ ] Tapping navigates correctly
  - [ ] Empty state shown when not following anyone

- [ ] Personal activity
  - [ ] Shows user's own activities
  - [ ] Displays all activity types
  - [ ] Pagination works

---

## Best Practices

### 1. Error Handling

```dart
// Always wrap API calls in try-catch
try {
  await ref.read(followStateProvider(userId).notifier).followUser();

  // Show success feedback
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('Successfully followed user')),
  );
} catch (e) {
  // Show error feedback
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Failed to follow user: $e')),
  );
}
```

### 2. Optimistic Updates

```dart
// Update UI immediately, revert on error
state = AsyncValue.data(state.value!.copyWith(following: true));

try {
  await apiService.followUser(userId);
} catch (e) {
  // Revert on error
  state = AsyncValue.data(state.value!.copyWith(following: false));
  rethrow;
}
```

### 3. Pagination

```dart
// Use infinite scroll for lists
class _FollowersScreenState extends ConsumerState<FollowersScreen> {
  final _scrollController = ScrollController();
  int _currentPage = 1;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent * 0.9) {
      // Load more when 90% scrolled
      _loadMore();
    }
  }

  Future<void> _loadMore() async {
    _currentPage++;
    // Load next page...
  }
}
```

### 4. Cache Management

```dart
// Invalidate cache when data changes
ref.invalidate(followersProvider);
ref.invalidate(unreadNotificationCountProvider);

// Keep cache fresh
ref.refresh(activityFeedProvider());
```

### 5. Deep Linking for Notifications

```dart
// Handle notification taps
void _handleNotificationTap(NotificationModel notification) {
  final data = notification.data;

  switch (notification.notificationType) {
    case NotificationType.streamStarted:
      final streamId = data?['stream_id'];
      context.push('/streams/$streamId');
      break;
    // Handle other types...
  }
}
```

### 6. Background Refresh

```dart
// Refresh unread count periodically
Timer.periodic(const Duration(minutes: 5), (timer) {
  ref.refresh(unreadNotificationCountProvider);
});
```

---

## Next Steps

1. **Week 1: Follow System**
   - Implement API service and providers
   - Build follow button widget
   - Create followers/following screens
   - Test all scenarios

2. **Week 2: Notifications**
   - Setup Firebase in Flutter app
   - Register device tokens
   - Build notification center
   - Add notification badges
   - Test push notifications

3. **Week 3: Activity Feed**
   - Implement activity providers
   - Build activity feed screen
   - Add activity cards for each type
   - Integrate with navigation

4. **Week 4: Polish & Testing**
   - Add animations and transitions
   - Optimize performance
   - Test on real devices
   - Fix bugs

---

## Support & Resources

**Documentation:**
- Firebase Cloud Messaging: https://firebase.google.com/docs/cloud-messaging
- Riverpod: https://riverpod.dev/docs
- Freezed: https://pub.dev/packages/freezed

**Backend Endpoints:**
- Local: `http://localhost:8000/api/v1`
- Staging: `https://api-staging.soukloop.com/api/v1`
- Production: `https://api.soukloop.com/api/v1`

**Common Issues:**
1. FCM token not received → Check Firebase configuration
2. Notifications not showing → Check permissions
3. Follow count not updating → Invalidate provider cache
4. API errors → Check authentication token

---

**Ready to implement! 🚀**
