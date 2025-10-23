"""Tests for Real-Time Cache Service (Phase 4)

Tests for:
- Viewer count tracking (sorted sets)
- Typing indicators (3s TTL)
- Presence status (5min TTL)
- Unread message counters

Requirements:
- Redis must be running on localhost:6379
- Run with: pytest tests/test_realtime_cache.py -v
"""

import asyncio
import time
from uuid import uuid4

import pytest

from app.core.cache.redis_manager import RedisManager, init_redis_manager
from app.services.cache.realtime_cache_service import RealTimeCacheService


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def redis_manager():
    """Create real Redis manager for integration tests."""
    manager = await init_redis_manager()
    yield manager
    await manager.close()


@pytest.fixture(scope="function")
async def realtime_cache(redis_manager):
    """Create RealTimeCacheService instance."""
    service = RealTimeCacheService(redis_manager)

    # Cleanup before tests
    try:
        await redis_manager.delete_pattern("live:*")
        await redis_manager.delete_pattern("typing:*")
        await redis_manager.delete_pattern("presence:*")
        await redis_manager.delete_pattern("unread:*")
    except Exception:
        pass  # Ignore cleanup errors

    return service


# ============================================================================
# TEST VIEWER COUNT TRACKING
# ============================================================================


@pytest.mark.asyncio
async def test_add_viewer(realtime_cache):
    """Test adding a viewer to a live stream."""
    stream_id = str(uuid4())
    user_id = str(uuid4())

    count = await realtime_cache.add_viewer(stream_id, user_id)

    assert count == 1, "Viewer count should be 1 after adding first viewer"


@pytest.mark.asyncio
async def test_add_multiple_viewers(realtime_cache):
    """Test adding multiple viewers to a live stream."""
    stream_id = str(uuid4())
    user_ids = [str(uuid4()) for _ in range(5)]

    for i, user_id in enumerate(user_ids):
        count = await realtime_cache.add_viewer(stream_id, user_id)
        assert count == i + 1, f"Viewer count should be {i + 1}"

    final_count = await realtime_cache.get_viewer_count(stream_id)
    assert final_count == 5, "Final viewer count should be 5"


@pytest.mark.asyncio
async def test_remove_viewer(realtime_cache):
    """Test removing a viewer from a live stream."""
    stream_id = str(uuid4())
    user_ids = [str(uuid4()) for _ in range(3)]

    # Add 3 viewers
    for user_id in user_ids:
        await realtime_cache.add_viewer(stream_id, user_id)

    # Remove one viewer
    count = await realtime_cache.remove_viewer(stream_id, user_ids[0])
    assert count == 2, "Viewer count should be 2 after removing one viewer"


@pytest.mark.asyncio
async def test_viewer_count_accuracy(realtime_cache):
    """Test viewer count accuracy within 1 second (Phase 4 requirement)."""
    stream_id = str(uuid4())
    user_ids = [str(uuid4()) for _ in range(10)]

    start_time = time.time()

    # Add 10 viewers rapidly
    for user_id in user_ids:
        await realtime_cache.add_viewer(stream_id, user_id)

    # Get count
    count = await realtime_cache.get_viewer_count(stream_id)
    elapsed = time.time() - start_time

    assert count == 10, "Should have 10 viewers"
    assert elapsed < 1.0, f"Should complete within 1 second (took {elapsed:.3f}s)"
    print(f"✅ Viewer count tracking completed in {elapsed:.3f}s (< 1s requirement)")


@pytest.mark.asyncio
async def test_get_viewers_list(realtime_cache):
    """Test retrieving list of viewer user IDs."""
    stream_id = str(uuid4())
    user_ids = [str(uuid4()) for _ in range(3)]

    # Add viewers
    for user_id in user_ids:
        await realtime_cache.add_viewer(stream_id, user_id)

    # Get viewer list
    viewers = await realtime_cache.get_viewers(stream_id)

    assert len(viewers) == 3, "Should have 3 viewers"
    assert all(uid in viewers for uid in user_ids), "All user IDs should be in viewers list"


@pytest.mark.asyncio
async def test_is_viewing(realtime_cache):
    """Test checking if a user is viewing a stream."""
    stream_id = str(uuid4())
    user_id = str(uuid4())

    # Not viewing initially
    is_viewing = await realtime_cache.is_viewing(stream_id, user_id)
    assert not is_viewing, "User should not be viewing initially"

    # Add viewer
    await realtime_cache.add_viewer(stream_id, user_id)

    # Should be viewing now
    is_viewing = await realtime_cache.is_viewing(stream_id, user_id)
    assert is_viewing, "User should be viewing after adding"


