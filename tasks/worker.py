# worker.py

import time
import redis as Redis
from settings import REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_BD
# from tasks.queues import my_queue


redis_conn = Redis.StrictRedis(host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT, db=REDIS_BD + 1)


def process_task(task):
    # Procesa la tarea aquí
    print(f"Procesando tarea: {task}")
    # Simula un tiempo de procesamiento
    time.sleep(2)


def listen_for_redis_signals():
    pubsub = redis_conn.pubsub()
    pubsub.subscribe('cola_redis')  # Sustituye 'cola_redis' por el nombre de tu canal en Redis

    for message in pubsub.listen():
        if message['type'] == 'message':
            task = message['data'].decode('utf-8')
            process_task(task)


if __name__ == '__main__':
    print("Esperando señales de Redis...")
    listen_for_redis_signals()
