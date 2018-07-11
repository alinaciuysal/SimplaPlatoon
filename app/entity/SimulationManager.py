from app.entity.Car import Car
import traci
import traci.constants as tc
import app.Config as Config

class SimulationManager(traci.StepListener):
    """ central registry for all our cars we have in the sumo simulation """

    carIndex = None
    cars = None
    totalCarCounter = None

    TripDurations = None
    CO2Emissions = None
    COEmissions = None
    HCEmissions = None
    PMXEmissions = None
    NOxEmissions = None
    FuelConsumptions = None
    NoiseEmissions = None
    Speeds = None

    _subscriptionResults = None

    def __init__(self):
        # total amount of cars that should be in this regular scenario system
        self.totalCarCounter = Config.totalCarCounter

        # always increasing counter for carIDs
        self.carIndex = 0
        # list of all cars, type: dict(str, Car)
        self.cars = dict()

        self.TripDurations = []
        self.CO2Emissions = []
        self.COEmissions = []
        self.HCEmissions = []
        self.PMXEmissions = []
        self.NOxEmissions = []
        self.FuelConsumptions = []
        self.NoiseEmissions = []
        self.Speeds = []
        self.simTime = simTime()

    def applyCarCounter(self):
        """ syncs the value of the carCounter to the SUMO simulation """
        while len(self.cars) < self.totalCarCounter:
            self.addCarToSimulation(self.simTime)

    def addCarToSimulation(self, simTime):
        c = Car(self.carIndex)
        self.cars[c.id] = c
        c.addToSimulation(simTime)
        self.carIndex += 1

    def findById(self, carID):
        """ returns a car by a given carID """
        return self.cars[carID]


    def _removeArrived(self):
        for ID in traci.simulation.getArrivedIDList():
            veh = self.cars.pop(ID)
            self._updateStatistics(veh)
            self.addCarToSimulation(self.simTime)

    def step(self, s=0):
        '''step(int)
        Manages simulation at each time step.
        '''
        # Handle vehicles entering and leaving the simulation
        self._removeArrived()
        self._updateVehicleStates()
        if Config.forTests:
            self._endSimulation()

    def stop(self):
        '''stop()

        Immediately release all vehicles from the managers control, and unsubscribe them from traci
        '''

        for veh in self.cars.values():
            traci.vehicle.unsubscribe(veh.getID())
        self.cars = dict()


    def _updateVehicleStates(self):
        '''_updateVehicleStates()

        This updates the vehicles' states with information from the simulation
        '''
        self._subscriptionResults = traci.vehicle.getSubscriptionResults()
        for veh in self.cars.values():
            speed = self._subscriptionResults[veh.getID()][tc.VAR_SPEED]
            # Emissions
            CO2Emission = self._subscriptionResults[veh.getID()][tc.VAR_CO2EMISSION]
            COEmission = self._subscriptionResults[veh.getID()][tc.VAR_COEMISSION]
            HCEmission = self._subscriptionResults[veh.getID()][tc.VAR_HCEMISSION]
            PMXEmission = self._subscriptionResults[veh.getID()][tc.VAR_PMXEMISSION]
            NOxEmission = self._subscriptionResults[veh.getID()][tc.VAR_NOXEMISSION]
            FuelConsumption = self._subscriptionResults[veh.getID()][tc.VAR_FUELCONSUMPTION]
            NoiseEmission = self._subscriptionResults[veh.getID()][tc.VAR_NOISEEMISSION]

            # sometimes emissions are always 0.0, filters them out
            if CO2Emission > 0:
                veh.reportedCO2Emissions.append(CO2Emission)

            if COEmission > 0:
                veh.reportedCOEmissions.append(COEmission)

            if HCEmission > 0:
                veh.reportedHCEmissions.append(HCEmission)

            if PMXEmission > 0:
                veh.reportedPMXEmissions.append(PMXEmission)

            if NOxEmission > 0:
                veh.reportedNOxEmissions.append(NOxEmission)

            if FuelConsumption > 0:
                veh.reportedFuelConsumptions.append(FuelConsumption)

            if NoiseEmission > 0:
                veh.reportedNoiseEmissions.append(NoiseEmission)

            if speed > 0:
                veh.reportedSpeeds.append(speed)

    def _updateStatistics(self, veh):
        tripDuration = simTime() - veh.currentRouteBeginTime
        self.TripDurations.append(tripDuration)
        self.CO2Emissions.extend(veh.reportedCO2Emissions)
        self.COEmissions.extend(veh.reportedCOEmissions)
        self.HCEmissions.extend(veh.reportedHCEmissions)
        self.PMXEmissions.extend(veh.reportedPMXEmissions)
        self.NOxEmissions.extend(veh.reportedNOxEmissions)
        self.FuelConsumptions.extend(veh.reportedFuelConsumptions)
        self.NoiseEmissions.extend(veh.reportedNoiseEmissions)
        self.Speeds.extend(veh.reportedSpeeds)

    def addToAverage(self, totalCount, totalValue, newValue):
        """ simple sliding average calculation """
        return ((1.0 * totalCount * totalValue) + newValue) / (totalCount + 1)

    def get_statistics(self):
        config = dict(
            totalCarCounter=Config.totalCarCounter
        )
        data = dict(
            TripDurations=self.TripDurations,
            CO2Emissions=self.CO2Emissions,
            # COEmissions=self.COEmissions,
            # HCEmissions=self.HCEmissions,
            # PMXEmissions=self.PMXEmissions,
            # NOxEmissions=self.NOxEmissions,
            FuelConsumptions=self.FuelConsumptions,
            # NoiseEmissions=self.NoiseEmissions,
            Speeds=self.Speeds,
            Overheads=self.Overheads
        )

        res = dict(
            data=data,
            config=config,
            simTime=simTime()
        )
        # if required, total number of trips can be obtained with len(TripDurations)

        return res

    def _endSimulation(self):
        import app.simulation.Simulation as ps
        if simTime() % Config.nrOfTicks == 0:
            ps.simulationEnded = True

def simTime():
    return traci.simulation.getCurrentTime() / 1000.


