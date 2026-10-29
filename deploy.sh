#!/bin/bash
# deploy.sh — script to update the app on EC2

echo "🚀 Starting deployment..."

# Navigate to app directory
cd /home/ec2-user/app

# Pull latest code from GitHub
echo "📥 Pulling latest code..."
git pull origin main

# Activate virtual environment
source .venv/bin/activate

# Install any new requirements
echo "📦 Checking dependencies..."
pip install -r requirements.txt

# Run any new database migrations
echo "🗄️ Running migrations..."
python manage.py migrate

# Collect new static files
echo "🎨 Updating static files..."
python manage.py collectstatic --noinput

# Restart Gunicorn service
echo "🔄 Restarting Gunicorn server..."
sudo systemctl restart gunicorn

echo "✅ Deployment complete! Your app is live."
