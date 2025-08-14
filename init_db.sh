#!/usr/bin/env bash
set -euo pipefail

# KBAI API Database Initialization Script
echo "Initializing KBAI API database..."

# Get script directory and set paths relative to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Configuration
DB_PATH="$PROJECT_ROOT/app/kbai_api.db"
SCHEMA_PATH="$PROJECT_ROOT/app/schema.sql"

# Create app directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/app"

# Remove existing database if it exists
if [ -f "$DB_PATH" ]; then
    echo "Removing existing database: $DB_PATH"
    rm -f "$DB_PATH"
    rm -f "${DB_PATH}-shm"
    rm -f "${DB_PATH}-wal"
fi

# Check if schema file exists
if [ ! -f "$SCHEMA_PATH" ]; then
    echo "Error: Schema file not found at $SCHEMA_PATH"
    exit 1
fi

# Initialize database with schema
echo "Creating database: $DB_PATH"
sqlite3 "$DB_PATH" < "$SCHEMA_PATH"

# Verify database creation
if [ -f "$DB_PATH" ]; then
    echo "✅ Database initialized successfully: $DB_PATH"
    
    # Show table info
    echo ""
    echo "Database tables:"
    sqlite3 "$DB_PATH" ".tables"
    
    echo ""
    echo "Sessions table schema:"
    sqlite3 "$DB_PATH" ".schema sessions"
    
    echo ""
    echo "Traces table schema:"
    sqlite3 "$DB_PATH" ".schema traces"
else
    echo "❌ Failed to create database"
    exit 1
fi

echo ""
echo "🚀 Database initialization complete!"
echo "You can now run the API with: ./run_api.sh"