# Souk Loop Backend Tag System - Complete Implementation Prompt (Python/FastAPI)

You are building the complete backend tag system for **Souk Loop**, a hyperlocal social commerce platform for Dubai/UAE. Create a comprehensive, production-ready backend API with database schemas, indexing strategies, search algorithms, and API endpoints using Python and FastAPI.

---

## 📁 PROJECT STRUCTURE

Create the following file structure:

```
/backend
  /app
    /models
      tag.py
      category.py
      product.py
      user.py
      tag_analytics.py
      
    /routers
      tags.py
      products.py
      search.py
      filters.py
      
    /services
      tag_service.py
      search_service.py
      recommendation_service.py
      analytics_service.py
      
    /schemas
      tag_schema.py
      product_schema.py
      filter_schema.py
      response_schema.py
      
    /middleware
      auth.py
      rate_limit.py
      validation.py
      
    /utils
      tag_helpers.py
      search_helpers.py
      geo_helpers.py
      cache.py
      
    /config
      database.py
      settings.py
      constants.py
      
    /aggregations
      tag_analytics_pipeline.py
      search_aggregation_pipeline.py
      
    main.py
    dependencies.py
    
  /tests
    /test_routers
    /test_services
    /test_models
    
  requirements.txt
  .env.example
  README.md
```

---

## 🎯 CORE REQUIREMENTS

### Technology Stack
- **Python 3.11+**
- **FastAPI** for REST API framework
- **MongoDB 6.0+** with PyMongo (sync driver with threading)
- **Pydantic** for data validation
- **Redis** for caching and rate limiting
- **Elasticsearch** (optional) for advanced search
- **AWS S3** (boto3) for media storage
- **JWT** (python-jose) for authentication
- **uvicorn** as ASGI server

### Note on PyMongo with FastAPI
Since FastAPI is async but PyMongo is synchronous, we'll use `asyncio.to_thread()` to run database operations in thread pool, ensuring non-blocking behavior while maintaining PyMongo compatibility.


### Key Features
1. **Dynamic Tag Management** - CRUD operations for all tag types
2. **Advanced Search** - Full-text search with filters and facets
3. **Geospatial Queries** - Location-based product discovery
4. **Tag Analytics** - Performance tracking and trending tags
5. **Smart Recommendations** - AI-powered tag suggestions
6. **Caching Layer** - Redis for frequently accessed data
7. **Rate Limiting** - Protect against abuse
8. **Data Validation** - Pydantic models for input validation
9. **Async Operations** - Non-blocking database operations
10. **OpenAPI Documentation** - Auto-generated API docs

---

## 📦 DEPENDENCIES (`requirements.txt`)

```txt
# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
pymongo==4.6.1
motor==3.3.2  # Keep for Redis async operations only

# Authentication & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Caching & Rate Limiting
redis==5.0.1
aioredis==2.0.1
slowapi==0.1.9

# Data Validation
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.1.0

# AWS & Storage
boto3==1.34.10
aioboto3==12.3.0

# Search (Optional)
elasticsearch==8.11.0

# Utilities
python-dateutil==2.8.2
pytz==2023.3

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
black==23.12.1
```

---

## ⚙️ CONFIGURATION

### Settings (`/app/config/settings.py`)

```python
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Souk Loop API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "souk_loop"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "me-south-1"
    AWS_S3_BUCKET: Optional[str] = None
    
    # Search
    ELASTICSEARCH_URL: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Geospatial
    DEFAULT_SEARCH_RADIUS_KM: float = 5.0
    MAX_SEARCH_RADIUS_KM: float = 50.0
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### Database Configuration (`/app/config/database.py`)

```python
from pymongo import MongoClient, ASCENDING, DESCENDING, GEO2D
from pymongo.database import Database
from typing import Optional
from app.config.settings import get_settings
import asyncio

settings = get_settings()

class DatabaseManager:
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
    
    def connect(self):
        """Connect to MongoDB using PyMongo (sync)"""
        self.client = MongoClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGODB_DB_NAME]
        
        # Create indexes
        self._create_indexes()
        
        print("✅ Connected to MongoDB (PyMongo)")
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("❌ Closed MongoDB connection")
    
    def _create_indexes(self):
        """Create all necessary indexes"""
        # Products collection indexes
        products = self.db.products
        
        # Single field indexes
        products.create_index([("product_id", ASCENDING)], unique=True)
        products.create_index([("primary_category", ASCENDING)])
        products.create_index([("seller_id", ASCENDING)])
        products.create_index([("status", ASCENDING)])
        products.create_index([("created_at", DESCENDING)])
        products.create_index([("search_score", DESCENDING)])
        products.create_index([("brand", ASCENDING)])
        products.create_index([("location.neighborhood", ASCENDING)])
        
        # Geospatial index
        products.create_index([("location.coordinates", "2dsphere")])
        
        # Compound indexes
        products.create_index([
            ("primary_category", ASCENDING),
            ("created_at", DESCENDING)
        ])
        products.create_index([
            ("location.neighborhood", ASCENDING),
            ("primary_category", ASCENDING)
        ])
        products.create_index([
            ("price", ASCENDING),
            ("primary_category", ASCENDING)
        ])
        products.create_index([
            ("seller_id", ASCENDING),
            ("status", ASCENDING)
        ])
        products.create_index([
            ("search_score", DESCENDING),
            ("created_at", DESCENDING)
        ])
        
        # Text index for search
        products.create_index([
            ("title", "text"),
            ("description", "text"),
            ("search_keywords", "text")
        ], weights={
            "title": 10,
            "search_keywords": 5,
            "description": 1
        })
        
        # Tag Analytics indexes
        tag_analytics = self.db.tag_analytics
        tag_analytics.create_index([("tag_id", ASCENDING)], unique=True)
        tag_analytics.create_index([("tag_type", ASCENDING)])
        tag_analytics.create_index([("last_updated", ASCENDING)])
        tag_analytics.create_index([
            ("tag_type", ASCENDING),
            ("metrics.popularity_score", DESCENDING)
        ])
        tag_analytics.create_index([("metrics.trending_score", DESCENDING)])
        
        # Users indexes
        users = self.db.users
        users.create_index([("user_id", ASCENDING)], unique=True)
        users.create_index([("email", ASCENDING)], unique=True)
        users.create_index([("created_at", DESCENDING)])
        
        print("✅ Created MongoDB indexes")
    
    def get_collection(self, name: str):
        """Get a collection from database"""
        return self.db[name]

# Global database manager
db_manager = DatabaseManager()

def get_database() -> Database:
    """Get database instance"""
    return db_manager.db

async def connect_to_mongo():
    """Async wrapper for database connection"""
    await asyncio.to_thread(db_manager.connect)

async def close_mongo_connection():
    """Async wrapper for closing connection"""
    await asyncio.to_thread(db_manager.disconnect)
```
```

---

## 📊 PYDANTIC MODELS & HELPER FUNCTIONS

### Product Model (`/app/models/product.py`)

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

# Enums
class CategoryEnum(str, Enum):
    FASHION = "fashion"
    BEAUTY = "beauty"
    HOME = "home"
    ELECTRONICS = "electronics"
    KIDS_BABY = "kids_baby"
    SPORTS_FITNESS = "sports_fitness"
    AUTOMOTIVE = "automotive"
    SERVICES = "services"

class ConditionEnum(str, Enum):
    BRAND_NEW_SEALED = "brand_new_sealed"
    BRAND_NEW_OPEN_BOX = "brand_new_open_box"
    LIKE_NEW_EXCELLENT = "like_new_excellent"
    GENTLY_USED_GOOD = "gently_used_good"
    USED_FAIR = "used_fair"
    USED_NEEDS_REPAIR = "used_needs_repair"
    REFURBISHED = "refurbished"
    HANDMADE = "handmade"

class SellerTypeEnum(str, Enum):
    INDIVIDUAL = "individual"
    MICRO_INFLUENCER = "micro_influencer"
    MID_INFLUENCER = "mid_influencer"
    VERIFIED_SELLER = "verified_seller"
    POWER_SELLER = "power_seller"
    MOVING_SALE = "moving_sale"
    LOCAL_BUSINESS = "local_business"

class ProductStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SOLD = "sold"
    DELETED = "deleted"

# Embedded Models
class LocationData(BaseModel):
    type: str = "Point"
    coordinates: List[float] = Field(..., min_length=2, max_length=2)  # [longitude, latitude]
    neighborhood: str
    building: Optional[str] = None
    address: Optional[str] = None

class ProductImage(BaseModel):
    url: str
    thumbnail: Optional[str] = None
    order: int = 0

class ProductMetrics(BaseModel):
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    inquiries: int = 0
    impressions: int = 0
    click_through_rate: float = 0.0
    conversion_rate: float = 0.0

class ProductTags(BaseModel):
    lifestyle: List[str] = []
    events: List[str] = []
    urgency: List[str] = []
    audience: List[str] = []
    authenticity: List[str] = []

