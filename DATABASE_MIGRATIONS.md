# Database Migrations with Alembic

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations.

## Setup

### 1. Install Alembic
```bash
pip install -r requirements.txt
```

### 2. Initialize Alembic (First Time Only)
```bash
# Initialize Alembic in the project
alembic init alembic

# This creates:
# - alembic/          # Migration scripts directory
# - alembic.ini       # Configuration file
```

### 3. Configure Alembic

Edit `alembic.ini`:
```ini
# Set database URL (or use environment variable)
sqlalchemy.url = postgresql://user:password@localhost/dbname

# Or use environment variable (recommended):
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

Edit `alembic/env.py`:
```python
# Import your models
from src.database import Base

# Set target metadata
target_metadata = Base.metadata
```

## Common Operations

### Create a New Migration

After modifying models in `src/database.py`:

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column to videos table"

# This creates a new file in alembic/versions/
```

### Apply Migrations

```bash
# Upgrade to latest version
alembic upgrade head

# Upgrade by +1 version
alembic upgrade +1

# Downgrade by -1 version
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

### Manual Migrations

For complex changes, create an empty migration:

```bash
alembic revision -m "Complex schema change"
```

Then edit the generated file in `alembic/versions/`:

```python
def upgrade():
    op.add_column('videos', sa.Column('new_field', sa.String(255)))
    op.create_index('idx_new_field', 'videos', ['new_field'])

def downgrade():
    op.drop_index('idx_new_field', table_name='videos')
    op.drop_column('videos', 'new_field')
```

## Migration Best Practices

### 1. Always Review Auto-Generated Migrations
```bash
# After generating, review the file before applying
alembic revision --autogenerate -m "Description"
# Check alembic/versions/xxxx_description.py
```

### 2. Test Migrations Locally First
```bash
# Create a test database
createdb test_voyoutube

# Test migration
DATABASE_URL=postgresql://localhost/test_voyoutube alembic upgrade head

# Test downgrade
DATABASE_URL=postgresql://localhost/test_voyoutube alembic downgrade -1
```

### 3. Backup Before Production Migrations
```bash
# Backup production database
pg_dump -h hostname -U username dbname > backup_$(date +%Y%m%d_%H%M%S).sql

# Then apply migration
alembic upgrade head
```

### 4. Handle Data Migrations Carefully
```python
# Example: Populate new column with default values
def upgrade():
    # Add column
    op.add_column('videos', sa.Column('new_status', sa.String(50)))

    # Populate with default value
    op.execute("UPDATE videos SET new_status = 'active' WHERE processing_status = 'completed'")

    # Make NOT NULL after populating
    op.alter_column('videos', 'new_status', nullable=False)
```

## Current Schema vs Model Sync

To keep migrations in sync with the current auto-created tables:

### Option 1: Stamp Current Database
If you're starting Alembic on an existing database that was created by SQLAlchemy:

```bash
# Create initial migration from current models
alembic revision --autogenerate -m "Initial schema"

# Mark database as up-to-date without running migration
alembic stamp head
```

### Option 2: Fresh Start
For development environments:

```bash
# Drop all tables
# WARNING: This deletes all data!
python -c "from src.database import Base, Database; db = Database(); Base.metadata.drop_all(db.engine)"

# Create tables via migration
alembic upgrade head
```

## Deployment Workflow

### Development
```bash
# 1. Make model changes in src/database.py
# 2. Generate migration
alembic revision --autogenerate -m "Add indexes to videos table"

# 3. Review migration file
cat alembic/versions/xxxx_add_indexes.py

# 4. Test migration
alembic upgrade head

# 5. Commit migration to git
git add alembic/versions/
git commit -m "Add database migration: indexes"
```

### Production
```bash
# 1. Pull latest code
git pull origin main

# 2. Backup database
pg_dump $DATABASE_URL > backup.sql

# 3. Apply migrations
alembic upgrade head

# 4. Verify
alembic current
```

## Troubleshooting

### Migration Conflicts
If multiple developers create migrations:

```bash
# You may get: "Multiple head revisions are present"
alembic merge heads -m "Merge migrations"

# This creates a merge migration that combines both branches
```

### Reset Migration History
```bash
# Check current stamp
alembic current

# Downgrade to base
alembic downgrade base

# Re-upgrade
alembic upgrade head
```

### Skip Auto-Detection of Certain Tables
In `alembic/env.py`:

```python
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name == "temp_table":
        return False
    return True

context.configure(
    # ...
    include_object=include_object
)
```

## Migration for Current Project

### Step 1: Initialize (if not done)
```bash
alembic init alembic
```

### Step 2: Update alembic/env.py
```python
from src.database import Base
target_metadata = Base.metadata
```

### Step 3: Create Initial Migration
```bash
# If database already has tables (via SQLAlchemy auto-create):
alembic revision --autogenerate -m "Initial schema"
alembic stamp head  # Mark as current without running

# If fresh database:
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### Step 4: For Index Additions (from Phase 3)
```bash
# The indexes we added in Phase 3:
alembic revision --autogenerate -m "Add performance indexes"

# Review the generated migration
# It should include:
# - idx_status_completed_at
# - idx_status_view_count
# - Index on tier_id
# - Indexes on processing_status, completed_at, view_count

alembic upgrade head
```

## Environment Variables

Set these in `.env`:

```bash
# For Alembic configuration
DATABASE_URL=postgresql://user:password@localhost/dbname

# Or override in alembic.ini to use env var:
# In alembic.ini:
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run database migrations
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
  run: |
    pip install alembic
    alembic upgrade head
```

### Railway Deployment
Add to `Procfile` or deployment script:
```bash
# Run migrations before starting app
alembic upgrade head && gunicorn app:app
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Auto Generating Migrations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [SQLAlchemy Migration Patterns](https://alembic.sqlalchemy.org/en/latest/cookbook.html)

---

**Note:** Alembic is configured but migrations are **optional** for this project. The current `_run_migrations()` method in `src/database.py` handles schema updates automatically. Alembic is recommended for production environments where you need:
- Version control of schema changes
- Rollback capability
- Team collaboration on schema changes
- Audit trail of database modifications
