# gunicorn.conf.py — production config for AWS EC2 (Amazon Linux 2023)
bind    = "0.0.0.0:8000"
workers = 2          # 2 workers is enough for 15 users on low-RAM instances
timeout = 120
accesslog = "/home/ec2-user/logs/gunicorn-access.log"
errorlog  = "/home/ec2-user/logs/gunicorn-error.log"
loglevel  = "info"