# Main Product Model (Pydantic BaseModel, not Beanie Document)
class Product(BaseModel):
    # MongoDB _id field
    id: Optional[str] = Field(default=None, alias="_id")
    
    # Basic Information
    product_id: str = Field(default_factory=lambda: f"prod_{uuid.uuid4().hex[:12]}")
    title: str = Field(..., min_length=10, max_length=200)
    description: str = Field(..., max_length=2000)
    price: float = Field(..., ge=0)
    currency: str = "AED"
    
    # Category Classification
    primary_category: CategoryEnum
    subcategory: Optional[str] = None
    tertiary_category: Optional[str] = None
    
    # Condition & Status
    condition: ConditionEnum
    availability: str = "in_stock"
    quantity: int = Field(default=1, ge=0)
    
    # Location Data
    location: LocationData
    
    # Seller Information
    seller_id: str
    seller_type: SellerTypeEnum
    seller_rating: float = Field(default=0.0, ge=0, le=5)
    seller_badges: List[str] = []
    
    # Media
    images: List[ProductImage] = []
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    content_format: Optional[str] = None
    video_duration: Optional[int] = None
    
    # Transaction Options
    transaction_types: List[str] = []
    delivery_options: List[str] = []
    delivery_fee: float = Field(default=0.0, ge=0)
    
    # Multi-Tag System
    tags: ProductTags = ProductTags()
    
    # Brand
    brand: Optional[str] = None
    brand_verified: bool = False
    
    # Engagement Metrics
    metrics: ProductMetrics = ProductMetrics()
    
    # Search Optimization
    search_keywords: List[str] = []
    search_score: float = 0.0
    
    # Status & Timestamps
    status: ProductStatusEnum = ProductStatusEnum.ACTIVE
    is_featured: bool = False
    featured_until: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    sold_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            CategoryEnum: lambda v: v.value,
            ConditionEnum: lambda v: v.value,
            SellerTypeEnum: lambda v: v.value,
            ProductStatusEnum: lambda v: v.value
        }
    
    @validator('search_keywords', always=True)
    def generate_search_keywords(cls, v, values):
        """Auto-generate search keywords"""
        keywords = set()
        
        if 'title' in values and values['title']:
            words = values['title'].lower().split()
            keywords.update([w for w in words if len(w) > 2])
        
        if 'primary_category' in values and values['primary_category']:
            keywords.add(values['primary_category'].value)
        
        if 'subcategory' in values and values['subcategory']:
            keywords.add(values['subcategory'])
        
        if 'brand' in values and values['brand']:
            keywords.add(values['brand'].lower())
        
        if 'location' in values and values['location']:
            keywords.add(values['location'].neighborhood.lower())
        
        return list(keywords)
    
    def calculate_search_score(self) -> float:
        """Calculate dynamic search score"""
        score = 0.0
        
        days_since_creation = (datetime.utcnow() - self.created_at).days
        score += max(0, 100 - days_since_creation)
        
        score += (self.metrics.views or 0) * 0.1
        score += (self.metrics.likes or 0) * 2
        score += (self.metrics.saves or 0) * 5
        score += (self.metrics.inquiries or 0) * 10
        
        score += (self.seller_rating or 0) * 20
        score += len(self.seller_badges) * 15
        
        if self.is_featured:
            score += 200
        
        if 'urgent_sale' in self.tags.urgency:
            score += 50
        if 'leaving_uae' in self.tags.urgency:
            score += 75
        
        return round(score, 2)
    
    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document"""
        data = self.model_dump(by_alias=True, exclude={'id'})
        
        # Convert enums to strings
        if isinstance(data.get('primary_category'), CategoryEnum):
            data['primary_category'] = data['primary_category'].value
        if isinstance(data.get('condition'), ConditionEnum):
            data['condition'] = data['condition'].value
        if isinstance(data.get('seller_type'), SellerTypeEnum):
            data['seller_type'] = data['seller_type'].value
        if isinstance(data.get('status'), ProductStatusEnum):
            data['status'] = data['status'].value
        
        # Recalculate search score before saving
        data['search_score'] = self.calculate_search_score()
        data['updated_at'] = datetime.utcnow()
        
        return data
    
    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> 'Product':
        """Create Product from MongoDB document"""
        if not data:
            return None
        
        # Convert _id to string if it's ObjectId
        if '_id' in data:
            data['_id'] = str(data['_id'])
        
        return cls(**data)


# Database Operations Helper Class
class ProductDB:
    """Helper class for Product database operations using PyMongo"""
    
    def __init__(self, db):
        self.collection = db.products
    
    async def create(self, product: Product) -> Product:
        """Insert a product into database"""
        import asyncio
        
        def _insert():
            doc = product.to_mongo()
            result = self.collection.insert_one(doc)
            doc['_id'] = str(result.inserted_id)
            return Product.from_mongo(doc)
        
        return await asyncio.to_thread(_insert)
    
    async def find_one(self, query: Dict) -> Optional[Product]:
        """Find single product"""
        import asyncio
        
        def _find():
            doc = self.collection.find_one(query)
            return Product.from_mongo(doc) if doc else None
        
        return await asyncio.to_thread(_find)
    
    async def find_many(self, query: Dict, skip: int = 0, limit: int = 20, sort: List = None) -> List[Product]:
        """Find multiple products"""
        import asyncio
        
        def _find():
            cursor = self.collection.find(query).skip(skip).limit(limit)
            if sort:
                cursor = cursor.sort(sort)
            return [Product.from_mongo(doc) for doc in cursor]
        
        return await asyncio.to_thread(_find)
    
    async def update_one(self, query: Dict, update: Dict) -> bool:
        """Update a product"""
        import asyncio
        
        def _update():
            result = self.collection.update_one(query, {'$set': update})
            return result.modified_count > 0
        
        return await asyncio.to_thread(_update)
    
    async def delete_one(self, query: Dict) -> bool:
        """Delete a product (usually soft delete by updating status)"""
        import asyncio
        
        def _delete():
            result = self.collection.update_one(
                query,
                {'$set': {'status': 'deleted', 'updated_at': datetime.utcnow()}}
            )
            return result.modified_count > 0
        
        return await asyncio.to_thread(_delete)
    
    async def count(self, query: Dict) -> int:
        """Count documents"""
        import asyncio
        
        def _count():
            return self.collection.count_documents(query)
        
        return await asyncio.to_thread(_count)
    
    async def aggregate(self, pipeline: List[Dict]) -> List[Dict]:
        """Run aggregation pipeline"""
        import asyncio
        
        def _aggregate():
            return list(self.collection.aggregate(pipeline))
        
        return await asyncio.to_thread(_aggregate)
```

---

### Tag Analytics Model (`/app/models/tag_analytics.py`)

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TagTypeEnum(str, Enum):
    CATEGORY = "category"
    CONDITION = "condition"
    LOCATION = "location"
    LIFESTYLE = "lifestyle"
    EVENT = "event"
    URGENCY = "urgency"
    BRAND = "brand"

class TrendEnum(str, Enum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"

class NeighborhoodStats(BaseModel):
    neighborhood: str
    count: int

class DailyStats(BaseModel):
    date: datetime
    products: int = 0
    impressions: int = 0
    clicks: int = 0
    sales: int = 0

class AnalyticsMetrics(BaseModel):
    total_products: int = 0
    active_products: int = 0
    sold_products: int = 0
    total_impressions: int = 0
    total_clicks: int = 0
    total_views: int = 0
    click_through_rate: float = 0.0
    conversion_rate: float = 0.0
    average_price: float = 0.0
    average_time_to_sell: float = 0.0
    popularity_score: float = 0.0
    trending_score: float = 0.0

class TagAnalytics(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    tag_id: str
    tag_type: TagTypeEnum
    tag_value: str
    metrics: AnalyticsMetrics = AnalyticsMetrics()
    top_neighborhoods: List[NeighborhoodStats] = []
    daily_stats: List[DailyStats] = []
    weekly_trend: TrendEnum = TrendEnum.STABLE
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
    
    def to_mongo(self) -> Dict[str, Any]:
        """Convert to MongoDB document"""
        data = self.model_dump(by_alias=True, exclude={'id'})
        if isinstance(data.get('tag_type'), TagTypeEnum):
            data['tag_type'] = data['tag_type'].value
        if isinstance(data.get('weekly_trend'), TrendEnum):
            data['weekly_trend'] = data['weekly_trend'].value
        return data
    
    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> 'TagAnalytics':
        """Create from MongoDB document"""
        if not data:
            return None
        if '_id' in data:
            data['_id'] = str(data['_id'])
        return cls(**data)


class TagAnalyticsDB:
    """Helper class for TagAnalytics database operations"""
    
    def __init__(self, db):
        self.collection = db.tag_analytics
    
    async def find_one(self, query: Dict) -> Optional[TagAnalytics]:
        import asyncio
        
        def _find():
            doc = self.collection.find_one(query)
            return TagAnalytics.from_mongo(doc) if doc else None
        
        return await asyncio.to_thread(_find)
    
    async def find_many(self, query: Dict, limit: int = 20, sort: List = None) -> List[TagAnalytics]:
        import asyncio
        
        def _find():
            cursor = self.collection.find(query).limit(limit)
            if sort:
                cursor = cursor.sort(sort)
            return [TagAnalytics.from_mongo(doc) for doc in cursor]
        
        return await asyncio.to_thread(_find)
    
    async def update_or_create(self, tag_analytics: TagAnalytics) -> TagAnalytics:
        import asyncio
        
        def _upsert():
            doc = tag_analytics.to_mongo()
            self.collection.update_one(
                {'tag_id': tag_analytics.tag_id},
                {'$set': doc},
                upsert=True
            )
            return tag_analytics
        
        return await asyncio.to_thread(_upsert)
```

---

### User Model (`/app/models/user.py`)

```python
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class SavedSearch(BaseModel):
    name: str
    filters: dict
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserPreferences(BaseModel):
    favorite_categories: List[str] = []
    hidden_tags: List[str] = []
    saved_searches: List[SavedSearch] = []
    followed_sellers: List[str] = []

class SellerProfile(BaseModel):
    seller_type: Optional[str] = None
    rating: float = Field(default=0.0, ge=0, le=5)
    total_sales: int = 0
    badges: List[str] = []
    response_time: Optional[int] = None
    is_verified: bool = False

class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    email: EmailStr
    hashed_password: str
    user_type: str = "buyer"
    default_location: Optional[dict] = None
    preferences: UserPreferences = UserPreferences()
    seller_profile: Optional[SellerProfile] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
    
    def to_mongo(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True, exclude={'id'})
    
    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> 'User':
        if not data:
            return None
        if '_id' in data:
            data['_id'] = str(data['_id'])
        return cls(**data)


class UserDB:
    """Helper class for User database operations"""
    
    def __init__(self, db):
        self.collection = db.users
    
    async def find_one(self, query: Dict) -> Optional[User]:
        import asyncio
        
        def _find():
            doc = self.collection.find_one(query)
            return User.from_mongo(doc) if doc else None
        
        return await asyncio.to_thread(_find)
    
    async def create(self, user: User) -> User:
        import asyncio
        
        def _insert():
            doc = user.to_mongo()
            result = self.collection.insert_one(doc)
            doc['_id'] = str(result.inserted_id)
            return User.from_mongo(doc)
        
        return await asyncio.to_thread(_insert)
```
```

---

## 📋 PYDANTIC SCHEMAS (Request/Response)

### Product Schemas (`/app/schemas/product_schema.py`)

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from app.models.product import (
    CategoryEnum, ConditionEnum, SellerTypeEnum,
    LocationData, ProductImage, ProductTags, ProductMetrics
)

class ProductCreate(BaseModel):
    title: str = Field(..., min_length=10, max_length=200)
    description: str = Field(..., min_length=20, max_length=2000)
    price: float = Field(..., gt=0)
    
    primary_category: CategoryEnum
    subcategory: Optional[str] = None
    
    condition: ConditionEnum
    
    location: LocationData
    
    transaction_types: List[str] = Field(..., min_items=1)
    delivery_options: List[str] = Field(..., min_items=1)
    delivery_fee: float = Field(default=0.0, ge=0)
    
    tags: Optional[ProductTags] = ProductTags()
    
    brand: Optional[str] = None
    
    images: List[ProductImage] = []
    video_url: Optional[str] = None
    
    @validator('transaction_types')
    def validate_transaction_types(cls, v):
        valid_types = [
            'buy_now', 'make_offer', 'auction_style', 'group_buy',
            'flash_sale', 'bnpl_available', 'free_giveaway'
        ]
        for t in v:
            if t not in valid_types:
                raise ValueError(f"Invalid transaction type: {t}")
        return v
    
    @validator('delivery_options')
    def validate_delivery_options(cls, v):
        valid_options = [
            'same_building', 'within_1km', 'free_delivery', 'paid_delivery',
            'buyer_pickup', 'seller_delivers', 'meet_halfway', 'building_lobby'
        ]
        for opt in v:
            if opt not in valid_options:
                raise ValueError(f"Invalid delivery option: {opt}")
        return v

class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=10, max_length=200)
    description: Optional[str] = Field(None, min_length=20, max_length=2000)
    price: Optional[float] = Field(None, gt=0)
    condition: Optional[ConditionEnum] = None
    tags: Optional[ProductTags] = None
    status: Optional[str] = None

class ProductResponse(BaseModel):
    id: str
    product_id: str
    title: str
    description: str
    price: float
    currency: str
    primary_category: str
    subcategory: Optional[str]
    condition: str
    location: LocationData
    seller_id: str
    seller_type: str
    seller_rating: float
    tags: ProductTags
    images: List[ProductImage]
    transaction_types: List[str]
    delivery_options: List[str]
    metrics: ProductMetrics
    search_score: float
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### Filter Schemas (`/app/schemas/filter_schema.py`)

```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from enum import Enum

class SortByEnum(str, Enum):
    NEWEST = "newest"
    PRICE_LOW = "price_low"
    PRICE_HIGH = "price_high"
    DISTANCE = "distance"
    POPULAR = "popular"

class SearchFilters(BaseModel):
    # Text Search
    query: Optional[str] = None
    
    # Category Filters
    categories: List[str] = []
    subcategories: List[str] = []
    
    # Location Filters
    neighborhood: Optional[str] = None
    proximity_km: Optional[float] = Field(None, gt=0, le=50)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    
    # Price Filters
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    
    # Condition Filters
    condition: List[str] = []
    
    # Delivery Filters
    delivery_options: List[str] = []
    
    # Seller Filters
    seller_types: List[str] = []
    min_seller_rating: Optional[float] = Field(None, ge=0, le=5)
    
    # Tag Filters
    lifestyle_tags: List[str] = []
    event_tags: List[str] = []
    urgency_tags: List[str] = []
    
    # Brand Filter
    brands: List[str] = []
    
    # Sorting & Pagination
    sort_by: SortByEnum = SortByEnum.NEWEST
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
    @validator('max_price')
    def max_price_greater_than_min(cls, v, values):
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v < values['min_price']:
                raise ValueError('max_price must be greater than min_price')
        return v

class FacetResponse(BaseModel):
    field: str
    values: List[dict]  # [{"value": "fashion", "count": 150}]

class SearchResponse(BaseModel):
    products: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int
    facets: Optional[List[FacetResponse]] = None
```

---

## 🔌 API ROUTERS

### Tags Router (`/app/routers/tags.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.services.tag_service import TagService
from app.utils.cache import get_cache, set_cache
from app.dependencies import get_current_user
import json

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])

@router.get("/categories")
async def get_categories():
    """Get all categories with product counts"""
    cache_key = "categories:all"
    cached = await get_cache(cache_key)
    
    if cached:
        return json.loads(cached)
    
    categories = await TagService.get_categories_with_counts()
    await set_cache(cache_key, json.dumps(categories), ttl=3600)
    
    return {
        "success": True,
        "data": categories
    }

@router.get("/categories/{category_id}/subcategories")
async def get_subcategories(category_id: str):
    """Get subcategories for a specific category"""
    subcategories = await TagService.get_subcategories(category_id)
    
    return {
        "success": True,
        "data": subcategories
    }

@router.get("/conditions")
async def get_conditions():
    """Get all condition tags"""
    cache_key = "conditions:all"
    cached = await get_cache(cache_key)
    
    if cached:
        return json.loads(cached)
    
    conditions = TagService.get_conditions()
    await set_cache(cache_key, json.dumps(conditions), ttl=86400)  # Cache for 24h
    
    return {
        "success": True,
        "data": conditions
    }

@router.get("/locations")
async def get_locations(
    type: Optional[str] = Query(None, description="Filter by type: neighborhood, city, emirate")
):
    """Get all location tags"""
    cache_key = f"locations:{type or 'all'}"
    cached = await get_cache(cache_key)
    
    if cached:
        return json.loads(cached)
    
    locations = await TagService.get_locations(location_type=type)
    await set_cache(cache_key, json.dumps(locations), ttl=86400)
    
    return {
        "success": True,
        "data": locations
    }

@router.get("/brands")
async def get_brands(
    limit: int = Query(200, ge=1, le=500),
    search: Optional[str] = None
):
    """Get active brands with product counts"""
    if search:
        brands = await TagService.search_brands(search, limit)
    else:
        cache_key = f"brands:top:{limit}"
        cached = await get_cache(cache_key)
        
        if cached:
            return json.loads(cached)
        
        brands = await TagService.get_top_brands(limit)
        await set_cache(cache_key, json.dumps(brands), ttl=3600)
    
    return {
        "success": True,
        "data": brands
    }

@router.get("/trending")
async def get_trending_tags(
    limit: int = Query(20, ge=1, le=50),
    tag_type: Optional[str] = None
):
    """Get trending tags"""
    cache_key = f"trending:{tag_type or 'all'}:{limit}"
    cached = await get_cache(cache_key)
    
    if cached:
        return json.loads(cached)
    
    trending = await TagService.get_trending_tags(limit, tag_type)
    await set_cache(cache_key, json.dumps(trending), ttl=300)  # Cache for 5 min
    
    return {
        "success": True,
        "data": trending
    }

@router.get("/popular/{neighborhood}")
async def get_popular_tags_in_neighborhood(
    neighborhood: str,
    limit: int = Query(10, ge=1, le=30)
):
    """Get popular tags in a specific neighborhood"""
    cache_key = f"popular:{neighborhood}:{limit}"
    cached = await get_cache(cache_key)
    
    if cached:
        return json.loads(cached)
    
    popular = await TagService.get_popular_tags_by_neighborhood(neighborhood, limit)
    await set_cache(cache_key, json.dumps(popular), ttl=1800)  # Cache for 30 min
    
    return {
        "success": True,
        "data": popular
    }

@router.get("/hydrate")
async def hydrate_tag_data(
    user_location: Optional[str] = Query(None, description="User's neighborhood")
):
    """
    Hydration endpoint - returns all tag data needed for frontend initialization
    """
    cache_key = f"hydrate:{user_location or 'global'}"
    cached = await get_cache(cache_key)
    
    if cached:
        return json.loads(cached)
    
    data = {
        "category_stats": await TagService.get_categories_with_counts(),
        "brands": await TagService.get_top_brands(200),
        "trending": await TagService.get_trending_tags(20),
        "locations": await TagService.get_locations()
    }
    
    if user_location:
        data["popular_in_area"] = await TagService.get_popular_tags_by_neighborhood(
            user_location, 10
        )
    
    await set_cache(cache_key, json.dumps(data), ttl=3600)
    
    return {
        "success": True,
        "data": data
    }

@router.get("/analytics/{tag_id}")
async def get_tag_analytics(tag_id: str):
    """Get analytics for a specific tag"""
    from app.models.tag_analytics import TagAnalytics
    
    analytics = await TagAnalytics.find_one(TagAnalytics.tag_id == tag_id)
    
    if not analytics:
        raise HTTPException(status_code=404, detail="Tag analytics not found")
    
    return {
        "success": True,
        "data": analytics.dict()
    }

@router.post("/suggest")
async def suggest_tags(
    title: str,
    description: str,
    category: str,
    current_user = Depends(get_current_user)
):
    """
    AI-powered tag suggestions based on product title and description
    """
    suggestions = await TagService.suggest_tags(title, description, category)
    
    return {
        "success": True,
        "data": suggestions
    }
```

---

### Products Router (`/app/routers/products.py`)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductResponse
from app.models.product import Product, ProductDB
from app.dependencies import get_current_user, get_db
from app.services.tag_service import TagService
from datetime import datetime

router = APIRouter(prefix="/api/v1/products", tags=["products"])

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new product with tags"""
    product_db = ProductDB(db)
    
    # Create product document
    product = Product(
        **product_data.model_dump(),
        seller_id=current_user.user_id,
        seller_type=current_user.seller_profile.seller_type if current_user.seller_profile else "individual",
        seller_rating=current_user.seller_profile.rating if current_user.seller_profile else 0.0
    )
    
    # Save to database
    created_product = await product_db.create(product)
    
    # Update tag analytics asynchronously (non-blocking)
    import asyncio
    asyncio.create_task(TagService.update_tag_analytics(created_product, db))
    
    return created_product

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db = Depends(get_db)
):
    """Get a single product by ID"""
    product_db = ProductDB(db)
    product = await product_db.find_one({"product_id": product_id})
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Increment view count
    await product_db.update_one(
        {"product_id": product_id},
        {"metrics.views": product.metrics.views + 1}
    )
    
    return product

