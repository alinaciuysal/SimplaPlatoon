import logging
import app.Config as cfg
from app.dataproviders import createInstance

def main():
    dp = dict(
        type="kafka_consumer",
        kafka_uri=cfg.kafkaHost,
        topic=cfg.kafkaTopicData,
        serializer="JSON"
    )
    createInstance(wf=None, dp=dp)


def find_average(res):
    for key in res:
        tuple = res[key]
        d = float(sum(tuple)) / len(tuple)
        res[key] = d
    print(res)

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s.%(msecs)s:%(name)s:%(thread)d:%(levelname)s:%(process)d:%(message)s',
        level=logging.INFO
    )
    res = main()
    find_average(res)

