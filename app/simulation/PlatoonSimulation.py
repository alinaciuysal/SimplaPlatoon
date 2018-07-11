import json
import traci
import app.Config as cfg
import traci.constants as tc
from app.streaming import KafkaForword, KafkaConnector
from app.simpla._config import setValues, getValues
from app.entity import SimulationManager

simulationEnded = False


class PlatoonSimulation(object):

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
        # else:
            # NEW: apply platoon configs
            # print("setting config")
            # config = json.load(open('./knobs.json'))
            # setValues(config)
            # print("new globals", str(getValues()))

    @classmethod
    def start(cls, platoon_mgr):
        """ start the simulation """
        print("# Started adding initial cars to the simulation")

        global simulationEnded
        simulationEnded = False
        platoon_mgr.applyCarCounter()
        while not simulationEnded:
            # let the cars process this step via platoonmgr
            traci.simulationStep()

        results = platoon_mgr.get_statistics()
        return results