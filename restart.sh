#!/bin/bash

# 重启 celery.service
sudo systemctl restart celery.service

# 检查服务状态并自动退出
sudo systemctl status celery.service | tee /dev/null
