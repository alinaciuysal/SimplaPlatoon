from app.changeproviders.KafkaProducerChangeProvider import KafkaProducerChangeProvider


def init_change_provider(wf):
    """ loads the specified change provider into the workflow """
    cp = wf["change_provider"]
    if cp["type"] == "kafka_producer":
        cp["instance"] = KafkaProducerChangeProvider(wf, cp)
    else:
        cp["instance"] = None
        exit(1)