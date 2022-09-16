import configparser

from celery import Celery
from celery.schedules import crontab

from periodic_tasks import updater, clean_up


CFG = configparser.ConfigParser()
CFG.read('config.ini')
BROKER_URL = CFG['credentials']['celery_broker_url']

app = Celery('tasks', broker=BROKER_URL)


@app.task
def run_updater():
    updater()

@app.task
def run_clean_up():
    clean_up()

app.conf.beat_schedule = {
    'run-updater-task': {
        'task': 'app.run_updater',
        'schedule': crontab(minute='2,10,17,25,32,40,47,55')
    },
    'run-clean-up-task': {
        'task': 'app.run_clean_up',
        'schedule': crontab(minute='5,20,35,50')
    }
}