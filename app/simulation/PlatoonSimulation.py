import json
import traci
import traci.constants as tc

from colorama import Fore
from app.logging import info
from app import Config
from app.streaming import KafkaForword, KafkaConnector
from app.simpla import update


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
    def start(cls):
        _useStepListener = 'addStepListener' in dir(traci)
        # print(_useStepListener) # prints out true because version is >= 0.30
        cls._tick = 0
        while cls._tick < 10000:
            update()
            cls._tick += 1
