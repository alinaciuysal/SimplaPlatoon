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
            file_path = os.path.join("..", "..", "parameters.json") # relative path to this file
            with open(file_path) as f:
                parameters = json.load(f)
            cls.changeVariables(parameters)
        except:
            pass

    @classmethod
    def applyKafkaConfig(cls):
        """ Gets a new configuration value from Kafka"""
        new_conf = KafkaConnector.checkForNewConfiguration()
        if new_conf is not None:
            info("new_conf arrived", new_conf)
        # else:
            # NEW: apply platoon configs
            # print("setting config")
            # config = json.load(open('./parameters.json'))
            # setValues(config)
            # print("new globals", str(getValues()))

    @classmethod
    def start(cls, platoon_mgr):
        """ start the simulation """
        info("# Applying file config")
        cls.applyFileConfig()

        info("# Started adding initial cars to the simulation")
        platoon_mgr.applyCarCounter()
        while 1:
            # let the cars process this step via platoonmgr
            traci.simulationStep()

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
                warn(str(variable_name) + " does not exist in Config.py")
