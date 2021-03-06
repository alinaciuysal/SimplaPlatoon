import os
import sys

from app.streaming import KafkaConnector

sys.path.append(os.path.join(os.environ.get("SUMO_HOME"), "tools"))

from app.logging import info
from app.simulation.PlatoonSimulation import PlatoonSimulation
from app.streaming import KafkaPublisher
from colorama import Fore
from app.sumo import SUMOConnector, SUMODependency
import app.Config as Config
import app.simpla
import traci

def initiateSimulation():
    info('#####################################', Fore.CYAN)
    info('# Starting Traffic-Control-A9-v0.1  #', Fore.CYAN)
    info('#####################################', Fore.CYAN)
    info('# Configuration:', Fore.YELLOW)
    info('# Kafka-Host   -> ' + Config.kafkaHost, Fore.YELLOW)

    # init sending updates to kafka and getting commands from there
    if Config.kafkaUpdates:
        KafkaPublisher.connect()
        KafkaConnector.connect()

    # Check if sumo is installed and available
    SUMODependency.checkDeps()
    info('# SUMO-Dependency check OK!', Fore.GREEN)
    SUMOConnector.start()
    info("\n# Starting the simulation!", Fore.GREEN)

    current_dir = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.abspath(os.path.join(current_dir, "map", "simpla.cfg"))
    platoon_mgr = app.simpla.load(file_path)
    PlatoonSimulation.start(platoon_mgr)
    app.simpla.stop()

    # Simulation ended, so we shutdown
    info(Fore.RED + '# Shutdown' + Fore.RESET)
    traci.close()
    sys.stdout.flush()
    return None