@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update a product"""
    product_db = ProductDB(db)
    product = await product_db.find_one({"product_id": product_id})
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check ownership
    if product.seller_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this product")
    
    # Update fields
    update_data = product_update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.utcnow()
    
    await product_db.update_one(
        {"product_id": product_id},
        update_data
    )
    
    # Fetch updated product
    updated_product = await product_db.find_one({"product_id": product_id})
    return updated_product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Delete a product (soft delete)"""
    product_db = ProductDB(db)
    product = await product_db.find_one({"product_id": product_id})
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check ownership
    if product.seller_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this product")
    
    # Soft delete
    await product_db.delete_one({"product_id": product_id})
    
    return None

@router.patch("/{product_id}/tags")
async def update_product_tags(
    product_id: str,
    tags: dict,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update only the tags of a product"""
    product_db = ProductDB(db)
    product = await product_db.find_one({"product_id": product_id})
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.seller_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Update tags
    await product_db.update_one(
        {"product_id": product_id},
        {"tags": tags, "updated_at": datetime.utcnow()}
    )
    
    updated_product = await product_db.find_one({"product_id": product_id})
    
    return {
        "success": True,
        "message": "Tags updated successfully",
        "data": updated_product.tags
    }
```

---

### Search Router (`/app/routers/search.py`)

```python
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from app.schemas.filter_schema import SearchFilters, SearchResponse
from app.services.search_service import SearchService
from app.dependencies import get_optional_user

router = APIRouter(prefix="/api/v1/search", tags=["search"])

@router.get("/", response_model=SearchResponse)
async def search_products(
    # Text search
    q: Optional[str] = Query(None, description="Search query"),
    
    # Category
    categories: Optional[str] = Query(None, description="Comma-separated category IDs"),
    subcategories: Optional[str] = Query(None, description="Comma-separated subcategory IDs"),
    
    # Location
    neighborhood: Optional[str] = None,
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: Optional[float] = Query(None, gt=0, le=50),
    
    # Price
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    
    # Filters
    condition: Optional[str] = Query(None, description="Comma-separated conditions"),
    seller_types: Optional[str] = Query(None, description="Comma-separated seller types"),
    delivery_options: Optional[str] = Query(None, description="Comma-separated delivery options"),
    brands: Optional[str] = Query(None, description="Comma-separated brands"),
    
    # Tags
    lifestyle_tags: Optional[str] = None,
    event_tags: Optional[str] = None,
    urgency_tags: Optional[str] = None,
    
    # Sort & Pagination
    sort_by: str = Query("newest", description="Sort by: newest, price_low, price_high, distance, popular"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    
    # Optional user for personalization
    current_user = Depends(get_optional_user)
):
    """
    Main search endpoint with comprehensive filtering
    """
    
    # Parse comma-separated values
    filters = SearchFilters(
        query=q,
        categories=categories.split(',') if categories else [],
        subcategories=subcategories.split(',') if subcategories else [],
        neighborhood=neighborhood,
        latitude=lat,
        longitude=lon,
        proximity_km=radius_km,
        min_price=min_price,
        max_price=max_price,
        condition=condition.split(',') if condition else [],
        seller_types=seller_types.split(',') if seller_types else [],
        delivery_options=delivery_options.split(',') if delivery_options else [],
        brands=brands.split(',') if brands else [],
        lifestyle_tags=lifestyle_tags.split(',') if lifestyle_tags else [],
        event_tags=event_tags.split(',') if event_tags else [],
        urgency_tags=urgency_tags.split(',') if urgency_tags else [],
        sort_by=sort_by,
        page=page,
        page_size=page_size
    )
    
    results = await SearchService.search(filters, user=current_user)
    
    return results

@router.post("/filter", response_model=SearchResponse)
async def advanced_search(
    filters: SearchFilters,
    current_user = Depends(get_optional_user)
):
    """
    Advanced search with POST body for complex filters
    """
    results = await SearchService.search(filters, user=current_user)
    return results

@router.get("/nearby", response_model=SearchResponse)
async def search_nearby(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(5.0, gt=0, le=50),
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    Search for products near a specific location (geospatial query)
    """
    results = await SearchService.search_nearby(
        longitude=lon,
        latitude=lat,
        max_distance_km=radius_km,
        category=category,
        page=page,
        page_size=page_size
    )
    
    return results

@router.get("/category/{category_id}")
async def search_by_category(
    category_id: str,
    subcategory: Optional[str] = None,
    neighborhood: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """
    Search products by category
    """
    results = await SearchService.search_by_category(
        category=category_id,
        subcategory=subcategory,
        neighborhood=neighborhood,
        page=page,
        page_size=page_size
    )
    
    return results

@router.post("/facets")
async def get_facets(filters: SearchFilters):
    """
    Get available facets (filter options) for current search results
    """
    facets = await SearchService.get_facets(filters)
    
    return {
        "success": True,
        "data": facets
    }

@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20)
):
    """
    Autocomplete suggestions for search query
    """
    suggestions = await SearchService.autocomplete(q, limit)
    
    return {
        "success": True,
        "data": suggestions
    }
