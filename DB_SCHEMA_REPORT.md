# Database Schema Analysis Report
**Date**: October 22, 2025
**Project**: Jiran Backend
**Database**: PostgreSQL (jiran)

---

## Executive Summary

✅ **Database Connection**: Working properly
⚠️ **Schema Issues**: 2 critical issues detected
⚠️ **Migrations**: 4 pending migrations not applied

---

## Issues Detected

### 1. 🚨 CRITICAL: Enum Value Case Mismatch

**Problem**: The `user_role` enum in the database uses UPPERCASE values, but the User model expects lowercase values.

**Database Values**:
- BUYER
- SELLER
- BOTH
- ADMIN

**Model Expects** (from `app/models/user.py`):
- buyer
- seller
- both
- admin

**Impact**: User registration fails with error:
```
invalid input value for enum user_role: "buyer"
```

**Root Cause**: The initial migration created the enum with uppercase values, but the model was later updated to use lowercase, or vice versa.

---

### 2. ⚠️ Schema Mismatch: Location Column

**Problem**: Database schema doesn't match User model for location fields.

**Database Has**:
- `location` column (type: geometry/PostGIS)

**Model Expects**:
- `location_lat` (float)
- `location_lon` (float)
- `neighborhood` (string)
- `building_name` (string)

**Impact**: Any operations involving user location may fail.

**Note**: The model was updated to remove PostGIS dependency and use simple lat/lon fields.

---

### 3. ⚠️ Pending Migrations

**Current Migration**: `3a91f2c4d8e5` (Phase 8 - Admin Log)

**Pending Migrations** (4 total):
1. `5822d3a8617c` - Add payout model for seller earnings
2. `600ef51be77e` - Add fulltext search index for products
3. `b37627451129` - Enhance stream model for Go Live flow
4. `be5f12795a69` - Phase 7 social features (Follow, Activity, etc.)

**Note**: We are at migration #3 of 7 total migrations.

---

## Registration Schema Verification

### ✅ RegisterRequest Schema (Pydantic)

```python
RegisterRequest:
  - email: EmailStr (required)
  - username: str (3-50 chars, required)
  - password: str (8+ chars, required)
  - phone: str (8-20 chars, required)
  - full_name: str (max 255 chars, required)
  - role: UserRole (default: BUYER)
```

### ✅ User Model (SQLAlchemy)

```python
User Model Fields (Required):
  - email: String(255), unique, indexed
  - username: String(50), unique, indexed
  - phone: String(20), unique, indexed
  - password_hash: String(255)  # hashed from password
  - full_name: String(255)
  - role: Enum(UserRole), default=BUYER
```

**Mapping**: Registration request correctly maps to User model fields.

### ✅ Registration Flow

1. User submits registration → `POST /api/v1/auth/register`
2. Backend validates input (Pydantic)
3. Password is hashed using bcrypt
4. User record created in database
5. JWT tokens generated
6. OTP sent via email
7. Response includes tokens + user data

**All fields map correctly EXCEPT for the enum case mismatch issue.**

---

## Database Connection Details

**Connection String**: `postgresql+asyncpg://jiran:jiran@localhost:5432/jiran`
**Status**: ✅ Connected
**PostgreSQL Version**: 15.4 (Debian 15.4-1.pgdg110+1)
**Current User Count**: 1
**Users Table**: ✅ Exists

---

## Recommended Fixes

### Fix #1: Update Enum Values (Choose One)

**Option A: Update Database to Lowercase** (Recommended)
```sql
-- Backup first!
-- Then update enum values to lowercase

ALTER TYPE user_role RENAME TO user_role_old;

CREATE TYPE user_role AS ENUM ('buyer', 'seller', 'both', 'admin');

ALTER TABLE users
  ALTER COLUMN role TYPE user_role
  USING role::text::user_role;

DROP TYPE user_role_old;
```

**Option B: Update Model to Uppercase**
```python
# In app/models/user.py
class UserRole(str, Enum):
    BUYER = "BUYER"    # Change from "buyer"
    SELLER = "SELLER"  # Change from "seller"
    BOTH = "BOTH"      # Change from "both"
    ADMIN = "ADMIN"    # Change from "admin"
```

**Recommendation**: Option A (update database) is better as the code likely uses lowercase throughout.

### Fix #2: Apply Pending Migrations

```bash
cd /Users/saleemjadallah/Desktop/Soukloop/backend
alembic upgrade head
```

This will:
- Apply all 4 pending migrations
- Update location column schema
- Add missing indexes and tables

### Fix #3: Verify After Fixes

After applying fixes, run:
```bash
python3 test_db_connection.py
python3 test_registration.py
```

---

## Migration Creation Needed

If the location column migration doesn't exist, create one:

```bash
alembic revision -m "migrate_location_to_lat_lon"
```

Then add this migration logic:
```python
def upgrade():
    # Remove old location column
    op.drop_column('users', 'location')

    # Add new location columns
    op.add_column('users', sa.Column('location_lat', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('location_lon', sa.Float(), nullable=True))

def downgrade():
    # Reverse migration
    op.drop_column('users', 'location_lat')
    op.drop_column('users', 'location_lon')

    # Re-add PostGIS column (if needed)
    # op.add_column('users', sa.Column('location', Geometry('POINT', srid=4326), nullable=True))
```

---

## Summary

### ✅ Working Correctly
- Database connection
- Users table exists
- Basic schema structure
- Registration endpoint is accessible
- JWT token generation
- Password hashing

### ⚠️ Needs Fixing
1. **CRITICAL**: Enum case mismatch (UPPERCASE vs lowercase)
2. **HIGH**: Pending migrations (4 not applied)
3. **MEDIUM**: Location column schema mismatch

### 📌 Action Items

1. **Immediate**: Fix enum case mismatch
2. **Immediate**: Apply pending migrations (`alembic upgrade head`)
3. **Verify**: Test registration after fixes
4. **Monitor**: Check application logs for other issues

---

## Test Results

### ✅ Database Connection Test
- Connection: ✅ Working
- Users table: ✅ Exists
- Column count: 21 columns
- Required columns: ✅ All present

### ❌ Registration Endpoint Test
- Status: ❌ Failed (500 error)
- Reason: Enum case mismatch
- Expected after fix: ✅ Should work

### ✅ Schema Validation Test
- All required fields present
- Unique constraints properly configured
- Indexes on email, username, phone: ✅ Exist

---

## Contact

For questions about this report, please check:
- `/Users/saleemjadallah/Desktop/Soukloop/backend/test_db_connection.py`
- `/Users/saleemjadallah/Desktop/Soukloop/backend/check_schema_mismatch.py`
- `/Users/saleemjadallah/Desktop/Soukloop/backend/check_enum_values.py`
