import json
import traci
import traci.constants as tc

import app.Config as cfg
import numpy as np
from app.streaming import KafkaForword, KafkaConnector

class Simulation(object):

    # the current tick of the simulation
    tick = 0
    # whether the hard should should be open
    hard_shoulder_on = False

    reportedCO2Emissions = []
    reportedCOEmissions = []
    reportedHCEmissions = []
    reportedPMXEmissions = []
    reportedNOxEmissions = []
    reportedFuelConsumptions = []
    reportedNoiseEmissions = []
    reportedSpeeds = []

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

            KafkaForword.publish({"tick": 1}, cfg.kafkaTopicTicks)

            # attach listener to each car in the simulation
            for veh_id in traci.simulation.getDepartedIDList():
                traci.vehicle.subscribe(veh_id, [tc.VAR_LANE_ID, tc.VAR_LANEPOSITION, tc.VAR_SPEED,
                                                 tc.VAR_CO2EMISSION,
                                                 tc.VAR_COEMISSION,
                                                 tc.VAR_HCEMISSION,
                                                 tc.VAR_PMXEMISSION,
                                                 tc.VAR_NOXEMISSION,
                                                 tc.VAR_FUELCONSUMPTION,
                                                 tc.VAR_NOISEEMISSION])

            cars = traci.vehicle.getSubscriptionResults()
            for car in cars:
                lane = cars[car][tc.VAR_LANE_ID]
                if lane == "Shoulder01_1" or lane == "Shoulder01_2" or lane == "Shoulder01_3":
                    position = cars[car][tc.VAR_LANEPOSITION]
                    if 500 < position < 1500:
                        KafkaForword.publish({"speed": cars[car][tc.VAR_SPEED]}, cfg.kafkaTopicCarSpeeds)
                # NEW
                CO2Emission = cars[car][tc.VAR_CO2EMISSION]
                COEmission = cars[car][tc.VAR_COEMISSION]
                HCEmission = cars[car][tc.VAR_HCEMISSION]
                PMXEmission = cars[car][tc.VAR_PMXEMISSION]
                NOxEmission = cars[car][tc.VAR_NOXEMISSION]
                FuelConsumption = cars[car][tc.VAR_FUELCONSUMPTION]
                NoiseEmission = cars[car][tc.VAR_NOISEEMISSION]
                Speed = cars[car][tc.VAR_SPEED]

                cls.reportedCO2Emissions.append(CO2Emission)
                cls.reportedCOEmissions.append(COEmission)
                cls.reportedHCEmissions.append(HCEmission)
                cls.reportedPMXEmissions.append(PMXEmission)
                cls.reportedNOxEmissions.append(NOxEmission)
                cls.reportedFuelConsumptions.append(FuelConsumption)
                cls.reportedNoiseEmissions.append(NoiseEmission)
                cls.reportedSpeeds.append(Speed)

            loopDetectorOccupancies = traci.inductionloop.getSubscriptionResults()
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop0500_1'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop0500_1'}, cfg.kafkaTopicLoopDetectorOccupancies)
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop0500_2'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop0500_2'}, cfg.kafkaTopicLoopDetectorOccupancies)
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop0500_3'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop0500_3'}, cfg.kafkaTopicLoopDetectorOccupancies)
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop01500_1'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop01500_1'}, cfg.kafkaTopicLoopDetectorOccupancies)
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop01500_2'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop01500_2'}, cfg.kafkaTopicLoopDetectorOccupancies)
            KafkaForword.publish({"occupancy" : loopDetectorOccupancies['loop01500_3'][tc.LAST_STEP_OCCUPANCY], "id" : 'loop01500_3'}, cfg.kafkaTopicLoopDetectorOccupancies)

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
                if cfg.kafkaUpdates is False:
                    cls.applyFileConfig()
                else:
                    cls.applyKafkaConfig()
        # NEW: get statistics
        results = cls.get_statistics()
        print(results)

    @classmethod
    def get_statistics(self):
        print(len(self.reportedCO2Emissions))
        res = dict(
            totalCO2EmissionAverage=np.mean(self.reportedCO2Emissions),
            totalCOEmissionAverage=np.mean(self.reportedCOEmissions),
            totalFuelConsumptionAverage=np.mean(self.reportedFuelConsumptions),
            totalHCEmissionAverage=np.mean(self.reportedHCEmissions),
            totalPMXEmissionAverage=np.mean(self.reportedPMXEmissions),
            totalNOxEmissionAverage=np.mean(self.reportedNOxEmissions),
            totalNoiseEmissionAverage=np.mean(self.reportedNoiseEmissions),
            totalSpeedAverage=np.mean(self.reportedSpeeds),
        )
        return res