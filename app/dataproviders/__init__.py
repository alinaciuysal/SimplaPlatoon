from app.dataproviders.KafkaConsumerDataProvider import KafkaConsumerDataProvider


def createInstance(wf, dp):
    """ creates a single instance of a data provider and stores the instance as reference in the definition """
    if dp["type"] == "kafka_consumer":
        dp["instance"] = KafkaConsumerDataProvider(wf, dp)
    else:
        dp["instance"] = None