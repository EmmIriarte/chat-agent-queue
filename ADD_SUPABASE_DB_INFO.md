# Supabase Database Connection Setup

## Steps to Add Supabase Database Connection

### 1. Get Your Supabase Database Connection String

1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to **Settings** → **Database**
4. Look for **Connection string** section
5. You'll see something like:
   ```
   Host: db.daytrevkzlyeaqxcsmdq.supabase.co
   Database: postgres
   Port: 5432
   User: postgres.XXXXX
   Password: [Your database password]
   ```

### 2. Update Cloud Build Configuration

Add these new substitution variables to your Cloud Build configuration:

```bash
# In deploy-gcp.sh, add these to the substitutions:
_SUPABASE_DB_HOST=db.daytrevkzlyeaqxcsmdq.supabase.co
_SUPABASE_DB_PORT=5432
_SUPABASE_DB_NAME=postgres
_SUPABASE_DB_USER=postgres.YOUR_USER_ID
_SUPABASE_DB_PASSWORD=YOUR_DATABASE_PASSWORD
```

### 3. Run the SQL Schema in Supabase

Go to **Supabase Dashboard** → **SQL Editor** and run the contents of `supabase_schema.sql` to create all the tables.

### 4. Test the Connection

After deploying, check the logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=chat-agent-queue" --limit=20
```

Look for:
- "✅ Supabase PostgreSQL pool created"
- Connection errors (if any)

## Benefits

✅ **Persistent data** - Survives restarts, deploys, and cold starts  
✅ **Simpler architecture** - No local PostgreSQL  
✅ **Better performance** - Supabase is optimized and managed  
✅ **Automatic backups** - Supabase handles backups  
✅ **Scalable** - Supabase scales with your usage

