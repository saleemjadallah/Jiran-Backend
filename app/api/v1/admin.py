"""
Admin moderation tools and dashboard endpoints.
All endpoints require admin role.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.database import get_db
from app.dependencies import get_current_user, require_admin_role
from app.models.user import User
from app.models.product import Product
from app.models.transaction import Transaction
from app.models.stream import Stream
from app.models.report import Report
from app.models.verification import Verification
from app.models.admin_log import AdminLog
from app.schemas.base import StandardResponse, PaginatedResponse

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_role)])


# ============================================================================
# Schemas
# ============================================================================

class AdminDashboardResponse(BaseModel):
    """Admin dashboard overview metrics"""
    pending_verifications: int = Field(description="Count of pending verifications")
    pending_reports: int = Field(description="Count of pending reports")
    active_users_online: int = Field(description="Currently active users")
    live_streams_count: int = Field(description="Currently live streams")
    recent_transactions_count: int = Field(description="Transactions in last 24h")
    platform_health: dict = Field(description="Platform health metrics")


class UpdateUserRequest(BaseModel):
    """Request to update user fields"""
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    role: Optional[str] = None


class SuspendUserRequest(BaseModel):
    """Request to suspend user"""
    reason: str = Field(min_length=10, max_length=500)
    duration_days: Optional[int] = Field(None, description="Duration in days, null for permanent")


class RemoveProductRequest(BaseModel):
    """Request to remove product"""
    reason: str = Field(min_length=10, max_length=500)


class RefundTransactionRequest(BaseModel):
    """Request to refund transaction"""
    reason: str = Field(min_length=10, max_length=500)
    refund_amount: Optional[float] = Field(None, description="Partial refund amount, null for full refund")


class EndStreamRequest(BaseModel):
    """Request to force end stream"""
    reason: str = Field(min_length=10, max_length=500)


# ============================================================================
# Helper Functions
# ============================================================================

async def create_admin_log(
    admin_user_id: str,
    action_type: str,
    target_type: str,
    target_id: str,
    reason: Optional[str] = None,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    request: Optional[Request] = None,
    db: AsyncSession = None
):
    """Create admin action log entry"""
    try:
        log = AdminLog(
            admin_user_id=admin_user_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            old_values=old_values,
            new_values=new_values,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None
        )

        db.add(log)
        await db.commit()

    except Exception as e:
        print(f"Error creating admin log: {e}")
        # Don't fail the main operation if logging fails
        pass


# ============================================================================
# Dashboard & Overview
# ============================================================================

@router.get("/dashboard", response_model=StandardResponse[AdminDashboardResponse])
async def get_admin_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get admin dashboard overview metrics.
    """
    try:
        # Count pending verifications
        verifications_query = select(func.count(Verification.id)).where(
            Verification.status == "pending"
        )
        pending_verifications = (await db.execute(verifications_query)).scalar() or 0

        # Count pending reports
        reports_query = select(func.count(Report.id)).where(
            Report.status == "pending"
        )
        pending_reports = (await db.execute(reports_query)).scalar() or 0

        # Count live streams
        streams_query = select(func.count(Stream.id)).where(
            Stream.status == "live"
        )
        live_streams = (await db.execute(streams_query)).scalar() or 0

        # Count recent transactions (last 24h)
        recent_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        transactions_query = select(func.count(Transaction.id)).where(
            and_(
                Transaction.status == "completed",
                Transaction.created_at >= recent_time
            )
        )
        recent_transactions = (await db.execute(transactions_query)).scalar() or 0

        # Platform health (simplified)
        platform_health = {
            "database_status": "healthy",
            "api_status": "operational",
            "services_status": "operational"
        }

        dashboard_data = AdminDashboardResponse(
            pending_verifications=pending_verifications,
            pending_reports=pending_reports,
            active_users_online=0,  # TODO: Get from Redis
            live_streams_count=live_streams,
            recent_transactions_count=recent_transactions,
            platform_health=platform_health
        )

        return StandardResponse(
            success=True,
            data=dashboard_data,
            message="Dashboard data retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dashboard: {str(e)}"
        )


# ============================================================================
# User Management
# ============================================================================

