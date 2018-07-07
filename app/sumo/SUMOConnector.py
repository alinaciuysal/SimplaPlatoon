from sumolib import checkBinary
from app import Config
import traci
from colorama import Fore

import os.path

# Starts SUMO in the background using the defined network
def start():
    if Config.sumoUseGUI:
        sumoBinary = checkBinary('sumo-gui')
    else:
        sumoBinary = checkBinary('sumo')

    current_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    map_dir = os.path.abspath(os.path.join(parent_dir, "map"))
    sumo_map = os.path.abspath(os.path.join(map_dir, Config.sumoConfig))
    traci.start([sumoBinary, "-c", sumo_map, "--no-step-log", "true", "--no-warnings", "true"])

