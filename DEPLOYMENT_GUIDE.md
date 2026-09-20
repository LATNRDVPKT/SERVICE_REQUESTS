# End-to-End Deployment Guide (AWS EC2)
**Project:** SERVICE_REQUESTS Django App  
**OS:** Amazon Linux 2023  
**Web Server:** Gunicorn (with WhiteNoise for static files)  
**Database:** MySQL 8.0  

---

## 1. AWS EC2 Setup
1. Launch an EC2 Instance:
   - **AMI:** Amazon Linux 2023
   - **Storage:** 20 GB gp3 (ext4)
   - **Security Group:** Open Port 22 (SSH) for your IP, and Port 8000 (Custom TCP) for Anywhere (0.0.0.0/0).
2. Create and attach an **Elastic IP** to the instance so the IP address never changes.
3. SSH into the instance using your `.pem` key:
   ```bash
   ssh -i "path/to/key.pem" ec2-user@<ELASTIC_IP>
   ```

---

## 2. Install System Dependencies & MySQL
Update the system and install Python 3.11, Git, and MySQL 8.0.

```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip python3.11-devel git gcc gcc-c++ make mysql-devel

# Install MySQL 8.0
sudo dnf install -y https://dev.mysql.com/get/mysql80-community-release-el9-4.noarch.rpm
sudo dnf install -y mysql-community-server mysql-community-devel

# Start MySQL
sudo systemctl start mysqld
sudo systemctl enable mysqld
```

---

## 3. Configure MySQL Database
1. Get the temporary root password:
   ```bash
   sudo grep 'temporary password' /var/log/mysqld.log
   ```
2. Secure the installation and set a new root password (e.g., `UPENdra@4G1`):
   ```bash
   sudo mysql_secure_installation
   ```
3. Create the application database:
   ```bash
   mysql -u root -p
   # Inside MySQL shell:
   CREATE DATABASE service_requests CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   FLUSH PRIVILEGES;
   EXIT;
   ```

---

## 4. Clone Repository & Setup Virtual Environment
```bash
cd /home/ec2-user
git clone https://github.com/LATNRDVPKT/SERVICE_REQUESTS.git app
cd app

# Create and activate virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies (including gunicorn and whitenoise)
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 5. Configure Environment Variables
Create the `.env` file in the project root (`/home/ec2-user/app/.env`):

```bash
nano .env
```
Paste the following (generate a unique `DJANGO_SECRET_KEY`):
```bash
DJANGO_SECRET_KEY="your-secret-key-here"
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<YOUR_ELASTIC_IP>,localhost,127.0.0.1

DB_NAME=service_requests
DB_USER=root
DB_PASSWORD=UPENdra@4G1
DB_HOST=127.0.0.1
DB_PORT=3306

# Add your Email and API configurations here as well...
```
Secure the file:
```bash
chmod 600 .env
```

---

## 6. Run Migrations & Collect Static Files
```bash
python manage.py migrate
python manage.py seed_users   # Note the generated passwords printed to the terminal!
python manage.py collectstatic --noinput

# Create log directory for Gunicorn
mkdir -p /home/ec2-user/logs
```

---

## 7. Setup Gunicorn as a systemd Service
Create the service file so the app runs in the background and starts on boot.

```bash
sudo nano /etc/systemd/system/gunicorn.service
```
Add the following configuration:
```ini
[Unit]
Description=Gunicorn — SERVICE_REQUESTS Django
After=network.target mysqld.service

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/app
EnvironmentFile=/home/ec2-user/app/.env
ExecStart=/home/ec2-user/app/.venv/bin/gunicorn \
    --config /home/ec2-user/app/gunicorn.conf.py \
    service_requests.wsgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
```

---

## 8. Automating Code Updates (deploy.sh)
To deploy new code from GitHub in the future, just run the deploy script:
```bash
bash /home/ec2-user/app/deploy.sh
```

---

## 9. Automating Log Backups to AWS S3
1. **AWS Console:** Create an S3 Bucket (e.g., `danlaw-service-requests-logs`).
2. **AWS Console:** Create an IAM Role with `AmazonS3FullAccess` and attach it to your EC2 instance.
3. **EC2 Terminal:** Schedule the sync script to run daily at midnight.
   ```bash
   sudo dnf install -y cronie
   sudo systemctl enable crond
   sudo systemctl start crond
   crontab -e
   ```
   Add this line:
   ```bash
   0 0 * * * bash /home/ec2-user/app/sync_logs_to_s3.sh
   ```
