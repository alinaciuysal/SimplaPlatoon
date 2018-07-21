import app.Config as cfg
import json

from json import dumps
from app.changeproviders import init_change_provider
from kafka import KafkaProducer


def main():
    wf = dict(
        change_provider=dict(
            type="kafka_producer",
            kafka_uri=cfg.kafkaHost,
            topic=cfg.kafkaPlatoonConfigTopic,
            serializer="JSON"
        )
    )
    init_change_provider(wf=wf)
    producer = wf["change_provider"]["instance"]

    i = 0
    while i < 5:
        d = {
            'platoon_config': "test"
        }
        json_obj = dumps(d)
        producer.applyChange(json_obj)
        i += 1

def main2():
    producer = KafkaProducer(value_serializer=lambda m: json.dumps(m).encode('ascii'))
    producer.send('platoon-config-2', {'key3': 'value3'})
    producer.send('platoon-config-2', {'key4': 'value4'})

if __name__ == "__main__":
    main2()