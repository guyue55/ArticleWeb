#!/bin/bash

# 检查数据库文件是否存在
if [ -f "/app/db.sqlite3" ]; then
    echo "Database file exists, skipping migrations..."
else
    echo "Database file not found, running migrations..."
    python manage.py migrate --noinput
fi

# 启动Gunicorn
echo "Starting Gunicorn..."
exec gunicorn --config gunicorn.conf.py article_web.wsgi:application