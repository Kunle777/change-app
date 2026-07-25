from celery_app import celery_app

@celery_app.task
def say_hello(name:str):
    print(f"Sending hello to {name}")
    return f"Hello, {name}!"
