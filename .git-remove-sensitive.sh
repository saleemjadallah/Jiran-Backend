#!/bin/bash
# Remove sensitive files from git history

FILES=(
  "DB_SCHEMA_REPORT.md"
  "FINAL_VERIFICATION_REPORT.md"
  "fix_enum_case.py"
  "verify_all_migrations.py"
  "test_user_roles.py"
  "test_db_connection.py"
  "check_enum_values.py"
  "check_schema_mismatch.py"
  "test_registration.py"
)

echo "⚠️  WARNING: This will rewrite git history!"
echo "Files to remove:"
for file in "${FILES[@]}"; do
  echo "  - $file"
done
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

for file in "${FILES[@]}"; do
  echo "Removing $file from git history..."
  git filter-branch --force --index-filter \
    "git rm --cached --ignore-unmatch $file" \
    --prune-empty --tag-name-filter cat -- --all
done

echo ""
echo "✅ Files removed from history"
echo "⚠️  You must force push: git push origin --force --all"
