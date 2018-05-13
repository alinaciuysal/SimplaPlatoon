import json
import traci
import traci.constants as tc
import app.Config as cfg

from app.streaming import KafkaForword, KafkaConnector
from app.simpla import update
from app.simpla._config import setValues, getValues
from app.entity import CarRegistry
from app.util import Util

class PlatoonSimulation(object):

    # the current tick of the simulation
    tick = 0

    cars = {} # type: dict[str,app.entitiy.Car]

    # counts the number of finished trips
    totalTrips = 0
    # average of all trip durations
    totalTripAverage = 0
    # average of all trip overheads (overhead is TotalTicks/PredictedTicks)
    totalTripOverheadAverage = 0

    # average of all CO2 emissions
    totalCO2EmissionAverage = 0
    # average of all CO emissions
    totalCOEmissionAverage = 0
    # average of all fuel emissions
    totalFuelConsumptionAverage = 0
    # average of all speeds
    totalSpeedAverage = 0

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
            setValues(config)
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
        else:
            # NEW: apply platoon configs
            # print("setting config")
            config = json.load(open('./knobs.json'))
            setValues(config)
            # print("new globals", str(getValues()))

    @classmethod
    def start(cls):
        # _useStepListener = 'addStepListener' in dir(traci)
        # print(_useStepListener) # prints out true because version is >= 0.30
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()

            KafkaForword.publish({"tick": cls.tick}, cfg.kafkaTopicTicks)

            # attach listener to each car in the simulation
            for veh_id in traci.simulation.getDepartedIDList():
                traci.vehicle.subscribe(veh_id, [tc.VAR_LANE_ID,
                                                 tc.VAR_LANEPOSITION,
                                                 tc.VAR_SPEED,
                                                 tc.VAR_CO2EMISSION,
                                                 tc.VAR_COEMISSION,
                                                 tc.VAR_FUELCONSUMPTION])

            cars = traci.vehicle.getSubscriptionResults()
            for car in cars:
                speed = cars[car][tc.VAR_SPEED]
                fuel = cars[car][tc.VAR_FUELCONSUMPTION]
                co2 = cars[car][tc.VAR_CO2EMISSION]
                co = cars[car][tc.VAR_COEMISSION]

                KafkaForword.publish({"speed": speed}, cfg.kafkaTopicCarSpeeds)
                KafkaForword.publish({"fuel": fuel}, cfg.kafkaTopicCarFuels)
                KafkaForword.publish({"co2": co2}, cfg.kafkaTopicCarEmissions)
                KafkaForword.publish({"co": co}, cfg.kafkaTopicCarEmissions)

            # Check for removed cars and re-add them into the system
            # for removedCarId in traci.simulation.getSubscriptionResults()[122]:
            #     # CarRegistry.findById(removedCarId).setArrived(cls.tick)
            #     print("removedCarId")
            #     durationForTrip = (cls.tick - 0) # TODO: is this true?
            #     CarRegistry.totalTripAverage = addToAverage(CarRegistry.totalTrips,  # 100 for faster updates
            #                                             CarRegistry.totalTripAverage,
            #                                             durationForTrip)
            # loopDetectorOccupancies = traci.inductionloop.getSubscriptionResults()
            # KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop0500_1'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop0500_1'}, cfg.kafkaTopicLoopDetectorOccupancies)
            # KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop0500_2'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop0500_2'}, cfg.kafkaTopicLoopDetectorOccupancies)
            # KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop0500_3'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop0500_3'}, cfg.kafkaTopicLoopDetectorOccupancies)
            # KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop01500_1'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop01500_1'}, cfg.kafkaTopicLoopDetectorOccupancies)
            # KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop01500_2'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop01500_2'}, cfg.kafkaTopicLoopDetectorOccupancies)
            # KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop01500_3'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop01500_3'}, cfg.kafkaTopicLoopDetectorOccupancies)
            #
            # if cls.hard_shoulder_on:
            #     if 'passenger' not in traci.lane.getAllowed('Shoulder01_0'):
            #         print("Opening hard shoulder...")
            #         traci.lane.setAllowed('Shoulder01_0', ['passenger'])
            # else:
            #     if 'passenger' in traci.lane.getAllowed('Shoulder01_0'):
            #         print("Closing hard shoulder...")
            #         traci.lane.setDisallowed('Shoulder01_0', ['passenger'])


            cls.tick += 1
            if (cls.tick % 10) == 0:
                if cfg.kafkaUpdates is False:
                    cls.applyFileConfig()
                else:
                    cls.applyKafkaConfig()

                # print status update if we are not running in parallel mode
                print(str(cfg.processID) + " -> Step:" + str(cls.tick) + " # Driving cars: " + str(
                    traci.vehicle.getIDCount()) + "/"
                    + " # totalFuelConsumptionAverage: " + str(cls.totalFuelConsumptionAverage)
                    + " # totalSpeedAverage: " + str(cls.totalSpeedAverage)
                    + " # totalCO2EmissionAverage: " + str(cls.totalCO2EmissionAverage)
                    + " # totalCOEmissionAverage: " + str(cls.totalCOEmissionAverage) )