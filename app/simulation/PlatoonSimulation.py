import json
import traci
import app.Config as cfg
import traci.constants as tc
from app.streaming import KafkaForword, KafkaConnector
from app.simpla._config import setValues, getValues
from app.entity import CarRegistry
from app.simpla._platoonmanager import _destinations


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
        """ start the simulation """
        print("# Started adding initial cars to the simulation")
        # apply the configuration from the json file
        cls.applyFileConfig()
        platoon_mgr.applyCarCounter()

        while 1:
            cls.tick += 1
            # if (cls.tick % 10) == 0:
            #     if cfg.kafkaUpdates is False:
            #         cls.applyFileConfig()
            #     else:
            #         cls.applyKafkaConfig()
            #
            # # Check for removed cars and re-add them into the system
            # for removedCarId in traci.simulation.getSubscriptionResults()[122]:
            #     CarRegistry.findById(removedCarId).setArrived(cls.tick)

            # let the cars process this step via platoonmgr
            traci.simulationStep()


        # results = platoon_mgr.get_statistics()
        # print(results)