@pytest.mark.asyncio
async def test_clear_viewers(realtime_cache):
    """Test clearing all viewers when stream ends."""
    stream_id = str(uuid4())
    user_ids = [str(uuid4()) for _ in range(5)]

    # Add viewers
    for user_id in user_ids:
        await realtime_cache.add_viewer(stream_id, user_id)

    # Clear viewers
    await realtime_cache.clear_viewers(stream_id)

    # Count should be 0
    count = await realtime_cache.get_viewer_count(stream_id)
    assert count == 0, "Viewer count should be 0 after clearing"


# ============================================================================
# TEST TYPING INDICATORS
# ============================================================================


@pytest.mark.asyncio
async def test_set_typing(realtime_cache):
    """Test setting typing indicator."""
    conversation_id = str(uuid4())
    user_id = str(uuid4())

    await realtime_cache.set_typing(conversation_id, user_id)

    is_typing = await realtime_cache.is_typing(conversation_id, user_id)
    assert is_typing, "User should be typing after setting indicator"


@pytest.mark.asyncio
async def test_typing_auto_expire(realtime_cache):
    """Test typing indicator auto-expires after 3 seconds."""
    conversation_id = str(uuid4())
    user_id = str(uuid4())

    await realtime_cache.set_typing(conversation_id, user_id)

    # Should be typing immediately
    is_typing = await realtime_cache.is_typing(conversation_id, user_id)
    assert is_typing, "User should be typing immediately"

    # Wait 3.5 seconds (TTL is 3s)
    await asyncio.sleep(3.5)

    # Should not be typing anymore
    is_typing = await realtime_cache.is_typing(conversation_id, user_id)
    assert not is_typing, "Typing indicator should auto-expire after 3s"
    print("✅ Typing indicator auto-expired after 3s (TTL working)")


@pytest.mark.asyncio
async def test_typing_instant_show_hide(realtime_cache):
    """Test typing indicator shows/hides instantly (Phase 4 requirement)."""
    conversation_id = str(uuid4())
    user_id = str(uuid4())

    start_time = time.time()

    # Set typing
    await realtime_cache.set_typing(conversation_id, user_id)
    set_elapsed = time.time() - start_time

    # Check typing (should be instant)
    is_typing = await realtime_cache.is_typing(conversation_id, user_id)
    check_elapsed = time.time() - start_time

    # Clear typing
    await realtime_cache.clear_typing(conversation_id, user_id)
    clear_elapsed = time.time() - start_time

    # Check cleared
    is_not_typing = not await realtime_cache.is_typing(conversation_id, user_id)

    assert is_typing, "Should be typing after set"
    assert is_not_typing, "Should not be typing after clear"
    assert set_elapsed < 0.1, f"Set should be instant (<100ms, took {set_elapsed*1000:.1f}ms)"
    assert check_elapsed < 0.1, f"Check should be instant (<100ms, took {check_elapsed*1000:.1f}ms)"
    assert clear_elapsed < 0.2, f"Clear should be instant (<200ms, took {clear_elapsed*1000:.1f}ms)"
    print(f"✅ Typing show/hide completed in {clear_elapsed*1000:.1f}ms (instant)")


@pytest.mark.asyncio
async def test_get_typing_users(realtime_cache):
    """Test getting list of typing users in a conversation."""
    conversation_id = str(uuid4())
    user_ids = [str(uuid4()) for _ in range(3)]

    # Set multiple users typing
    for user_id in user_ids:
        await realtime_cache.set_typing(conversation_id, user_id)

    # Get typing users
    typing_users = await realtime_cache.get_typing_users(conversation_id)

    assert len(typing_users) == 3, "Should have 3 typing users"
    assert all(uid in typing_users for uid in user_ids), "All user IDs should be in typing list"


# ============================================================================
# TEST PRESENCE STATUS
# ============================================================================


@pytest.mark.asyncio
async def test_set_presence_online(realtime_cache):
    """Test setting user presence to online."""
    user_id = str(uuid4())

    await realtime_cache.set_presence(user_id, "online")

    status = await realtime_cache.get_presence(user_id)
    assert status == "online", "User should be online"


@pytest.mark.asyncio
async def test_set_presence_away(realtime_cache):
    """Test setting user presence to away."""
    user_id = str(uuid4())

    await realtime_cache.set_presence(user_id, "away")

    status = await realtime_cache.get_presence(user_id)
    assert status == "away", "User should be away"


@pytest.mark.asyncio
async def test_set_offline(realtime_cache):
    """Test setting user offline (deletes presence key)."""
    user_id = str(uuid4())

    # Set online first
    await realtime_cache.set_presence(user_id, "online")

    # Set offline
    await realtime_cache.set_offline(user_id)

    status = await realtime_cache.get_presence(user_id)
    assert status == "offline", "User should be offline"