```

---

## 🔧 SERVICES

### Tag Service (`/app/services/tag_service.py`)

```python
from app.models.product import Product, CategoryEnum
from app.models.tag_analytics import TagAnalytics, TagTypeEnum
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import re

class TagService:
    
    @staticmethod
    async def get_categories_with_counts() -> List[Dict]:
        """Get all categories with active product counts"""
        pipeline = [
            {
                "$match": {
                    "status": "active"
                }
            },
            {
                "$group": {
                    "_id": "$primary_category",
                    "count": {"$sum": 1},
                    "avg_price": {"$avg": "$price"}
                }
            },
            {
                "$sort": {"count": -1}
            }
        ]
        
        results = await Product.aggregate(pipeline).to_list()
        
        categories = []
        for result in results:
            categories.append({
                "id": result["_id"],
                "label": result["_id"].replace("_", " ").title(),
                "count": result["count"],
                "avg_price": round(result["avg_price"], 2)
            })
        
        return categories
    
    @staticmethod
    async def get_subcategories(category_id: str) -> List[Dict]:
        """Get subcategories for a specific category with counts"""
        pipeline = [
            {
                "$match": {
                    "primary_category": category_id,
                    "status": "active",
                    "subcategory": {"$exists": True, "$ne": None}
                }
            },
            {
                "$group": {
                    "_id": "$subcategory",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1}
            }
        ]
        
        results = await Product.aggregate(pipeline).to_list()
        
        return [
            {
                "id": r["_id"],
                "label": r["_id"].replace("_", " ").title(),
                "count": r["count"],
                "parent_category": category_id
            }
            for r in results
        ]
    
    @staticmethod
    def get_conditions() -> List[Dict]:
        """Get all condition tags (static)"""
        return [
            {"id": "brand_new_sealed", "label": "Brand New (Sealed)", "icon": "✨"},
            {"id": "brand_new_open_box", "label": "Brand New (Open Box)", "icon": "📦"},
            {"id": "like_new_excellent", "label": "Like New", "icon": "⭐"},
            {"id": "gently_used_good", "label": "Gently Used", "icon": "👍"},
            {"id": "used_fair", "label": "Used (Fair)", "icon": "✓"},
            {"id": "used_needs_repair", "label": "Needs Repair", "icon": "🔧"},
            {"id": "refurbished", "label": "Refurbished", "icon": "♻️"},
            {"id": "handmade", "label": "Handmade", "icon": "✋"},
        ]
    
    @staticmethod
    async def get_locations(location_type: Optional[str] = None) -> List[Dict]:
        """Get all locations with product counts"""
        match_filter = {"status": "active"}
        
        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": "$location.neighborhood",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1}
            },
            {
                "$limit": 100
            }
        ]
        
        results = await Product.aggregate(pipeline).to_list()
        
        return [
            {
                "id": r["_id"],
                "label": r["_id"].replace("_", " ").title(),
                "count": r["count"],
                "type": "neighborhood"
            }
            for r in results if r["_id"]
        ]
    
    @staticmethod
    async def get_top_brands(limit: int = 200) -> List[Dict]:
        """Get top brands with product counts"""
        pipeline = [
            {
                "$match": {
                    "status": "active",
                    "brand": {"$exists": True, "$ne": None, "$ne": ""}
                }
            },
            {
                "$group": {
                    "_id": "$brand",
                    "count": {"$sum": 1},
                    "verified_count": {
                        "$sum": {"$cond": ["$brand_verified", 1, 0]}
                    }
                }
            },
            {
                "$sort": {"count": -1}
            },
            {
                "$limit": limit
            }
        ]
        
        results = await Product.aggregate(pipeline).to_list()
        
        return [
            {
                "id": r["_id"],
                "name": r["_id"],
                "count": r["count"],
                "verified": r["verified_count"] > 0
            }
            for r in results
        ]
    
    @staticmethod
    async def search_brands(query: str, limit: int = 20) -> List[Dict]:
        """Search brands by name"""
        pipeline = [
            {
                "$match": {
                    "status": "active",
                    "brand": {
                        "$regex": f"^{re.escape(query)}",
                        "$options": "i"
                    }
                }
            },
            {
                "$group": {
                    "_id": "$brand",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1}
            },
            {
                "$limit": limit
            }
        ]
        
        results = await Product.aggregate(pipeline).to_list()
        
        return [
            {"id": r["_id"], "name": r["_id"], "count": r["count"]}
            for r in results
        ]
    
    @staticmethod
    async def get_trending_tags(
        limit: int = 20,
        tag_type: Optional[str] = None
    ) -> List[Dict]:
        """Get trending tags based on recent activity"""
        match_filter = {}
        if tag_type:
            match_filter["tag_type"] = tag_type
        
        trending = await TagAnalytics.find(
            match_filter,
            limit=limit,
            sort=[("metrics.trending_score", -1)]
        ).to_list()
        
        return [
            {
                "tag_id": t.tag_id,
                "tag_value": t.tag_value,
                "tag_type": t.tag_type.value,
                "trending_score": t.metrics.trending_score,
                "total_products": t.metrics.total_products
            }
            for t in trending
        ]
    
    @staticmethod
    async def get_popular_tags_by_neighborhood(
        neighborhood: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get most popular tags in a specific neighborhood"""
        # Get most common categories
        pipeline = [
            {
                "$match": {
                    "location.neighborhood": neighborhood,
                    "status": "active"
                }
            },
            {
                "$facet": {
                    "categories": [
                        {
                            "$group": {
                                "_id": "$primary_category",
                                "count": {"$sum": 1}
                            }
                        },
                        {"$sort": {"count": -1}},
                        {"$limit": limit}
                    ],
                    "brands": [
                        {
                            "$match": {"brand": {"$ne": None}}
                        },
                        {
                            "$group": {
                                "_id": "$brand",
                                "count": {"$sum": 1}
                            }
                        },
                        {"$sort": {"count": -1}},
                        {"$limit": limit}
                    ]
                }
            }
        ]
        
        results = await Product.aggregate(pipeline).to_list()
        
        if results:
            return {
                "categories": [
                    {"id": r["_id"], "count": r["count"]}
                    for r in results[0]["categories"]
                ],
                "brands": [
                    {"id": r["_id"], "count": r["count"]}
                    for r in results[0]["brands"]
                ]
            }
        
        return {"categories": [], "brands": []}
    
    @staticmethod
    async def suggest_tags(
        title: str,
        description: str,
        category: str
    ) -> Dict:
        """
        AI-powered tag suggestions based on product content
        Simple keyword extraction for now, can be enhanced with ML
        """
        text = f"{title} {description}".lower()
        
        suggestions = {
            "lifestyle": [],
            "urgency": [],
            "events": [],
            "audience": []
        }
        
        # Lifestyle tags
        if any(word in text for word in ["halal", "islamic", "muslim"]):
            suggestions["lifestyle"].append("halal_certified")
        if any(word in text for word in ["modest", "abaya", "hijab"]):
            suggestions["lifestyle"].append("modest_fashion")
        if any(word in text for word in ["eco", "organic", "natural", "sustainable"]):
            suggestions["lifestyle"].append("eco_friendly")
        if any(word in text for word in ["luxury", "premium", "designer"]):
            suggestions["lifestyle"].append("luxury_premium")
        if any(word in text for word in ["budget", "cheap", "affordable"]):
            suggestions["lifestyle"].append("budget_friendly")
        
        # Urgency tags
        if any(word in text for word in ["urgent", "asap", "quick"]):
            suggestions["urgency"].append("urgent_sale")
        if any(word in text for word in ["leaving", "relocating", "moving out"]):
            suggestions["urgency"].append("leaving_uae")
        if any(word in text for word in ["limited", "few left", "last"]):
            suggestions["urgency"].append("limited_stock")
        if any(word in text for word in ["new arrival", "just arrived", "fresh"]):
            suggestions["urgency"].append("new_arrival")
        
        # Event tags
        current_month = datetime.now().month
        if current_month in [3, 4]:  # Ramadan typically
            suggestions["events"].append("ramadan_special")
        if "eid" in text:
            suggestions["events"].append("eid_collection")
        if "moving" in text or "exit" in text:
            suggestions["events"].append("exit_sale")
        
        return suggestions
    
    @staticmethod
    async def update_tag_analytics(product: Product):
        """
        Update tag analytics when a product is created/updated
        This should ideally run as a background task
        """
        # Update category analytics
        await TagService._update_tag_metric(
            tag_id=f"category_{product.primary_category}",
            tag_type=TagTypeEnum.CATEGORY,
            tag_value=product.primary_category.value
        )
        
        # Update brand analytics if applicable
        if product.brand:
            await TagService._update_tag_metric(
                tag_id=f"brand_{product.brand.lower()}",
                tag_type=TagTypeEnum.BRAND,
                tag_value=product.brand
            )
        
        # Update location analytics
        await TagService._update_tag_metric(
            tag_id=f"location_{product.location.neighborhood}",
            tag_type=TagTypeEnum.LOCATION,
            tag_value=product.location.neighborhood
        )
    
    @staticmethod
    async def _update_tag_metric(tag_id: str, tag_type: TagTypeEnum, tag_value: str):
        """Helper method to update or create tag analytics"""
        analytics = await TagAnalytics.find_one(TagAnalytics.tag_id == tag_id)
        
        if not analytics:
            analytics = TagAnalytics(
                tag_id=tag_id,
                tag_type=tag_type,
                tag_value=tag_value
            )
        
        # Increment counters
        analytics.metrics.total_products += 1
        analytics.metrics.active_products += 1
        analytics.last_updated = datetime.utcnow()
        
        await analytics.save()
```

---

### Search Service (`/app/services/search_service.py`)

```python
from app.models.product import Product
from app.schemas.filter_schema import SearchFilters, SearchResponse, FacetResponse, SortByEnum
from typing import Optional, List, Dict
from math import ceil

class SearchService:
    
    @staticmethod
    async def search(
        filters: SearchFilters,
        user: Optional[any] = None
    ) -> SearchResponse:
        """
        Main search function with comprehensive filtering
        """
        # Build MongoDB query
        query = SearchService._build_query(filters)
        
        # Build sort
        sort_criteria = SearchService._build_sort(filters.sort_by, filters)
        
        # Calculate pagination
        skip = (filters.page - 1) * filters.page_size
        
        # Execute search
        products_cursor = Product.find(
            query,
            skip=skip,
            limit=filters.page_size,
            sort=sort_criteria
        )
        
        products = await products_cursor.to_list()
        
        # Get total count
        total = await Product.find(query).count()
        
        # Convert to dict
        products_data = [p.dict() for p in products]
        
        # Calculate pagination info
        total_pages = ceil(total / filters.page_size) if total > 0 else 0
        
        return SearchResponse(
            products=products_data,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages
        )
    
    @staticmethod
    def _build_query(filters: SearchFilters) -> Dict:
        """Build MongoDB query from filters"""
        query = {"status": "active"}
        
        # Text search
        if filters.query:
            query["$text"] = {"$search": filters.query}
        
        # Category filters
        if filters.categories:
            query["primary_category"] = {"$in": filters.categories}
        
        if filters.subcategories:
            query["subcategory"] = {"$in": filters.subcategories}
        
        # Location filters
        if filters.neighborhood:
            query["location.neighborhood"] = filters.neighborhood
        
        # Geospatial filter
        if filters.latitude and filters.longitude:
            max_distance = (filters.proximity_km or 5.0) * 1000  # Convert to meters
            query["location.coordinates"] = {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [filters.longitude, filters.latitude]
                    },
                    "$maxDistance": max_distance
                }
            }
        
        # Price filters
        if filters.min_price is not None or filters.max_price is not None:
            price_query = {}
            if filters.min_price is not None:
                price_query["$gte"] = filters.min_price
            if filters.max_price is not None:
                price_query["$lte"] = filters.max_price
            query["price"] = price_query
        
        # Condition filter
        if filters.condition:
            query["condition"] = {"$in": filters.condition}
        
        # Delivery options
        if filters.delivery_options:
            query["delivery_options"] = {"$in": filters.delivery_options}
        
        # Seller filters
        if filters.seller_types:
            query["seller_type"] = {"$in": filters.seller_types}
        
        if filters.min_seller_rating is not None:
            query["seller_rating"] = {"$gte": filters.min_seller_rating}
        
        # Tag filters
        if filters.lifestyle_tags:
            query["tags.lifestyle"] = {"$in": filters.lifestyle_tags}
        
        if filters.event_tags:
            query["tags.events"] = {"$in": filters.event_tags}
        
        if filters.urgency_tags:
            query["tags.urgency"] = {"$in": filters.urgency_tags}
        
        # Brand filter
        if filters.brands:
            query["brand"] = {"$in": filters.brands}
        
        return query
    
    @staticmethod
    def _build_sort(sort_by: SortByEnum, filters: SearchFilters) -> List:
        """Build sort criteria"""
        if sort_by == SortByEnum.NEWEST:
            return [("created_at", -1)]
        elif sort_by == SortByEnum.PRICE_LOW:
            return [("price", 1)]
        elif sort_by == SortByEnum.PRICE_HIGH:
            return [("price", -1)]
        elif sort_by == SortByEnum.POPULAR:
            return [("search_score", -1), ("created_at", -1)]
        elif sort_by == SortByEnum.DISTANCE:
            # Distance sort is handled by $near in query
            return [("created_at", -1)]
        else:
            return [("created_at", -1)]
    
    @staticmethod
    async def search_nearby(
        longitude: float,
        latitude: float,
        max_distance_km: float = 5.0,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> SearchResponse:
        """Geospatial search for nearby products"""
        query = {
            "status": "active",
            "location.coordinates": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    },
                    "$maxDistance": max_distance_km * 1000  # Convert to meters
                }
            }
        }
        
        if category:
            query["primary_category"] = category
        
        skip = (page - 1) * page_size
        
        products = await Product.find(
            query,
            skip=skip,
            limit=page_size
        ).to_list()
        
        total = await Product.find(query).count()
        
        return SearchResponse(
            products=[p.dict() for p in products],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if total > 0 else 0
        )
    
    @staticmethod
    async def search_by_category(
        category: str,
        subcategory: Optional[str] = None,
        neighborhood: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> SearchResponse:
        """Search products by category"""
        query = {
            "status": "active",
            "primary_category": category
        }
        
        if subcategory:
            query["subcategory"] = subcategory
        
        if neighborhood:
            query["location.neighborhood"] = neighborhood
        
        skip = (page - 1) * page_size
        
        products = await Product.find(
            query,
            skip=skip,
            limit=page_size,
            sort=[("search_score", -1), ("created_at", -1)]
        ).to_list()
        
        total = await Product.find(query).count()
        
        return SearchResponse(
            products=[p.dict() for p in products],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=ceil(total / page_size) if total > 0 else 0
        )
    
    @staticmethod
    async def get_facets(filters: SearchFilters) -> List[FacetResponse]:
        """
        Get available facets (filter counts) for current search
        """
        query = SearchService._build_query(filters)
        
        pipeline = [
            {"$match": query},
            {
                "$facet": {
                    "categories": [
                        {"$group": {"_id": "$primary_category", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ],
                    "conditions": [
                        {"$group": {"_id": "$condition", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ],
                    "neighborhoods": [
                        {"$group": {"_id": "$location.neighborhood", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}},
                        {"$limit": 20}
                    ],
                    "seller_types": [
                        {"$group": {"_id": "$seller_type", "count": {"$sum": 1}}},
                        {"$sort": {"count": -1}}
                    ],
                    "price_ranges": [
                        {
                            "$bucket": {
                                "groupBy": "$price",
                                "boundaries": [0, 50, 100, 250, 500, 1000, 2500, 5000, 10000],
                                "default": "10000+",
                                "output": {"count": {"$sum": 1}}
                            }
                        }
                    ]
                }
            }
        ]
        
        results = await Product.aggregate(pipeline).to_list()
        
        if not results:
            return []
        
        facets = []
        for field, values in results[0].items():
            facets.append(FacetResponse(
                field=field,
                values=[
                    {"value": v["_id"], "count": v["count"]}
                    for v in values
                ]
            ))
        
        return facets
    
    @staticmethod
    async def autocomplete(query: str, limit: int = 10) -> List[str]:
        """Autocomplete suggestions for search"""
        # Search in product titles and brands
        pipeline = [
            {
                "$match": {
                    "status": "active",
                    "$or": [
                        {"title": {"$regex": f"^{query}", "$options": "i"}},
                        {"brand": {"$regex": f"^{query}", "$options": "i"}}
                    ]
                }
            },
            {
                "$project": {
                    "suggestion": {
                        "$cond": [
                            {"$regexMatch": {"input": "$title", "regex": f"^{query}", "options": "i"}},
                            "$title",
                            "$brand"
                        ]
                    }
                }
            },
            {"$limit": limit}
        ]
        
        results = await Product.aggregate(pipeline).to_list()
        
        suggestions = list(set([r["suggestion"] for r in results if r.get("suggestion")]))
        return suggestions[:limit]
```

---

## 🔒 MIDDLEWARE & DEPENDENCIES

### Auth Dependencies (`/app/dependencies.py`)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config.settings import get_settings
from app.config.database import get_database
from app.models.user import User, UserDB
from typing import Optional

settings = get_settings()
security = HTTPBearer()

def get_db():
    """Get database instance"""
    return get_database()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
) -> User:
    """
    Validate JWT token and return current user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user_db = UserDB(db)
    user = await user_db.find_one({"user_id": user_id})
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns user if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None
```

---

### Rate Limiting (`/app/middleware/rate_limit.py`)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response

limiter = Limiter(key_func=get_remote_address)

def setup_rate_limiting(app):
    """Setup rate limiting for FastAPI app"""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    return limiter
```

---

### Cache Utility (`/app/utils/cache.py`)

```python
import redis.asyncio as redis
from app.config.settings import get_settings
from typing import Optional
import json

settings = get_settings()

class RedisCache:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        self.redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        print("✅ Connected to Redis")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            print("❌ Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        return await self.redis_client.get(key)
    
    async def set(self, key: str, value: str, ttl: int = 3600):
        """Set value in cache with TTL"""
        if not self.redis_client:
            return
        await self.redis_client.setex(key, ttl, value)
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.redis_client:
            return
        await self.redis_client.delete(key)
    
    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern"""
        if not self.redis_client:
            return
        keys = await self.redis_client.keys(pattern)
        if keys:
            await self.redis_client.delete(*keys)

# Global cache instance
cache = RedisCache()

async def get_cache(key: str) -> Optional[str]:
    return await cache.get(key)

async def set_cache(key: str, value: str, ttl: int = 3600):
    await cache.set(key, value, ttl)

async def delete_cache(key: str):
    await cache.delete(key)
```

---

## 🚀 MAIN APPLICATION (`/app/main.py`)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config.database import connect_to_mongo, close_mongo_connection
from app.utils.cache import cache
from app.routers import tags, products, search
from app.middleware.rate_limit import setup_rate_limiting
from app.config.settings import get_settings

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    await cache.connect()
    yield
    # Shutdown
    await close_mongo_connection()
    await cache.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Souk Loop API",
    description="Hyperlocal Social Commerce Platform for Dubai/UAE",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup rate limiting
limiter = setup_rate_limiting(app)

# Include routers
app.include_router(tags.router)
app.include_router(products.router)
app.include_router(search.router)

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Souk Loop API",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

---

## ✅ IMPLEMENTATION CHECKLIST

- [ ] Set up Python virtual environment
- [ ] Install all dependencies from requirements.txt
- [ ] Configure .env file with MongoDB, Redis, JWT secrets
- [ ] Create all Pydantic models in `/app/models`
- [ ] Create all Pydantic schemas in `/app/schemas`
- [ ] Implement all routers in `/app/routers`
- [ ] Implement TagService with all static/dynamic tag methods
- [ ] Implement SearchService with comprehensive filtering
- [ ] Set up MongoDB indexes for performance
- [ ] Implement Redis caching layer
- [ ] Set up authentication middleware
- [ ] Implement rate limiting
- [ ] Create tag analytics aggregation pipeline
- [ ] Test all API endpoints
- [ ] Write unit tests for services
- [ ] Set up API documentation (FastAPI auto-generates)
- [ ] Deploy to production

---

## 📝 EXAMPLE .ENV FILE

```env
# App
APP_NAME=Souk Loop API
DEBUG=False

# Database
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=souk_loop

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AWS (Optional)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=me-south-1
AWS_S3_BUCKET=souk-loop-media

# Search (Optional)
ELASTICSEARCH_URL=http://localhost:9200

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

---

## 🎯 KEY FEATURES IMPLEMENTED

1. ✅ **Complete Tag System** - All 300+ tags from frontend
2. ✅ **Dynamic Tag Management** - Categories, brands, locations with counts
3. ✅ **Advanced Search** - Full-text, geospatial, faceted search
4. ✅ **Tag Analytics** - Performance tracking and trending
5. ✅ **Caching Layer** - Redis for performance
6. ✅ **Rate Limiting** - API protection
7. ✅ **Authentication** - JWT-based auth
8. ✅ **Geospatial Queries** - MongoDB 2dsphere indexes
9. ✅ **Async Operations** - Non-blocking I/O
10. ✅ **Auto-Generated Docs** - OpenAPI/Swagger UI

---

This provides a complete, production-ready Python/FastAPI backend implementation for the Souk Loop tag system!
  // Basic Information
  productId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  title: {
    type: String,
    required: true,
    trim: true,
    maxlength: 200,
    index: 'text'
  },
  description: {
    type: String,
    required: true,
    maxlength: 2000,
    index: 'text'
  },
  price: {
    type: Number,
    required: true,
    min: 0,
    index: true
  },
  currency: {
    type: String,
    default: 'AED',
    enum: ['AED', 'USD', 'EUR']
  },
  
  // Category Classification
  primaryCategory: {
    type: String,
    required: true,
    index: true,
    enum: [
      'fashion', 'beauty', 'home', 'electronics', 
      'kids_baby', 'sports_fitness', 'automotive', 'services'
    ]
  },
  subcategory: {
    type: String,
    index: true
  },
  tertiaryCategory: {
    type: String,
    index: true
  },
  
  // Condition & Status
  condition: {
    type: String,
    required: true,
    index: true,
    enum: [
      'brand_new_sealed', 'brand_new_open_box', 'like_new_excellent',
      'gently_used_good', 'used_fair', 'used_needs_repair',
      'refurbished', 'handmade'
    ]
  },
  availability: {
    type: String,
    default: 'in_stock',
    enum: ['in_stock', 'out_of_stock', 'pre_order', 'sold']
  },
  quantity: {
    type: Number,
    default: 1,
    min: 0
  },
  
  // Location Data (GeoJSON for geospatial queries)
  location: {
    type: {
      type: String,
      enum: ['Point'],
      default: 'Point'
    },
    coordinates: {
      type: [Number], // [longitude, latitude]
      required: true,
      index: '2dsphere'
    },
    neighborhood: {
      type: String,
      required: true,
      index: true
    },
    building: String,
    address: String
  },
  
  // Seller Information
  sellerId: {
    type: Schema.Types.ObjectId,
    ref: 'User',
    required: true,
    index: true
  },
  sellerType: {
    type: String,
    required: true,
    index: true,
    enum: [
      'individual', 'micro_influencer', 'mid_influencer',
      'verified_seller', 'power_seller', 'moving_sale', 'local_business'
    ]
  },
  sellerRating: {
    type: Number,
    min: 0,
    max: 5,
    default: 0
  },
  sellerBadges: [{
    type: String,
    enum: ['verified', 'power_seller', 'quick_responder', 'top_rated']
  }],
  
  // Media
  images: [{
    url: String,
    thumbnail: String,
    order: Number
  }],
  videoUrl: String,
  thumbnailUrl: String,
  contentFormat: {
    type: String,
    enum: [
      'live_stream', 'recorded_video', 'short_form_60s',
      'haul_video', 'unboxing', 'tutorial_howto', 'review', 'try_on'
    ]
  },
  videoDuration: Number, // in seconds
  
  // Transaction Options
  transactionTypes: [{
    type: String,
    required: true,
    enum: [
      'buy_now', 'make_offer', 'auction_style', 'group_buy',
      'flash_sale', 'bnpl_available', 'free_giveaway'
    ]
  }],
  deliveryOptions: [{
    type: String,
    required: true,
    enum: [
      'same_building', 'within_1km', 'free_delivery', 'paid_delivery',
      'buyer_pickup', 'seller_delivers', 'meet_halfway', 'building_lobby'
    ]
  }],
  deliveryFee: {
    type: Number,
    min: 0
  },
  
  // Multi-Tag System
  tags: {
    lifestyle: [{
      type: String,
      index: true
    }],
    events: [{
      type: String,
      index: true
    }],
    urgency: [{
      type: String,
      index: true
    }],
    audience: [{
      type: String,
      index: true
    }],
    authenticity: [{
      type: String,
      index: true
    }]
  },
  
  // Brand
  brand: {
    type: String,
    index: true
  },
  brandVerified: {
    type: Boolean,
    default: false
  },
  
  // Engagement Metrics
  metrics: {
    views: { type: Number, default: 0 },
    likes: { type: Number, default: 0 },
    comments: { type: Number, default: 0 },
    shares: { type: Number, default: 0 },
    saves: { type: Number, default: 0 },
    inquiries: { type: Number, default: 0 },
    impressions: { type: Number, default: 0 },
    clickThroughRate: { type: Number, default: 0 },
    conversionRate: { type: Number, default: 0 }
  },
  
  // Search Optimization
  searchKeywords: [{
    type: String,
    index: true
  }],
  searchScore: {
    type: Number,
    default: 0,
    index: true
  },
  
  // Status & Timestamps
  status: {
    type: String,
    default: 'active',
    enum: ['active', 'inactive', 'pending', 'sold', 'deleted']
  },
  featuredUntil: Date,
  isFeatured: {
    type: Boolean,
    default: false,
    index: true
  },
  
  createdAt: {
    type: Date,
    default: Date.now,
    index: true
  },
  updatedAt: {
    type: Date,
    default: Date.now
  },
  soldAt: Date
}, {
  timestamps: true,
  collection: 'products'
});

// Compound Indexes for Common Queries
ProductSchema.index({ primaryCategory: 1, createdAt: -1 });
ProductSchema.index({ 'location.neighborhood': 1, primaryCategory: 1 });
ProductSchema.index({ price: 1, primaryCategory: 1 });
ProductSchema.index({ sellerId: 1, status: 1 });
ProductSchema.index({ status: 1, createdAt: -1 });
ProductSchema.index({ searchScore: -1, createdAt: -1 });
ProductSchema.index({ 'location.coordinates': '2dsphere' });

// Text Index for Full-Text Search
ProductSchema.index({
  title: 'text',
  description: 'text',
  'searchKeywords': 'text'
}, {
  weights: {
    title: 10,
    searchKeywords: 5,
    description: 1
  }
});

// Pre-save Middleware
ProductSchema.pre('save', function(next) {
  // Auto-generate search keywords
  if (this.isModified('title') || this.isModified('description')) {
    const keywords = new Set();
    
    // Extract words from title
    this.title.toLowerCase().split(/\s+/).forEach(word => {
      if (word.length > 2) keywords.add(word);
    });
    
    // Add category as keyword
    keywords.add(this.primaryCategory);
    if (this.subcategory) keywords.add(this.subcategory);
    
    // Add brand as keyword
    if (this.brand) keywords.add(this.brand.toLowerCase());
    
    // Add location as keyword
    keywords.add(this.location.neighborhood.toLowerCase());
    
    this.searchKeywords = Array.from(keywords);
  }
  
  // Calculate search score
  this.searchScore = this.calculateSearchScore();
  
  next();
});

// Instance Methods
ProductSchema.methods.calculateSearchScore = function() {
  let score = 0;
  
  // Recency boost (newer = higher score)
  const daysSinceCreation = (Date.now() - this.createdAt) / (1000 * 60 * 60 * 24);
  score += Math.max(0, 100 - daysSinceCreation);
  
  // Engagement boost
  score += (this.metrics.views || 0) * 0.1;
  score += (this.metrics.likes || 0) * 2;
  score += (this.metrics.saves || 0) * 5;
  score += (this.metrics.inquiries || 0) * 10;
  
  // Seller reputation boost
  score += (this.sellerRating || 0) * 20;
  score += this.sellerBadges.length * 15;
  
  // Featured boost
  if (this.isFeatured) score += 200;
  
  // Urgency boost
  if (this.tags.urgency.includes('urgent_sale')) score += 50;
  if (this.tags.urgency.includes('leaving_uae')) score += 75;
  
  return Math.round(score);
};

ProductSchema.methods.toJSON = function() {
  const obj = this.toObject();
  delete obj.__v;
  return obj;
};

// Static Methods
ProductSchema.statics.findByNeighborhood = function(neighborhood, filters = {}) {
  return this.find({
    'location.neighborhood': neighborhood,
    status: 'active',
    ...filters
  });
};

ProductSchema.statics.findNearby = function(longitude, latitude, maxDistance = 5000, filters = {}) {
  return this.find({
    'location.coordinates': {
      $near: {
        $geometry: {
          type: 'Point',
          coordinates: [longitude, latitude]
        },
        $maxDistance: maxDistance // in meters
      }
    },
    status: 'active',
    ...filters
  });
};

module.exports = mongoose.model('Product', ProductSchema);
```

---

### 2. Tag Analytics Schema (`/models/TagAnalytics.model.js`)

```javascript
const mongoose = require('mongoose');
const { Schema } = mongoose;

const TagAnalyticsSchema = new Schema({
  tagId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  tagType: {
    type: String,
    required: true,
    enum: ['category', 'condition', 'location', 'lifestyle', 'event', 'urgency', 'brand']
  },
  tagValue: {
    type: String,
    required: true
  },
  
  // Performance Metrics
  metrics: {
    totalProducts: { type: Number, default: 0 },
    activeProducts: { type: Number, default: 0 },
    soldProducts: { type: Number, default: 0 },
    
    totalImpressions: { type: Number, default: 0 },
    totalClicks: { type: Number, default: 0 },
    totalViews: { type: Number, default: 0 },
    
    clickThroughRate: { type: Number, default: 0 },
    conversionRate: { type: Number, default: 0 },
    
    averagePrice: { type: Number, default: 0 },
    averageTimeToSell: { type: Number, default: 0 }, // in hours
    
    popularityScore: { type: Number, default: 0 },
    trendingScore: { type: Number, default: 0 }
  },
  
  // Geographic Distribution
  topNeighborhoods: [{
    neighborhood: String,
    count: Number
  }],
  
  // Temporal Data
  dailyStats: [{
    date: Date,
    products: Number,
    impressions: Number,
    clicks: Number,
    sales: Number
  }],
  
  // Last 7 days trend
  weeklyTrend: {
    type: String,
    enum: ['rising', 'falling', 'stable'],
    default: 'stable'
  },
  
  lastUpdated: {
    type: Date,
    default: Date.now
  }
}, {
  timestamps: true,
  collection: 'tag_analytics'
});

// Indexes
TagAnalyticsSchema.index({ tagType: 1, 'metrics.popularityScore': -1 });
TagAnalyticsSchema.index({ 'metrics.trendingScore': -1 });
TagAnalyticsSchema.index({ lastUpdated: 1 });

module.exports = mongoose.model('TagAnalytics', TagAnalyticsSchema);
```

---

### 3. User Schema (Simplified for Tag Context)

```javascript
const mongoose = require('mongoose');
const { Schema } = mongoose;

const UserSchema = new Schema({
  userId: {
    type: String,
    required: true,
    unique: true,
    index: true
  },
  email: {
    type: String,
    required: true,
    unique: true,
    lowercase: true
  },
  
  // User Type
  userType: {
    type: String,
    required: true,
    enum: ['buyer', 'seller', 'both'],
    default: 'buyer'
  },
  
  // Location Preferences
  defaultLocation: {
    neighborhood: String,
    coordinates: [Number] // [longitude, latitude]
  },
  
  // Tag Preferences
  preferences: {
    favoriteCategories: [String],
    hiddenTags: [String],
    savedSearches: [{
      name: String,
      filters: Schema.Types.Mixed,
      createdAt: Date
    }],
    followedSellers: [{
      type: Schema.Types.ObjectId,
      ref: 'User'
    }]
  },
  
  // Seller Profile (if applicable)
  sellerProfile: {
    sellerType: String,
    rating: { type: Number, default: 0 },
    totalSales: { type: Number, default: 0 },
    badges: [String],
    responseTime: Number, // in minutes
    isVerified: { type: Boolean, default: false }
  },
  
  createdAt: {
    type: Date,
    default: Date.now
  }
}, {
  timestamps: true,
  collection: 'users'
});

UserSchema.index({ 'defaultLocation.neighborhood': 1 });
UserSchema.index({ 'preferences.favoriteCategories': 1 });

module.exports = mongoose.model('User', UserSchema);
```

---

## 🔌 API ENDPOINTS

### 1. Tag Management Routes (`/routes/tags.routes.js`)

```javascript
const express = require('express');
const router = express.Router();
const tagsController = require('../controllers/tags.controller');
const { authenticate } = require('../middleware/auth.middleware');
const { validateTagQuery } = require('../validators/tag.validator');

// Public Routes
router.get('/categories', tagsController.getCategories);
router.get('/categories/:categoryId/subcategories', tagsController.getSubcategories);
router.get('/conditions', tagsController.getConditions);
router.get('/locations', tagsController.getLocations);
router.get('/delivery-options', tagsController.getDeliveryOptions);
router.get('/transaction-types', tagsController.getTransactionTypes);

// Dynamic Tag Routes
router.get('/brands', tagsController.getBrands);
router.get('/brands/search', tagsController.searchBrands);
router.get('/trending', tagsController.getTrendingTags);
router.get('/popular/:neighborhood', tagsController.getPopularTagsInNeighborhood);

// Tag Analytics
router.get('/analytics/:tagId', tagsController.getTagAnalytics);
router.get('/analytics/category/:categoryId', tagsController.getCategoryAnalytics);

// Hydration Endpoint (for frontend initialization)
router.get('/hydrate', validateTagQuery, tagsController.hydrateTagData);

// Protected Routes (Admin/Seller)
router.post('/suggest', authenticate, tagsController.suggestTags);
router.get('/performance', authenticate, tagsController.getTagPerformance);

module.exports = router;
```

---

### 2. Product Routes (`/routes/products.routes.js`)

```javascript
const express = require('express');
const router = express.Router();
const productsController = require('../controllers/products.controller');
const { authenticate } = require('../middleware/auth.middleware');
const { validateProduct } = require('../validators/product.validator');
const { rateLimit } = require('../middleware/rateLimit.middleware');

// Create Product with Tags
router.post('/', 
  authenticate, 
  validateProduct, 
  rateLimit({ max: 10, windowMs: 60000 }),
  productsController.createProduct
);

// Update Product Tags
router.patch('/:productId/tags', 
  authenticate, 
  productsController.updateProductTags
);

// Get Product with Tag Details
router.get('/:productId', productsController.getProduct);

// Delete Product
router.delete('/:productId', authenticate, productsController.deleteProduct);

module.exports = router;
```

---

### 3. Search & Filter Routes (`/routes/search.routes.js`)

```javascript
const express = require('express');
const router = express.Router();
const searchController = require('../controllers/search.controller');
const { validateSearchQuery } = require('../validators/search.validator');

// Main Search Endpoint
router.get('/', validateSearchQuery, searchController.searchProducts);

// Advanced Filter Search
router.post('/filter', validateSearchQuery, searchController.advancedSearch);

// Nearby Products (Geospatial)
router.get('/nearby', searchController.searchNearby);

// Category-specific Search
router.get('/category/:categoryId', searchController.searchByCategory);

// Faceted Search (get available filters for current results)
router.post('/facets', searchController.getFacets);

// Autocomplete
router.get('/autocomplete', searchController.autocomplete);

module.exports = router;
```

---

## 🎮 CONTROLLERS

### Tags Controller (`/controllers/tags.controller.js`)

```javascript
const TagService = require('../services/tagService');
const cache = require('../utils/cache');

class TagsController {
  // Get all categories with counts
  async getCategories(req, res) {
    try {
      const cacheKey = 'categories:all';
      let categories = await cache.get(cacheKey);
      
      if (!categories) {
        categories = await TagService.getCategoriesWithCounts();
        await cache.set(cacheKey, categories, 3600); // Cache for 1 hour
      }
      
      res.json({
        success: true,
        data: categories
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  }
  
  // Get subcategories for a category
  async getSubcategories(req, res) {
    try {
      const { categoryId } = req.params;
      const subcategories = await TagService.getSubcategories(categoryId);
      
      res.json({
        success: true,
        data: subcategories
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: error.message
      });
    }
  }
  
  // Get trending tags
  async getTrendingTags(req, res) {
    try {
      const { limit = 20, type } = req.query;
      const cacheKey = `trending:${type || 'all'}:${limit}`;
      
      let trending = await cache.get(cacheKey);
      
      if (!trending) {
        trending = await TagService.getTrendingTags(limit, type);
        await cache.set(cacheKey, trending, 300); // Cache for 5 minutes
      }
      
      res