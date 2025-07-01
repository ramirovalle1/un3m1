import time
from celery_setting import app


@app.task(name='create-task', bind=True)
def create_task(task_type):
    print(f"INICIA PROCESO ")
    time.sleep(int(task_type) * 10)
    return True