@pytest.mark.asyncio
async def test_is_online(realtime_cache):
    """Test checking if user is online."""
    user_id = str(uuid4())

    # Not online initially
    is_online = await realtime_cache.is_online(user_id)
    assert not is_online, "User should not be online initially"

    # Set online
    await realtime_cache.set_presence(user_id, "online")

    is_online = await realtime_cache.is_online(user_id)
    assert is_online, "User should be online after setting"


@pytest.mark.asyncio
async def test_presence_batch(realtime_cache):
    """Test batch getting presence for multiple users."""
    user_ids = [str(uuid4()) for _ in range(5)]

    # Set different statuses
    await realtime_cache.set_presence(user_ids[0], "online")
    await realtime_cache.set_presence(user_ids[1], "away")
    await realtime_cache.set_presence(user_ids[2], "online")
    # user_ids[3] and [4] left offline (no key)

    # Batch get
    statuses = await realtime_cache.get_presence_batch(user_ids)

    assert statuses[user_ids[0]] == "online"
    assert statuses[user_ids[1]] == "away"
    assert statuses[user_ids[2]] == "online"
    assert statuses[user_ids[3]] == "offline"
    assert statuses[user_ids[4]] == "offline"
    print("✅ Batch presence lookup working correctly")


# ============================================================================
# TEST UNREAD MESSAGE COUNTERS
# ============================================================================


@pytest.mark.asyncio
async def test_increment_unread_count(realtime_cache):
    """Test incrementing unread message count."""
    user_id = str(uuid4())
    conversation_id = str(uuid4())

    count = await realtime_cache.increment_unread_count(user_id, conversation_id)
    assert count == 1, "Unread count should be 1 after first increment"

    count = await realtime_cache.increment_unread_count(user_id, conversation_id)
    assert count == 2, "Unread count should be 2 after second increment"


@pytest.mark.asyncio
async def test_get_unread_count(realtime_cache):
    """Test getting unread message count."""
    user_id = str(uuid4())
    conversation_id = str(uuid4())

    # Should be 0 initially
    count = await realtime_cache.get_unread_count(user_id, conversation_id)
    assert count == 0, "Unread count should be 0 initially"

    # Increment a few times
    await realtime_cache.increment_unread_count(user_id, conversation_id)
    await realtime_cache.increment_unread_count(user_id, conversation_id)
    await realtime_cache.increment_unread_count(user_id, conversation_id)

    count = await realtime_cache.get_unread_count(user_id, conversation_id)
    assert count == 3, "Unread count should be 3 after 3 increments"


@pytest.mark.asyncio
async def test_reset_unread_count(realtime_cache):
    """Test resetting unread count to zero."""
    user_id = str(uuid4())
    conversation_id = str(uuid4())

    # Increment a few times
    await realtime_cache.increment_unread_count(user_id, conversation_id)
    await realtime_cache.increment_unread_count(user_id, conversation_id)

    # Reset
    await realtime_cache.reset_unread_count(user_id, conversation_id)

    count = await realtime_cache.get_unread_count(user_id, conversation_id)
    assert count == 0, "Unread count should be 0 after reset"


@pytest.mark.asyncio
async def test_total_unread_count(realtime_cache):
    """Test total unread count across all conversations."""
    user_id = str(uuid4())

    # Increment total (no conversation_id)
    count = await realtime_cache.increment_unread_count(user_id)
    assert count == 1

    count = await realtime_cache.increment_unread_count(user_id)
    assert count == 2

    total = await realtime_cache.get_unread_count(user_id)
    assert total == 2, "Total unread should be 2"


@pytest.mark.asyncio
async def test_unread_count_sync(realtime_cache):
    """Test unread counts sync across operations (Phase 4 requirement)."""
    user_id = str(uuid4())
    conv1 = str(uuid4())
    conv2 = str(uuid4())

    # Add messages to 2 conversations
    await realtime_cache.increment_unread_count(user_id, conv1)
    await realtime_cache.increment_unread_count(user_id, conv1)
    await realtime_cache.increment_unread_count(user_id, conv2)

    # Also increment total
    await realtime_cache.increment_unread_count(user_id)
    await realtime_cache.increment_unread_count(user_id)
    await realtime_cache.increment_unread_count(user_id)

    # Get counts
    conv1_count = await realtime_cache.get_unread_count(user_id, conv1)
    conv2_count = await realtime_cache.get_unread_count(user_id, conv2)
    total_count = await realtime_cache.get_unread_count(user_id)

    assert conv1_count == 2, "Conv1 should have 2 unread"
    assert conv2_count == 1, "Conv2 should have 1 unread"
    assert total_count == 3, "Total should be 3"
    print("✅ Unread counts synced correctly across conversations")


