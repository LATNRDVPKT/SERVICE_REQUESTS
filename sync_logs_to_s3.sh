#!/bin/bash
# sync_logs_to_s3.sh — Automatically backup Gunicorn logs to an S3 bucket

# Replace this with your actual S3 bucket name
S3_BUCKET="service-requests-logs-bucket"
LOG_DIR="/home/ec2-user/logs"

echo "🔄 Syncing logs to s3://${S3_BUCKET}/logs/..."

# Sync the logs (copies only new/modified files)
aws s3 sync ${LOG_DIR} s3://${S3_BUCKET}/logs/

echo "✅ Sync complete."
