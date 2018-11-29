from __future__ import absolute_import

from celery import Celery

app = Celery('proj',
             broker='amqp://',
             backend='amqp://',
             include=['proj.tasks', 'proj.analyze', 'proj.updated_analysis', 'proj.receive_tweets'])

# Optional configuration, see the application user guide.
app.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600,
    CELERY_IGNORE_RESULT=False,
    BROKER_HOST="127.0.0.1",  # IP address of the server running RabbitMQ and Celery
    BROKER_PORT=5672,
    BROKER_URL='amqp://',
    CELERY_RESULT_BACKEND="amqp"
)

if __name__ == '__main__':
    app.start()