@router.get("/users")
async def get_all_users(
    search: Optional[str] = Query(None, description="Search username, email, phone"),
    user_status: Optional[str] = Query(None, description="Filter by status: active, suspended, deleted"),
    role: Optional[str] = Query(None, description="Filter by role: buyer, seller, both, admin"),
    verified: Optional[bool] = Query(None, description="Filter by verification status"),
    sort_by: str = Query("joined", description="Sort by: joined, last_active, transactions"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all users with filters and search.
    """
    try:
        query = select(User)

        # Apply filters
        filters = []

        if search:
            search_pattern = f"%{search}%"
            filters.append(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.phone.ilike(search_pattern),
                    User.full_name.ilike(search_pattern)
                )
            )

        if user_status == "active":
            filters.append(User.is_active == True)
        elif user_status == "suspended":
            filters.append(User.is_active == False)

        if role:
            filters.append(User.role == role)

        if verified is not None:
            filters.append(User.is_verified == verified)

        if filters:
            query = query.where(and_(*filters))

        # Apply sorting
        if sort_by == "last_active":
            query = query.order_by(desc(User.last_login_at))
        elif sort_by == "transactions":
            # TODO: Join with transactions and count
            query = query.order_by(desc(User.created_at))
        else:  # joined
            query = query.order_by(desc(User.created_at))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar()

        # Paginate
        query = query.offset((page - 1) * per_page).limit(per_page)

        # Execute
        result = await db.execute(query)
        users = result.scalars().all()

        # Format response
        users_data = [
            {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_verified": user.is_verified,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
            }
            for user in users
        ]

        return PaginatedResponse(
            success=True,
            data=users_data,
            page=page,
            per_page=per_page,
            total=total,
            message="Users retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving users: {str(e)}"
        )


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed user information for admin.
    """
    try:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get verification status
        verification_query = select(Verification).where(Verification.user_id == user_id)
        verification_result = await db.execute(verification_query)
        verification = verification_result.scalar_one_or_none()

        # Get transaction stats
        transaction_stats_query = select(
            func.count(Transaction.id).label("total_transactions"),
            func.sum(Transaction.amount).label("total_spent")
        ).where(
            and_(
                Transaction.buyer_id == user_id,
                Transaction.status == "completed"
            )
        )
        trans_result = await db.execute(transaction_stats_query)
        trans_stats = trans_result.first()

        # Get products count
        products_query = select(func.count(Product.id)).where(Product.seller_id == user_id)
        products_count = (await db.execute(products_query)).scalar() or 0

        user_details = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role,
            "is_verified": user.is_verified,
            "is_active": user.is_active,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "neighborhood": user.neighborhood,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "verification": {
                "status": verification.status if verification else None,
                "type": verification.verification_type if verification else None,
                "submitted_at": verification.submitted_at.isoformat() if verification and verification.submitted_at else None
            },
            "stats": {
                "total_transactions": trans_stats.total_transactions or 0,
                "total_spent": float(trans_stats.total_spent or 0),
                "products_listed": products_count
            }
        }

        return StandardResponse(
            success=True,
            data=user_details,
            message="User details retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user details: {str(e)}"
        )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: UpdateUserRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user fields (admin override).
    """
    try:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Store old values for logging
        old_values = {
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "role": user.role
        }

        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(user, field, value)

        await db.commit()
        await db.refresh(user)

        # Log admin action
        await create_admin_log(
            admin_user_id=str(current_user.id),
            action_type="user_updated",
            target_type="user",
            target_id=user_id,
            old_values=old_values,
            new_values=update_dict,
            request=request,
            db=db
        )

        return StandardResponse(
            success=True,
            data={"id": str(user.id), "updated_fields": list(update_dict.keys())},
            message="User updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    suspend_data: SuspendUserRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Suspend user account.
    """
    try:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update user status
        user.is_active = False
        await db.commit()

        # TODO: Hide all active products
        # TODO: Cancel ongoing transactions
        # TODO: Send notification to user

        # Log admin action
        await create_admin_log(
            admin_user_id=str(current_user.id),
            action_type="user_suspended",
            target_type="user",
            target_id=user_id,
            reason=suspend_data.reason,
            new_values={"duration_days": suspend_data.duration_days},
            request=request,
            db=db
        )

        return StandardResponse(
            success=True,
            data={"user_id": user_id, "suspended": True},
            message="User suspended successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error suspending user: {str(e)}"
        )


@router.post("/users/{user_id}/unsuspend")
async def unsuspend_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reactivate suspended user account.
    """
    try:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Reactivate user
        user.is_active = True
        await db.commit()

        # TODO: Restore products
        # TODO: Send notification to user

        # Log admin action
        await create_admin_log(
            admin_user_id=str(current_user.id),
            action_type="user_unsuspended",
            target_type="user",
            target_id=user_id,
            request=request,
            db=db
        )

        return StandardResponse(
            success=True,
            data={"user_id": user_id, "active": True},
            message="User reactivated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reactivating user: {str(e)}"
        )


# ============================================================================
# Product Management
# ============================================================================

@router.get("/products")
async def get_all_products(
    product_status: Optional[str] = Query(None, description="Filter: active, sold, removed"),
    reported: Optional[bool] = Query(None, description="Only reported products"),
    feed_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all products with admin filters.
    """
    try:
        query = select(Product)

        # Apply filters
        filters = []

        if product_status == "active":
            filters.append(and_(Product.is_available == True, Product.sold_at == None))
        elif product_status == "sold":
            filters.append(Product.sold_at != None)
        elif product_status == "removed":
            filters.append(Product.is_available == False)

        if feed_type:
            filters.append(Product.feed_type == feed_type)

        if search:
            search_pattern = f"%{search}%"
            filters.append(
                or_(
                    Product.title.ilike(search_pattern),
                    Product.description.ilike(search_pattern)
                )
            )

        # TODO: Add filter for reported products

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(desc(Product.created_at))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar()

        # Paginate
        query = query.offset((page - 1) * per_page).limit(per_page)

        # Execute
        result = await db.execute(query)
        products = result.scalars().all()

        products_data = [
            {
                "id": str(product.id),
                "title": product.title,
                "price": float(product.price),
                "category": product.category,
                "feed_type": product.feed_type,
                "is_available": product.is_available,
                "view_count": product.view_count,
                "created_at": product.created_at.isoformat() if product.created_at else None
            }
            for product in products
        ]

        return PaginatedResponse(
            success=True,
            data=products_data,
            page=page,
            per_page=per_page,
            total=total,
            message="Products retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving products: {str(e)}"
        )


@router.delete("/products/{product_id}")
async def remove_product(
    product_id: str,
    removal_data: RemoveProductRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove product (soft delete).
    """
    try:
        query = select(Product).where(Product.id == product_id)
        result = await db.execute(query)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        # Soft delete
        product.is_available = False
        await db.commit()

        # TODO: Notify seller

        # Log admin action
        await create_admin_log(
            admin_user_id=str(current_user.id),
            action_type="product_removed",
            target_type="product",
            target_id=product_id,
            reason=removal_data.reason,
            request=request,
            db=db
        )

        return StandardResponse(
            success=True,
            data={"product_id": product_id, "removed": True},
            message="Product removed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing product: {str(e)}"
        )


# ============================================================================
# Admin Logs
# ============================================================================

@router.get("/logs")
async def get_admin_logs(
    action_type: Optional[str] = Query(None),
    admin_user_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get admin action logs for audit trail.
    """
    try:
        query = select(AdminLog)

        # Apply filters
        filters = []

        if action_type:
            filters.append(AdminLog.action_type == action_type)

        if admin_user_id:
            filters.append(AdminLog.admin_user_id == admin_user_id)

        if filters:
            query = query.where(and_(*filters))

        query = query.order_by(desc(AdminLog.created_at))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar()

        # Paginate
        query = query.offset((page - 1) * per_page).limit(per_page)

        # Execute
        result = await db.execute(query)
        logs = result.scalars().all()

        logs_data = [
            {
                "id": str(log.id),
                "admin_user_id": str(log.admin_user_id),
                "action_type": log.action_type,
                "target_type": log.target_type,
                "target_id": str(log.target_id),
                "reason": log.reason,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]

        return PaginatedResponse(
            success=True,
            data=logs_data,
            page=page,
            per_page=per_page,
            total=total,
            message="Admin logs retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving admin logs: {str(e)}"
        )
