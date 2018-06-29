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
        # _useStepListener = 'addStepListener' in dir(traci)
        # print(_useStepListener) # prints out true because version is >= 0.30
        # start listening to all cars that arrived at their target
        # traci.simulation.subscribe((tc.VAR_ARRIVED_VEHICLES_IDS,))

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

            cars = traci.vehicle.getSubscriptionResults()
            for car_id in cars:
                position = cars[car_id][tc.VAR_LANEPOSITION]
                lane = cars[car_id][tc.VAR_LANE_ID]
                print car_id
                print position
                print lane[:-2]

                car_arrival_data = _destinations[car_id]

                print car_arrival_data[0]
                print car_arrival_data[1]

                if lane[:-2] == car_arrival_data[0] and position >= car_arrival_data[1]:
                    print "HEREE"
                    traci.vehicle.remove(car_id)

                print "****************"


        # results = platoon_mgr.get_statistics()
        # print(results)