import logging
from colorama import Fore
from kafka import KafkaProducer
import json

from app.changeproviders.ChangeProvider import ChangeProvider

class KafkaProducerChangeProvider(ChangeProvider):
    """ implements a change provider based on kafka publish """

    def __init__(self, wf, cp):
        # load config
        try:
            self.kafka_uri = cp["kafka_uri"]
            self.topic = cp["topic"]
            self.serializer = cp["serializer"]
            print("> KafkaProducer  | " + self.serializer + " | URI: " + self.kafka_uri + " | Topic: " +
                 self.topic, Fore.CYAN)
        except KeyError:
            print("configuration.kafka_producer was incomplete")
            exit(1)
        # look at the serializer
        if self.serializer == "JSON":
            self.serialize_function = lambda v: json.dumps(v).encode('utf-8')
        else:
            print("serializer not implemented")
            exit(1)
        # try to connect
        try:
            # stop annoying logging
            logging.getLogger("kafka.coordinator.consumer").setLevel("ERROR")
            logging.getLogger("kafka.conn").setLevel("ERROR")
            self.producer = KafkaProducer(bootstrap_servers=self.kafka_uri,
                                          value_serializer=self.serialize_function,
                                          request_timeout_ms=5000)
        except:
            print("connection to kafka failed")
            exit(1)

    def applyChange(self, message):
        """ send out a message through kafka """
        print("Sending out Kafka Message to topic: " + str(self.topic) + " " + str(message))
        self.producer.send(self.topic, message)
