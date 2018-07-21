import os
import sys

sys.path.append(os.path.join(os.environ.get("SUMO_HOME"), "tools"))

from app.logging import info
from app.simulation.PlatoonSimulation import PlatoonSimulation
from colorama import Fore
from app.sumo import SUMOConnector, SUMODependency
import app.simpla
import traci


def initiateSimulation(ignore_first_n_results, sample_size, extended_simpla_logic):
    info('#####################################', Fore.CYAN)
    info('# Starting Platooning-A9  #', Fore.CYAN)
    info('#####################################', Fore.CYAN)

    # Check if sumo is installed and available
    SUMODependency.checkDeps()
    info('# SUMO-Dependency check OK!', Fore.GREEN)
    SUMOConnector.start()
    info("\n# Starting the simulation!", Fore.GREEN)

    current_dir = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.abspath(os.path.join(current_dir, "map", "simpla.cfg"))
    platoon_mgr = app.simpla.load(file_path, ignore_first_n_results, sample_size, extended_simpla_logic)
    results = PlatoonSimulation.start(platoon_mgr)
    app.simpla.stop()

    # Simulation ended, so we shutdown
    info(Fore.RED + '# Shutdown' + Fore.RESET)
    traci.close()
    sys.stdout.flush()

    return results