import json
import traci
from app.streaming import KafkaPublisher, KafkaConnector
from app.logging import *
import os.path
import app.Config as Config

simulationEnded = False


class PlatoonSimulation(object):

    @classmethod
    def applyFileConfig(cls):
        """ reads configs from a json and applies it at realtime to the simulation """
        try:
            file_path = os.path.join("parameters.json") # relative path to Run.py
            with open(file_path) as f:
                parameters = json.load(f)
            cls.changeVariables(parameters=parameters)
            info("# New parameters -> " + str(Config.parameters), Fore.GREEN)
        except Exception as e:
            print(e)
            pass

    @classmethod
    def applyKafkaConfig(cls):
        """ Gets a new configuration value from Kafka"""
        new_conf = KafkaConnector.checkForNewConfiguration()
        if new_conf is not None:
            info("new configuration arrived" + str(new_conf), Fore.GREEN)
            cls.changeVariables(parameters=new_conf)

    @classmethod
    def start(cls, platoon_mgr):
        """ start the simulation """
        info("# Applying file config")
        cls.applyFileConfig()

        info("# Started adding initial cars to the simulation", Fore.GREEN)
        platoon_mgr.applyCarCounter()

        kafkaIndex = 1
        while 1:
            # let the cars process this step via platoonmgr
            traci.simulationStep()
            # apply kafka config in 10 ticks
            if kafkaIndex % 10 == 0:
                cls.applyKafkaConfig()
            kafkaIndex += 1

    @classmethod
    def changeVariables(cls, parameters):
        '''
        :param parameters: dict that contains parameters to be changed
        :return:
        '''
        for variable_name in parameters:
            value = parameters[variable_name]
            # there should be a better way instead of these statements
            if variable_name == "maxVehiclesInPlatoon":
                Config.parameters["changeable"]["maxVehiclesInPlatoon"] = value
            elif variable_name == "catchupDistance":
                Config.parameters["changeable"]["catchupDistance"] = value
                Config.parameters["contextual"]["lookAheadDistance"] = value # set same value of catchupDist, as we did in experiments
            elif variable_name == "maxPlatoonGap":
                Config.parameters["changeable"]["maxPlatoonGap"] = value
            elif variable_name == "platoonSplitTime":
                Config.parameters["changeable"]["platoonSplitTime"] = value
            elif variable_name == "joinDistance":
                Config.parameters["changeable"]["joinDistance"] = value
            elif variable_name == "switchImpatienceFactor":
                Config.parameters["contextual"]["switchImpatienceFactor"] = value
            elif variable_name == "totalCarCounter":
                Config.parameters["contextual"]["totalCarCounter"] = value
            elif variable_name == "platoonCarCounter":
                Config.parameters["contextual"]["platoonCarCounter"] = value
            elif variable_name == "extended_simpla_logic":
                Config.parameters["contextual"]["extended_simpla_logic"] = value
            else:
                warn(str(variable_name) + " does not exist in Config.py", Fore.RED)
