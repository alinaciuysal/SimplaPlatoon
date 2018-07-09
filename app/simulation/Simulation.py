import json
import traci
from app.streaming import KafkaForword, KafkaConnector

# the current situation of the simulation
simulationEnded = False


class Simulation(object):

    @classmethod
    def applyFileConfig(cls):
        """ reads configs from a json and applies it at realtime to the simulation """
        try:
            config = json.load(open('./knobs.json'))
            if config['hard_shoulder'] == 0:
                cls.hard_shoulder_on = False
            else:
                cls.hard_shoulder_on = True
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

    @classmethod
    def start(cls, simulationManager):
        """ start the simulation """
        print("# Started adding initial cars to regular simulation")

        global simulationEnded
        simulationEnded = False

        simulationManager.applyCarCounter()
        while not simulationEnded:
            # let the cars process this step via simulationManager
            traci.simulationStep()

        results = simulationManager.get_statistics()
        return results