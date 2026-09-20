import mysql.connector

c = mysql.connector.connect(user='root', password=input('root password: '), host='127.0.0.1')
cur = c.cursor()
sql = """
CREATE DATABASE service_requests_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sr_user'@'localhost' IDENTIFIED BY 'UPENdra@4G1';
GRANT ALL PRIVILEGES ON service_requests_db.* TO 'sr_user'@'localhost';
FLUSH PRIVILEGES;
"""
for stmt in [s.strip() for s in sql.split(';') if s.strip()]:
    cur.execute(stmt)
c.commit()
cur.close()
c.close()
print('Done.')
