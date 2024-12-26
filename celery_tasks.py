from celery import Celery
import json
import mysql.connector
import requests
import logging
from datetime import datetime, timedelta
from celery.schedules import crontab
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# celery -A celery_tasks worker --loglevel=info

# 创建Celery应用
app = Celery('tasks', 
             broker=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/{os.getenv('REDIS_DB_BROKER', 0)}", 
             backend=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/{os.getenv('REDIS_DB_BACKEND', 1)}")

# 数据库连接函数
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

# 更新任务状态的函数
def update_task_status(ticket_id, status, result_info=None, error_info=None, serv_name=None, serv_switch_info=None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_query = """
        UPDATE sride_queue 
        SET status = %s, 
            result_info = %s, 
            error_info = %s, 
            started_at = CASE WHEN %s = 'In Progress' THEN NOW() ELSE started_at END,
            completed_at = CASE WHEN %s IN ('Completed', 'Cancelled', 'System Error') THEN NOW() ELSE completed_at END,
            serv_name = CASE WHEN %s IS NOT NULL THEN %s ELSE serv_name END,
            serv_switch_info = CASE WHEN %s IS NOT NULL THEN %s ELSE serv_switch_info END
        WHERE ticket_id = %s
        """
        
        cursor.execute(update_query, (status, 
                                      result_info, 
                                      error_info, 
                                      status, 
                                      status, 
                                      serv_name, 
                                      serv_name, 
                                      serv_switch_info, 
                                      serv_switch_info, 
                                      ticket_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        logger.info(f"成功更新任务状态: ticket_id={ticket_id}, status={status}")
    except Exception as e:
        logger.error(f"更新任务状态失败: ticket_id={ticket_id}, status={status}, error={str(e)}")

def check_and_update_stuck_tasks():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取所有 In Progress 的任务
        select_query = """
        SELECT ticket_id, serv_name, started_at
        FROM sride_queue
        WHERE status = 'In Progress'
        """
        cursor.execute(select_query)
        in_progress_tasks = cursor.fetchall()

        for task in in_progress_tasks:
            ticket_id, serv_name, started_at = task
            # 检查任务是否超时
            if datetime.now() - started_at > timedelta(seconds=300):
                # 检查服务器状态
                server_status = get_server_status(serv_name)
                if server_status == 'offline':
                    # 如果服务器离线，将任务重新排队
                    update_query = """
                    UPDATE sride_queue
                    SET status = 'Queueing', error_info = '服务器离线，任务重新排队'
                    WHERE ticket_id = %s
                    """
                    cursor.execute(update_query, (ticket_id,))
                else:
                    # 如果服务器在线，标记为系统错误
                    update_query = """
                    UPDATE sride_queue
                    SET status = 'System Error', error_info = '任务执行超时'
                    WHERE ticket_id = %s
                    """
                    cursor.execute(update_query, (ticket_id,))

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("已检查并更新卡住的任务")
    except Exception as e:
        logger.error(f"检查卡住任务时出错: {str(e)}")

# 设置定时任务
app.conf.beat_schedule = {
    'check-stuck-tasks-every-5-minutes': {
        'task': 'celery_tasks.check_and_update_stuck_tasks',
        'schedule': crontab(minute='*/5'),
    },
}

def get_server_status(serv_name):
    ai_server_status = requests.get(f"{os.getenv('AI_SERVER_URL')}{os.getenv('AI_SERVER_STATUS_ENDPOINT')}").json()
    for server in ai_server_status:
        if server['serv_name'] == serv_name:
            return server['serv_status']
    return 'unknown'

def get_available_server(exclude=[]):
    ai_server_status = requests.get(f"{os.getenv('AI_SERVER_URL')}{os.getenv('AI_SERVER_STATUS_ENDPOINT')}").json()
    available_servers = [server['serv_name'] for server in ai_server_status if server['serv_status'] == 'online' and server['serv_name'] not in exclude]
    
    return available_servers[0] if available_servers else None

def is_server_busy(serv_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
    SELECT COUNT(*) FROM sride_queue
    WHERE serv_name = %s AND status IN ('In Progress', 'Queueing')
    """
    cursor.execute(query, (serv_name,))
    count = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    return count > int(os.getenv('SERVER_BUSY_THRESHOLD', 10))

# 使用环境变量
AI_SERVER_URL = os.getenv('AI_SERVER_URL')

def check_and_switch_server(ticket_id, original_serv_name):
    """
    检查服务器状态并在必要时切换服务器
    
    :param ticket_id: 任务的ticket_id
    :param original_serv_name: 原始指定的服务器名称
    :return: 元组 (server_name, status)
             server_name: 最终选定的服务器名称
             status: 'ready' 表示可以执行任务，'requeued' 表示任务需要重新排队
    """
    try:
        # 检查指定的服务器是否在线
        server_status = get_server_status(original_serv_name)
        
        if server_status == 'online':
            # 如果服务器在线，直接返回
            logger.info(f"服务器 {original_serv_name} 在线，可以执行任务: ticket_id={ticket_id}")
            return original_serv_name, 'ready'
        else:
            # 如果指定的服务器离线，尝试切换到其他可用服务器
            logger.info(f"服务器 {original_serv_name} 离线，尝试切换服务器: ticket_id={ticket_id}")
            new_serv_name = get_available_server(exclude=[original_serv_name])
            
            if new_serv_name:
                # 如果找到了新的可用服务器
                if not is_server_busy(new_serv_name):
                    # 如果新服务器不忙，更新任务信息
                    serv_switch_info = {
                        "switch_time": datetime.now().isoformat(),
                        "from_serv": original_serv_name,
                        "to_serv": new_serv_name,
                        "reason": "原服务器离线，切换到新服务器"
                    }
                    update_task_status(ticket_id, 'In Progress', serv_name=new_serv_name, serv_switch_info=json.dumps(serv_switch_info))
                    logger.info(f"任务切换到新服务器: ticket_id={ticket_id}, new_serv_name={new_serv_name}")
                    return new_serv_name, 'ready'
                else:
                    # 如果新服务器忙，将任务重新排队
                    serv_switch_info = {
                        "switch_time": datetime.now().isoformat(),
                        "from_serv": original_serv_name,
                        "to_serv": new_serv_name,
                        "reason": "原服务器离线，新服务器繁忙，任务重新排队"
                    }
                    update_task_status(ticket_id, 'Queueing', serv_name=new_serv_name, serv_switch_info=json.dumps(serv_switch_info))
                    logger.info(f"新服务器繁忙，任务重新排队: ticket_id={ticket_id}, new_serv_name={new_serv_name}")
                    return new_serv_name, 'requeued'
            else:
                # 如果没有可用的服务器，将任务标记为错误
                error_info = "没有可用的服务器"
                update_task_status(ticket_id, 'System Error', error_info=error_info)
                logger.error(f"没有可用的服务器，任务失败: ticket_id={ticket_id}")
                raise Exception(error_info)
    except Exception as e:
        logger.error(f"检查和切换服务器时出错: ticket_id={ticket_id}, 错误: {str(e)}")
        raise

# 然后，我们可以在每个任务中使用这个函数：

@app.task(name='Image Creation', bind=True)
def image_creation(self, task_params, user_id, serv_name):
    ticket_id = self.request.id
    logger.info(f"开始执行Image Creation任务,ticket_id: {ticket_id}, serv_name: {serv_name}")
    
    try:
        serv_name, status = check_and_switch_server(ticket_id, serv_name)
        if status == 'requeued':
            return {"status": "requeued"}
        
        # 更新任务状态为进行中
        update_task_status(ticket_id, 'In Progress')
        logger.info(f"任务状态更新为In Progress: ticket_id={ticket_id}")
        
        # 准备请求参数
        task_params['user_id'] = user_id
        task_params['serv_name'] = serv_name
        
        # 调用AI服务器API
        response = requests.post(f"{AI_SERVER_URL}/image_creation", json=task_params, timeout=300)
        response.raise_for_status()
        
        # 解析返回的文件列表
        result_info = {"image_urls": response.json()}
        update_task_status(ticket_id, 'Completed', result_info=json.dumps(result_info))
        logger.info(f"Image Creation任务完成: ticket_id={ticket_id}")
        return result_info
    except requests.Timeout:
        error_info = "AI服务器请求超时"
        update_task_status(ticket_id, 'System Error', error_info=error_info)
        logger.error(f"Image Creation任务超时: ticket_id={ticket_id}")
        return {"error": error_info}
    except Exception as e:
        error_info = str(e)
        update_task_status(ticket_id, 'System Error', error_info=error_info)
        logger.error(f"Image Creation任务处理过程中出错: ticket_id={ticket_id}, 错误: {error_info}")
        return {"error": error_info}

@app.task(name='Image Upscale', bind=True)
def image_upscale(self, task_params, user_id, serv_name):
    ticket_id = self.request.id
    logger.info(f"开始执行Image Upscale任务,ticket_id: {ticket_id}, serv_name: {serv_name}")
    
    try:
        serv_name, status = check_and_switch_server(ticket_id, serv_name)
        if status == 'requeued':
            return {"status": "requeued"}
        
        # 更新任务状态为进行中
        update_task_status(ticket_id, 'In Progress')
        logger.info(f"任务状态更新为In Progress: ticket_id={ticket_id}")
        
        # 准备请求参数
        task_params['user_id'] = user_id
        task_params['serv_name'] = serv_name

        # 调用AI服务器API
        response = requests.post(f"{AI_SERVER_URL}/image_upscale", json=task_params, timeout=300)
        response.raise_for_status()

        # 解析返回的文件列表
        result_info = {"image_urls": response.json()}
        update_task_status(ticket_id, 'Completed', result_info=json.dumps(result_info))
        logger.info(f"Image Upscale任务完成: ticket_id={ticket_id}")
        return result_info
    except requests.Timeout:
        error_info = "AI服务器请求超时"
        update_task_status(ticket_id, 'System Error', error_info=error_info)
        logger.error(f"Image Upscale任务超时: ticket_id={ticket_id}")
        return {"error": error_info}
    except Exception as e:
        error_info = str(e)
        update_task_status(ticket_id, 'System Error', error_info=error_info)
        logger.error(f"Image Upscale任务处理过程中出错: ticket_id={ticket_id}, 错误: {error_info}")
        return {"error": error_info}

@app.task(name='Face Swap', bind=True)
def face_swap(self, task_params, user_id, serv_name):
    ticket_id = self.request.id
    logger.info(f"开始执行Face Swap任务,ticket_id: {ticket_id}, serv_name: {serv_name}")
    
    try:
        serv_name, status = check_and_switch_server(ticket_id, serv_name)
        if status == 'requeued':
            return {"status": "requeued"}
        
        # 更新任务状态为进行中
        update_task_status(ticket_id, 'In Progress')
        logger.info(f"任务状态更新为In Progress: ticket_id={ticket_id}")

        # 准备请求参数
        task_params['user_id'] = user_id
        task_params['serv_name'] = serv_name

        # 调用AI服务器API
        response = requests.post(f"{AI_SERVER_URL}/face_swap", json=task_params, timeout=300)
        response.raise_for_status()

        # 解析返回的文件列表
        result_info = {"image_urls": response.json()}
        update_task_status(ticket_id, 'Completed', result_info=json.dumps(result_info))
        logger.info(f"Face Swap任务完成: ticket_id={ticket_id}")
        return result_info
    except requests.Timeout:
        error_info = "AI服务器请求超时"
        update_task_status(ticket_id, 'System Error', error_info=error_info)
        logger.error(f"Face Swap任务超时: ticket_id={ticket_id}")
        return {"error": error_info}
    except Exception as e:
        error_info = str(e)
        update_task_status(ticket_id, 'System Error', error_info=error_info)
        logger.error(f"Face Swap任务处理过程中出错: ticket_id={ticket_id}, 错误: {error_info}")
        return {"error": error_info}

@app.task(name='Video Creation', bind=True)
def video_creation(self, task_params, serv_name):
    ticket_id = self.request.id
    logger.info(f"开始执行Video Creation任务,ticket_id: {ticket_id}, serv_name: {serv_name}")
    
    try:
        serv_name, status = check_and_switch_server(ticket_id, serv_name)
        if status == 'requeued':
            return {"status": "requeued"}
        
        # 更新任务状态为进行中
        update_task_status(ticket_id, 'In Progress')
        logger.info(f"任务状态更新为In Progress: ticket_id={ticket_id}")
        
        # 准备请求参数
        task_params['serv_name'] = serv_name
        
        # 这里是Video Creation任务执行的具体逻辑
        # ...
        
        result_info = {"video_url": "url"}  # 这里需要替换为实际的结果
        update_task_status(ticket_id, 'Completed', result_info=json.dumps(result_info))
        logger.info(f"Video Creation任务完成: ticket_id={ticket_id}")
        return result_info
    except Exception as e:
        error_info = str(e)
        update_task_status(ticket_id, 'System Error', error_info=error_info)
        logger.error(f"Video Creation任务处理过程中出错: ticket_id={ticket_id}, 错误: {error_info}")
        return {"error": error_info}

@app.task
def process_task_queue():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 获取所有排队中的任务
    select_query = """
    SELECT ticket_id, task_type, task_params, serv_name
    FROM sride_queue
    WHERE status = 'Queueing'
    ORDER BY created_at ASC
    """
    cursor.execute(select_query)
    queued_tasks = cursor.fetchall()

    for task in queued_tasks:
        # 检查服务器是否可用且不繁忙
        if not is_server_busy(task['serv_name']):
            # 重新提交任务
            app.send_task(task['task_type'], args=[json.loads(task['task_params']), task['serv_name']])
            logger.info(f"重新提交任务: ticket_id={task['ticket_id']}")

    cursor.close()
    conn.close()

# 设置定时任务来处理队列
app.conf.beat_schedule['process-task-queue-every-minute'] = {
    'task': 'celery_tasks.process_task_queue',
    'schedule': crontab(minute='*'),
}

# 配置Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=int(os.getenv('TASK_TIMEOUT_SECONDS', 300)),
    worker_max_tasks_per_child=int(os.getenv('WORKER_MAX_TASKS', 100)),
    broker_connection_retry_on_startup=True
)