@pytest.mark.asyncio
async def test_get_all_conversation_unread_counts(realtime_cache):
    """Test getting unread counts for all conversations."""
    user_id = str(uuid4())
    conv_ids = [str(uuid4()) for _ in range(3)]

    # Add unread messages to multiple conversations
    await realtime_cache.increment_unread_count(user_id, conv_ids[0])
    await realtime_cache.increment_unread_count(user_id, conv_ids[0])
    await realtime_cache.increment_unread_count(user_id, conv_ids[1])
    await realtime_cache.increment_unread_count(user_id, conv_ids[2])
    await realtime_cache.increment_unread_count(user_id, conv_ids[2])
    await realtime_cache.increment_unread_count(user_id, conv_ids[2])

    # Get all counts
    all_counts = await realtime_cache.get_all_conversation_unread_counts(user_id)

    assert all_counts[conv_ids[0]] == 2
    assert all_counts[conv_ids[1]] == 1
    assert all_counts[conv_ids[2]] == 3
    print("✅ All conversation unread counts retrieved correctly")


@pytest.mark.asyncio
async def test_notification_counter(realtime_cache):
    """Test unread notification counter."""
    user_id = str(uuid4())

    # Increment notifications
    count = await realtime_cache.increment_notification_count(user_id)
    assert count == 1

    count = await realtime_cache.increment_notification_count(user_id)
    assert count == 2

    # Get count
    total = await realtime_cache.get_notification_count(user_id)
    assert total == 2

    # Reset
    await realtime_cache.reset_notification_count(user_id)
    total = await realtime_cache.get_notification_count(user_id)
    assert total == 0


# ============================================================================
# TEST ACTIVE STREAMS BY LOCATION
# ============================================================================


@pytest.mark.asyncio
async def test_active_streams_by_location(realtime_cache):
    """Test tracking active streams by neighborhood."""
    neighborhood = "Downtown"
    stream_ids = [str(uuid4()) for _ in range(3)]

    # Add active streams
    for stream_id in stream_ids:
        await realtime_cache.add_active_stream(neighborhood, stream_id)

    # Get active streams
    active = await realtime_cache.get_active_streams(neighborhood)
    assert len(active) == 3, "Should have 3 active streams"

    # Get count
    count = await realtime_cache.get_active_stream_count(neighborhood)
    assert count == 3

    # Remove one stream
    await realtime_cache.remove_active_stream(neighborhood, stream_ids[0])

    count = await realtime_cache.get_active_stream_count(neighborhood)
    assert count == 2, "Should have 2 active streams after removal"


# ============================================================================
# INTEGRATION TEST - FULL WORKFLOW
# ============================================================================


@pytest.mark.asyncio
async def test_full_live_stream_workflow(realtime_cache):
    """Test complete live stream workflow with all features."""
    stream_id = str(uuid4())
    seller_id = str(uuid4())
    viewer_ids = [str(uuid4()) for _ in range(5)]
    neighborhood = "Marina"

    print("\n🎥 Starting live stream workflow test...")

    # 1. Seller goes online
    await realtime_cache.set_presence(seller_id, "online")
    assert await realtime_cache.is_online(seller_id)
    print("✅ Seller is online")

    # 2. Add stream to neighborhood
    await realtime_cache.add_active_stream(neighborhood, stream_id)
    count = await realtime_cache.get_active_stream_count(neighborhood)
    assert count == 1
    print(f"✅ Stream active in {neighborhood}")

    # 3. Viewers join
    for viewer_id in viewer_ids:
        await realtime_cache.add_viewer(stream_id, viewer_id)
        await realtime_cache.set_presence(viewer_id, "online")

    viewer_count = await realtime_cache.get_viewer_count(stream_id)
    assert viewer_count == 5
    print(f"✅ {viewer_count} viewers joined")

    # 4. Test typing in chat
    await realtime_cache.set_typing(stream_id, viewer_ids[0])
    typing_users = await realtime_cache.get_typing_users(stream_id)
    assert len(typing_users) == 1
    print("✅ Typing indicator working")

    # 5. Some viewers leave
    await realtime_cache.remove_viewer(stream_id, viewer_ids[0])
    await realtime_cache.remove_viewer(stream_id, viewer_ids[1])
    viewer_count = await realtime_cache.get_viewer_count(stream_id)
    assert viewer_count == 3
    print(f"✅ {viewer_count} viewers remaining")

    # 6. Stream ends
    await realtime_cache.clear_viewers(stream_id)
    await realtime_cache.remove_active_stream(neighborhood, stream_id)
    viewer_count = await realtime_cache.get_viewer_count(stream_id)
    assert viewer_count == 0
    print("✅ Stream ended successfully")

    # 7. Seller goes offline
    await realtime_cache.set_offline(seller_id)
    is_online = await realtime_cache.is_online(seller_id)
    assert not is_online
    print("✅ Seller is offline")

    print("🎉 Full workflow test completed successfully!")


if __name__ == "__main__":
    print("Run tests with: pytest tests/test_realtime_cache.py -v")
