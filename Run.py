import os, sys

from app.streaming import KafkaConnector

sys.path.append(os.path.join(os.environ.get("SUMO_HOME"), "tools"))

from app.logging import info
from app.simulation.Simulation import Simulation
from app.simulation.PlatoonSimulation import PlatoonSimulation
from app.streaming import KafkaForword
from colorama import Fore
from app.sumo import SUMOConnector, SUMODependency
import app.simpla
import traci


def run():
    info('#####################################', Fore.CYAN)
    info('# Starting Traffic-Control-A9-v0.1  #', Fore.CYAN)
    info('#####################################', Fore.CYAN)
    info('# Configuration:', Fore.YELLOW)
    info('# Kafka-Host   -> ' + app.Config.kafkaHost, Fore.YELLOW)
    info('# Kafka-Topic1 -> ' + app.Config.kafkaTopicTicks, Fore.YELLOW)
    info('# Kafka-Topic2 -> ' + app.Config.kafkaTopicLoopDetectorOccupancies, Fore.YELLOW)
    info('# Kafka-Topic3 -> ' + app.Config.kafkaTopicDurationForTrips, Fore.YELLOW)
    info('# Kafka-Topic4 -> ' + app.Config.kafkaTopicReportedValues, Fore.YELLOW)

    # init sending updates to kafka and getting commands from there
    if app.Config.kafkaUpdates:
        KafkaForword.connect()
        KafkaConnector.connect()

    # Check if sumo is installed and available
    SUMODependency.checkDeps()
    info('# SUMO-Dependency check OK!', Fore.GREEN)
    SUMOConnector.start()
    info("\n# Starting the simulation!", Fore.GREEN)

    results = None
    if app.Config.platooning:
        current_dir = os.path.abspath(os.path.dirname(__file__))
        file_path = os.path.abspath(os.path.join(current_dir, "app", "map", "simpla.cfg"))
        platoon_mgr = app.simpla.load(file_path)
        results = PlatoonSimulation.start(platoon_mgr)
        app.simpla.stop()
    else:
        info("\n# SUMO-Application started OK!", Fore.GREEN)
        Simulation.start()
    # Simulation ended, so we shutdown
    info(Fore.RED + '# Shutdown' + Fore.RESET)
    traci.close()
    sys.stdout.flush()

    return results


if __name__ == '__main__':
    run()