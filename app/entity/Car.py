import random
import traci
import traci.constants as tc
from app import Config

# from app.Util import addToAverage
from app.network.Network import Network
# from app.routing.CustomRouter import CustomRouter
# from app.routing.RouterResult import RouterResult
# from app.streaming import RTXForword

def simTime():
    return traci.simulation.getCurrentTime() / 1000.


class Car:
    """ a abstract class of something that is driving around the streets """

    def __init__(self, carIndex):
        # the string id
        self.id = str(carIndex)  # type: str
        # when we started the route
        self.currentRouteBeginTick = None
        # the id of the current route (somu)
        self.currentRouteID = None  # type: str
        # the id of the current edge/street the car is driving (sumo)
        self.currentEdgeID = None
        # the tick this car got on this edge/street
        self.currentEdgeBeginTick = None
        # the target node this car drives to
        self.targetID = None
        # the source node this car is coming from
        self.sourceID = None
        # if it is disabled, it will stop driving
        self.disabled = False
        # the cars acceleration in the simulation
        # self.acceleration = max(1, random.gauss(4, 2))
        # the cars deceleration in the simulation
        # self.deceleration = max(1, random.gauss(6, 2))
        # the driver imperfection in handling the car
        # self.imperfection = min(0.9, max(0.1, random.gauss(0.5, 0.5)))

        self.edges = traci.simulation.findRoute(fromEdge=Config.startEdgeID, toEdge=Config.endEdgeID).edges

        # NEW
        self.reportedCO2Emissions = []
        self.reportedCOEmissions = []
        self.reportedHCEmissions = []
        self.reportedPMXEmissions = []
        self.reportedNOxEmissions = []
        self.reportedFuelConsumptions = []
        self.reportedNoiseEmissions = []
        self.reportedSpeeds = []

    def addToSimulation(self, tick):
        """ adds this car to the simulation through the traci API """
        self.currentRouteBeginTick = tick
        try:
            typeID = "normal-car" # must be same with <vType> id in flow.rou.xml if used
            routeID = "normal-car-route-" + str(self.id)
            traci.route.add(routeID, self.edges)

            # TODO: hard-coded lane numbers, there should be getLaneNumber(edgeID) method in edge,
            # TODO: but there's no such fcn in current version
            # see: http://www.sumo.dlr.de/daily/pydoc/traci._edge.html#EdgeDomain-getLaneNumber
            # laneNumbers = traci.edge.getLaneNumber("12N")
            laneNumbers = [0, 1, 2, 3]
            arrivalLane = str(random.choice(laneNumbers))
            traci.vehicle.addFull(vehID=self.id, routeID=routeID, typeID='DEFAULT_VEHTYPE', depart=str(simTime()), departLane='random', departPos='base', departSpeed='0', arrivalLane=arrivalLane, arrivalPos='random')
            traci.vehicle.subscribe(self.id,
                                    (tc.VAR_ROAD_ID, tc.VAR_LANE_INDEX, tc.VAR_LANE_ID, tc.VAR_SPEED, tc.VAR_LANEPOSITION,
                                     tc.VAR_CO2EMISSION,
                                     tc.VAR_COEMISSION,
                                     tc.VAR_HCEMISSION,
                                     tc.VAR_PMXEMISSION,
                                     tc.VAR_NOXEMISSION,
                                     tc.VAR_FUELCONSUMPTION,
                                     tc.VAR_NOISEEMISSION))
        except Exception as e:
            print("error adding" + str(e))

    def getID(self):
        return self.id

    def removeFromTraci(self):
        """" removes this car from sumo & car registry """
        try:
            traci.vehicle.remove(self.id)
        except Exception as e:
            print(e)
