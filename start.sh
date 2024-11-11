#!/bin/bash

# 启动 celery.service
sudo systemctl start celery.service

# 检查服务状态并自动退出
sudo systemctl status celery.service | tee /dev/null
