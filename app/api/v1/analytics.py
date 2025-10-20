"""
Analytics endpoints for seller and admin metrics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.analytics_service import analytics_service
from app.schemas.base import StandardResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/seller/overview")
async def get_seller_overview(
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get seller analytics overview for date range.

    Returns:
        - Total sales and revenue
        - Traffic metrics (views)
        - Engagement metrics
        - Top products
        - Top categories
    """
    # Default to last 30 days
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    try:
        metrics = await analytics_service.calculate_seller_metrics(
            seller_id=str(current_user.id),
            start_date=start_date,
            end_date=end_date,
            db=db
        )

        # Calculate conversion rate
        conversion_rate = await analytics_service.calculate_conversion_rate(
            seller_id=str(current_user.id),
            start_date=start_date,
            end_date=end_date,
            db=db
        )

        # Add conversion rate to metrics
        metrics["sales"]["conversion_rate"] = conversion_rate

        return StandardResponse(
            success=True,
            data=metrics,
            message="Seller analytics retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving analytics: {str(e)}"
        )


@router.get("/product/{product_id}")
async def get_product_analytics(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed analytics for a specific product.

    Includes:
        - Total views and unique viewers
        - Engagement (likes, saves)
        - Sales and revenue
        - Conversion rate
    """
    try:
        analytics = await analytics_service.get_product_analytics(
            product_id=product_id,
            db=db
        )

        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

        return StandardResponse(
            success=True,
            data=analytics,
            message="Product analytics retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving product analytics: {str(e)}"
        )


@router.get("/stream/{stream_id}")
async def get_stream_analytics(
    stream_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed analytics for a specific stream.

    Includes:
        - Viewer metrics (peak, unique, average watch time)
        - Engagement (chat, reactions)
        - Products tagged
        - Sales from stream
    """
    try:
        analytics = await analytics_service.get_stream_analytics(
            stream_id=stream_id,
            db=db
        )

        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stream not found"
            )

        return StandardResponse(
            success=True,
            data=analytics,
            message="Stream analytics retrieved successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving stream analytics: {str(e)}"
        )


@router.get("/admin/overview")
async def get_admin_overview(
    start_date: Optional[date] = Query(None, description="Start date (default: 30 days ago)"),
    end_date: Optional[date] = Query(None, description="End date (default: today)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get platform-wide admin overview metrics.

    **Requires admin role**

    Returns:
        - User statistics
        - Content statistics
        - Transaction metrics (GMV, platform revenue)
        - Active users
    """
    # Check admin role
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    try:
        overview = await analytics_service.get_admin_overview(
            start_date=start_date,
            end_date=end_date,
            db=db
        )

        return StandardResponse(
            success=True,
            data=overview,
            message="Admin overview retrieved successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving admin overview: {str(e)}"
        )
