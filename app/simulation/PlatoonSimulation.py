import json
import traci
import app.Config as cfg

from app.streaming import KafkaForword, KafkaConnector
from app.simpla._config import setValues, getValues

class PlatoonSimulation(object):

    # the current tick of the simulation
    tick = 0

    @classmethod
    def applyFileConfig(cls):
        """ reads configs from a json and applies it at realtime to the simulation """
        try:
            config = json.load(open('./knobs.json'))
            if config['hard_shoulder'] == 0:
                cls.hard_shoulder_on = False
            else:
                cls.hard_shoulder_on = True

            # NEW: apply platoon configs
            # print("setting config")
            # setValues(config)
            # print("new globals", str(getValues()))
        except:
            pass

    @classmethod
    def applyKafkaConfig(cls):
        """ Gets a new configuration value from Kafka"""
        new_conf = KafkaConnector.checkForNewConfiguration()
        if new_conf is not None:
            if "hard_shoulder" in new_conf:
                if new_conf['hard_shoulder'] == 0:
                    cls.hard_shoulder_on = False
                else:
                    cls.hard_shoulder_on = True
        # TODO: to be removed, just for easy testing
        # else:
            # NEW: apply platoon configs
            # print("setting config")
            # config = json.load(open('./knobs.json'))
            # setValues(config)
            # print("new globals", str(getValues()))

    @classmethod
    def start(cls, platoon_mgr):
        # _useStepListener = 'addStepListener' in dir(traci)
        # print(_useStepListener) # prints out true because version is >= 0.30
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            cls.tick += 1
            if (cls.tick % 10) == 0:
                if cfg.kafkaUpdates is False:
                    cls.applyFileConfig()
                else:
                    cls.applyKafkaConfig()

                # print status update if we are not running in parallel mode
                # print(str(cfg.processID) + " -> Step:" + str(cls.tick) + " # Driving cars: " + str(
                #     traci.vehicle.getIDCount()) + "/"
                #     + " # totalFuelConsumptionAverage: " + str(cls.totalFuelConsumptionAverage)
                #     + " # totalSpeedAverage: " + str(cls.totalSpeedAverage)
                #     + " # totalCO2EmissionAverage: " + str(cls.totalCO2EmissionAverage)
                #     + " # totalCOEmissionAverage: " + str(cls.totalCOEmissionAverage) )
        results = platoon_mgr.get_statistics()
        print(results)