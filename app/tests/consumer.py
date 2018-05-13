import logging
import app.Config as cfg
from app.dataproviders.__init__ import createInstance

def main():
    dp = dict(
        type="kafka_consumer",
        kafka_uri=cfg.kafkaHost,
        topic=cfg.kafkaPlatoonConfigTopic,
        serializer="JSON"
    )
    createInstance(wf=None, dp=dp)
    consumer = dp["instance"].consumer
    while True:
        for message in consumer:
            # message value and key are raw bytes -- decode if necessary!
            # e.g., for unicode: `message.value.decode('utf-8')`
            print ("%s:%d:%d: key=%s value=%s" % (message.topic, message.partition,
                                                  message.offset, message.key,
                                                  message.value))

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
        level=logging.INFO
    )
    main()