import logging
import app.Config as cfg
import numpy as np
from app.dataproviders.__init__ import createInstance

def main():
    dp = dict(
        type="kafka_consumer",
        kafka_uri=cfg.kafkaHost,
        topic=cfg.kafkaTopicReportedValues,
        serializer="JSON"
    )
    createInstance(wf=None, dp=dp)
    overall_results = dict(
        reportedCO2Emissions=[],
        reportedCOEmissions=[],
        reportedNOxEmissions=[],
        reportedHCEmissions=[],
        reportedPMXEmissions=[],
        reportedFuelConsumptions=[],
        reportedNoiseEmissions=[],
        reportedSpeeds=[]
    )
    i = 0
    # TODO: come up with different logic to fetch data until the end of simulation
    while i < 1149:
        data = dp["instance"].returnData()
        if data is not None:
            for key in data:
                value = float(data[key])
                overall_results[str(key)].append(value)
            i += 1
    return overall_results

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

