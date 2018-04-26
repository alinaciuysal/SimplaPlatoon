import json
import traci
import traci.constants as tc

from colorama import Fore
from app.logging import info
from app import Config
from app.streaming import KafkaForword, KafkaConnector

class Simulation(object):

    # the current tick of the simulation
    tick = 0
    # whether the hard should should be open
    hard_shoulder_on = False

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

        # start listening to all loop detectors
        traci.inductionloop.subscribe("loop0500_1", [tc.LAST_STEP_VEHICLE_NUMBER, tc.LAST_STEP_OCCUPANCY])
        traci.inductionloop.subscribe("loop0500_2", [tc.LAST_STEP_VEHICLE_NUMBER, tc.LAST_STEP_OCCUPANCY])
        traci.inductionloop.subscribe("loop0500_3", [tc.LAST_STEP_VEHICLE_NUMBER, tc.LAST_STEP_OCCUPANCY])
        traci.inductionloop.subscribe("loop01500_1", [tc.LAST_STEP_VEHICLE_NUMBER, tc.LAST_STEP_OCCUPANCY])
        traci.inductionloop.subscribe("loop01500_2", [tc.LAST_STEP_VEHICLE_NUMBER, tc.LAST_STEP_OCCUPANCY])
        traci.inductionloop.subscribe("loop01500_3", [tc.LAST_STEP_VEHICLE_NUMBER, tc.LAST_STEP_OCCUPANCY])

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()

            KafkaForword.publish({"tick" : 1}, Config.kafkaTopicTicks)

            # attach listener to each car in the simulation
            for veh_id in traci.simulation.getDepartedIDList():
                traci.vehicle.subscribe(veh_id, [tc.VAR_LANE_ID, tc.VAR_LANEPOSITION, tc.VAR_SPEED])

            cars = traci.vehicle.getSubscriptionResults()
            for car in cars:
                lane = cars[car][tc.VAR_LANE_ID]
                if lane == "Shoulder01_1" or lane == "Shoulder01_2" or lane == "Shoulder01_3":
                    position = cars[car][tc.VAR_LANEPOSITION]
                    if 500 < position < 1500:
                        KafkaForword.publish({"speed": cars[car][tc.VAR_SPEED]}, Config.kafkaTopicCarSpeeds)

            loopDetectorOccupancies = traci.inductionloop.getSubscriptionResults()
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop0500_1'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop0500_1'}, Config.kafkaTopicLoopDetectorOccupancies)
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop0500_2'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop0500_2'}, Config.kafkaTopicLoopDetectorOccupancies)
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop0500_3'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop0500_3'}, Config.kafkaTopicLoopDetectorOccupancies)
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop01500_1'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop01500_1'}, Config.kafkaTopicLoopDetectorOccupancies)
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop01500_2'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop01500_2'}, Config.kafkaTopicLoopDetectorOccupancies)
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop01500_3'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop01500_3'}, Config.kafkaTopicLoopDetectorOccupancies)

            if cls.hard_shoulder_on:
                if 'passenger' not in traci.lane.getAllowed('Shoulder01_0'):
                    print("Opening hard shoulder...")
                    traci.lane.setAllowed('Shoulder01_0', ['passenger'])
            else:
                if 'passenger' in traci.lane.getAllowed('Shoulder01_0'):
                    print("Closing hard shoulder...")
                    traci.lane.setDisallowed('Shoulder01_0', ['passenger'])

            cls.tick += 1
            if (cls.tick % 10) == 0:
                if Config.kafkaUpdates is False:
                    cls.applyFileConfig()
                else:
                    cls.applyKafkaConfig()