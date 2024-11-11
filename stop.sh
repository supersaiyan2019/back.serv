#!/bin/bash

# 停止 celery.service
sudo systemctl stop celery.service

# 检查服务状态并自动退出
sudo systemctl status celery.service | tee /dev/null
