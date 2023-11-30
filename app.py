import json
import connexion
import datetime
from pykafka import KafkaClient
import requests
import uuid
import yaml
import logging
import logging.config
from connexion import NoContent
import time
import os

MAX_EVENTS = 10
EVENT_FILE = 'events.json'
req_queue = []

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

# External Logging Configuration
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

for curr_retry in range(app_config["events"]["max_retry"]):
    try:
        logger.info(f'Attempting to connect to Kafka, retry count: {curr_retry}')
        client = KafkaClient(hosts=f'{app_config["events"]["hostname"]}:{app_config["events"]["port"]}')
        topic = client.topics[str.encode(f'{app_config["events"]["topic"]}')]
        producer = topic.get_sync_producer()
        break
    except Exception as e:
        logger.error(f'Kafka connection failed: {str(e)}')
        time.sleep(app_config["events"]["sleep_time"])
else:
    logger.error(f'Failed to connect to Kafka after {app_config["events"]["max_retry"]} retries')
# def process_events(body):
#     new_event = {
#         "recieved_timestamp": datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
#         "request_data": f'Booking {body["id"]} with a name of {body["name"]}'
#     }
#     req_queue.insert(0, new_event)
#     if len(req_queue) > MAX_EVENTS:
#         req_queue.pop()
#     with open(EVENT_FILE, 'w') as file:
#         json_str = json.dumps(req_queue)
#         file.write(json_str)

def book(body):
    trace_id = str(uuid.uuid4())
    body['trace_id'] = trace_id
    event_name = 'event_book'
    logger.info(f'Recieved event {event_name} with a trace id of {trace_id}')
    msg = { "type": "Event",
           "datetime" : datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
           "payload": body }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f'Returned event {event_name} response (ID:{trace_id}) with status {201}')
    return NoContent, 201

def cancel(body):
    trace_id = str(uuid.uuid4())
    body['trace_id'] = trace_id
    event_name = 'event_cancel'
    logger.info(f'Recieved event {event_name} with a trace id of {trace_id}')
    msg = { "type": "EventCancel",
           "datetime" : datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
           "payload": body }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f'Returned event {event_name} response (ID:{trace_id}) with status {201}')
    return NoContent, 201

def health():
    return 200

# Your functions here
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api(
    "openapi.yml",
    base_path="/receiver",
    strict_validation=True,
    validate_responses=True
)

if __name__ == "__main__":
    print("hello world")
    app.run(port=8080)
    
