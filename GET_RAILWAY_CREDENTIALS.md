# Get Railway PostgreSQL Credentials

## Quick Steps:

1. **Go to Railway Dashboard:**
   - Visit: https://railway.app/dashboard
   - Login if needed

2. **Select Your Project:**
   - Find your Jiran backend project
   - Click on it to open

3. **Find PostgreSQL Service:**
   - Look for the **PostgreSQL** service/database
   - Click on it

4. **Get Variables:**
   - Click on the **Variables** tab (or **Connect** tab)
   - You'll see these variables (copy them):

```
PGHOST=containers-us-west-XXX.railway.app
PGPORT=5432
PGDATABASE=railway (or jiran)
PGUSER=postgres
PGPASSWORD=XXX-YOUR-PASSWORD-XXX
```

5. **Alternative - Connection String:**
   - Or look for `DATABASE_URL` or `DATABASE_PRIVATE_URL`
   - Format: `postgresql://user:password@host:port/database`

## Example:

If you see:
```
DATABASE_URL=postgresql://postgres:mypass123@containers-us-west-123.railway.app:5432/railway
```

Then your credentials are:
- **PGHOST**: `containers-us-west-123.railway.app`
- **PGPORT**: `5432`
- **PGDATABASE**: `railway`
- **PGUSER**: `postgres`
- **PGPASSWORD**: `mypass123`

## What to Do Next:

Once you have these credentials, paste them here in the format:

```
PGHOST=your-host-here
PGPORT=5432
PGDATABASE=your-database-name
PGUSER=your-user
PGPASSWORD=your-password
```

I'll then update the Directus configuration and connect it to your production database!

---

**Security Note:** These are production credentials - keep them secure and never commit to git!
