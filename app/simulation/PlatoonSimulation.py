import traci


class PlatoonSimulation(object):

    @classmethod
    def start(cls, platoon_mgr):
        """ start the simulation """
        print("# Started adding initial cars to the simulation")

        global simulationEnded
        simulationEnded = False
        platoon_mgr.applyCarCounter()
        while not simulationEnded:
            # let the cars process this step via platoonmgr
            traci.simulationStep()

        results = platoon_mgr.get_statistics()
        return results