# encoding: utf-8
import json
from flask import Flask, request, jsonify
from celery.result import AsyncResult
from celery_tasks import app as celery_app, process_task_queue
import mysql.connector
import requests
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format=os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
)
logger = logging.getLogger(__name__)

flask_app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        port=int(os.getenv('DB_PORT')),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

def get_server_load():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
    SELECT serv_name, 
           SUM(CASE WHEN status IN ('Queueing', 'In Progress') THEN 1 ELSE 0 END) as active_tasks,
           SUM(CASE WHEN status = 'In Progress' AND started_at < %s THEN 1 ELSE 0 END) as stuck_tasks
    FROM sride_queue
    GROUP BY serv_name
    """
    
    timeout_threshold = datetime.now() - timedelta(seconds=int(os.getenv('TASK_TIMEOUT_SECONDS', 300)))
    cursor.execute(query, (timeout_threshold,))
    server_loads = {row['serv_name']: row for row in cursor.fetchall()}
    
    cursor.close()
    conn.close()
    
    return server_loads

def get_available_server():
    server_loads = get_server_load()
    ai_server_status = requests.get(f"{os.getenv('AI_SERVER_URL')}{os.getenv('AI_SERVER_STATUS_ENDPOINT')}").json()
    
    available_servers = [server['serv_name'] for server in ai_server_status if server['serv_status'] == 'online']
    
    if not available_servers:
        raise Exception("没有可用的AI服务器")
    
    min_load = float('inf')
    selected_server = None
    
    for server in available_servers:
        load = server_loads.get(server, {'active_tasks': 0, 'stuck_tasks': 0})
        current_load = load['active_tasks'] - load['stuck_tasks']
        if current_load < min_load:
            min_load = current_load
            selected_server = server
    
    return selected_server

@flask_app.route('/submit_task', methods=['POST'])
def submit_task():
    try:
        data = request.json
        task_type = data['task_type']
        task_params = data['task_params']
        user_id = data['user_id']

        # 获取可用的服务器
        selected_server = get_available_server()

        # 将任务发送到Celery，分别传递task_params和serv_name
        task = celery_app.send_task(task_type, args=[task_params, user_id, selected_server])

        conn = get_db_connection()
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO sride_queue (ticket_id, user_id, serv_name, task_type, task_params, status)
        VALUES (%s, %s, %s, %s, %s, 'Queueing')
        """
        cursor.execute(insert_query, (task.id, user_id, selected_server, task_type, json.dumps(task_params)))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({"ticket_id": task.id, "serv_name": selected_server, "status": "Queueing"}), 202
    except Exception as e:
        logger.error(f"提交任务失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@flask_app.route('/query_task/<ticket_id>', methods=['GET'])
def query_task(ticket_id):
    task_result = AsyncResult(ticket_id, app=celery_app)

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    select_query = "SELECT * FROM sride_queue WHERE ticket_id = %s"
    cursor.execute(select_query, (ticket_id,))
    task_info = cursor.fetchone()

    if not task_info:
        return jsonify({"error": "任务不存在"}), 404

    response = {
        "status": task_info['status'],
        "result_info": json.loads(task_info['result_info']) if task_info['result_info'] else None
    }

    if task_info['status'] == 'Queueing':
        # 获取队列中排在前面的任务数量
        count_query = "SELECT COUNT(*) as count FROM sride_queue WHERE status = 'Queueing' AND created_at < %s"
        cursor.execute(count_query, (task_info['created_at'],))
        queue_position = cursor.fetchone()['count']
        response["queue_position"] = queue_position

    cursor.close()
    conn.close()

    return jsonify(response)

@flask_app.route('/cancel_task/<ticket_id>', methods=['POST'])
def cancel_task(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    select_query = "SELECT status FROM sride_queue WHERE ticket_id = %s"
    cursor.execute(select_query, (ticket_id,))
    task_status = cursor.fetchone()

    if not task_status:
        return jsonify({"error": "任务不存在"}), 404

    if task_status[0] != 'Queueing':
        return jsonify({"error": "只能取消排队中的任务"}), 400

    update_query = "UPDATE sride_queue SET status = 'Cancelled' WHERE ticket_id = %s"
    cursor.execute(update_query, (ticket_id,))
    conn.commit()

    celery_app.control.revoke(ticket_id, terminate=True)

    cursor.close()
    conn.close()

    return jsonify({"message": "任务已取消"})

@flask_app.route('/process_queue', methods=['POST'])
def trigger_process_queue():
    process_task_queue.delay()
    return jsonify({"message": "队列处理已触发"}), 202

DIFY_URL = os.getenv('DIFY_URL')
TRANSLATOR_API_KEY = os.getenv('TRANSLATOR_API_KEY')
PROMPTOR_API_KEY = os.getenv('PROMPTOR_API_KEY')

def call_dify_service(prompt_text, api_key):
    request_body = {
        "inputs": {
            "origin_prompt": prompt_text
        },
        "response_mode": "blocking",
        "user": "Anonymous"
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(f"{DIFY_URL}/workflows/run", json=request_body, headers=headers)

    if response.status_code == 200:
        processed_text = response.json().get('data', {}).get('outputs', {})
        polish_prompt = processed_text.get('polish_prompt')
        return polish_prompt
    else:
        raise Exception(f"AI服务请求失败，状态码：{response.status_code}，错误信息：{response.text}")

@flask_app.route('/translator', methods=['POST'])
def translator_service():
    try:
        data = request.json
        prompt_text = data.get('prompt_text')
        if not prompt_text:
            return jsonify({"error": "缺少prompt_text参数"}), 400
        
        result = call_dify_service(prompt_text, TRANSLATOR_API_KEY)
        return jsonify({"result": result}), 200
    except Exception as e:
        logger.error(f"翻译服务失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@flask_app.route('/promptor', methods=['POST'])
def promptor_service():
    try:
        data = request.json
        prompt_text = data.get('prompt_text')
        if not prompt_text:
            return jsonify({"error": "缺少prompt_text参数"}), 400
        
        result = call_dify_service(prompt_text, PROMPTOR_API_KEY)
        return jsonify({"result": result}), 200
    except Exception as e:
        logger.error(f"提示词服务失败: {str(e)}")
        return jsonify({"error": str(e)}), 500

@flask_app.route('/facebbox', methods=['POST'])
def face_bbox():
    if request.method == 'POST':
        try:
            image_data = request.files['image']
            response = requests.post(
                f"{os.getenv('AI_SERVER_URL')}{os.getenv('FACE_BBOX_ENDPOINT')}",
                files={'image': image_data}
            )
            return jsonify(response.json())
        except Exception as e:
            logger.error(f"Error in face_bbox: {str(e)}")
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Method not allowed'}), 405

if __name__ == '__main__':
    flask_app.run(
        debug=os.getenv('FLASK_DEBUG', '0') == '1',
        port=int(os.getenv('FLASK_PORT', 4093)),
        host=os.getenv('FLASK_HOST', '0.0.0.0')
    )