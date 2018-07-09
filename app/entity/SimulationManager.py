from app import Config
from app.entity.Car import Car
import traci
import traci.constants as tc
import numpy as np

class NullCar:
    """ a car with no function used for error prevention """
    def __init__(self):
        pass

    def setArrived(self, tick):
        pass


class SimulationManager(traci.StepListener):
    """ central registry for all our cars we have in the sumo simulation """

    tick = None
    carIndexCounter = None
    cars = None
    totalTrips = None
    totalTripAverage = None
    totalCarCounter = None
    # average of all speeds
    totalSpeedAverage = None
    # average of respective metrics
    totalCO2EmissionAverage = None
    totalCOEmissionAverage = None
    totalFuelConsumptionAverage = None
    totalHCEmissionAverage = None
    totalPMXEmissionAverage = None
    totalNOxEmissionAverage = None
    totalNoiseEmissionAverage = None
    _subscriptionResults = None

    def __init__(self):
        self.tick = 0
        # the total amount of cars that should be in the system
        self.totalCarCounter = Config.nonPlatoonCarCounter + Config.platoonCarCounter

        # always increasing counter for carIDs
        self.carIndexCounter = 0
        # list of all cars, type: dict(str, Car)
        self.cars = dict()
        # counts the number of finished trips
        self.totalTrips = 0
        # average of all trip durations
        self.totalTripAverage = 0
        # average of all trip overheads (overhead is TotalTicks/PredictedTicks)
        self.totalTripOverheadAverage = 0
        self.totalSpeedAverage = 0

        # average of respective metrics
        self.totalCO2EmissionAverage = 0
        self.totalCOEmissionAverage = 0
        self.totalFuelConsumptionAverage = 0
        self.totalHCEmissionAverage = 0
        self.totalPMXEmissionAverage = 0
        self.totalNOxEmissionAverage = 0
        self.totalNoiseEmissionAverage = 0

    def applyCarCounter(self):
        """ syncs the value of the carCounter to the SUMO simulation """
        while len(self.cars) < self.totalCarCounter:
            self.addCarToSimulation(self.tick)

    def addCarToSimulation(self, tick):
        self.carIndexCounter += 1
        c = Car(self.carIndexCounter)
        self.cars[c.id] = c
        c.addToSimulation(tick)

    def findById(self, carID):
        """ returns a car by a given carID """
        try:
            return self.cars[carID]
        except:
            return NullCar()

    def _removeArrived(self):
        for ID in traci.simulation.getArrivedIDList():
            veh = self.cars.pop(ID)
            self.totalTrips += 1
            self._updateStatistics(veh)

            self.addCarToSimulation(self.tick)

    def step(self, s=0):
        '''step(int)
        Manages simulation at each time step.
        '''
        self.tick += 1
        # Handle vehicles entering and leaving the simulation
        self._removeArrived()
        self._updateVehicleStates()
        self._endSimulation()

    def stop(self):
        '''stop()

        Immediately release all vehicles from the managers control, and unsubscribe them from traci
        '''

        for veh in self.cars.values():
            traci.vehicle.unsubscribe(veh.getID())
        self.cars = dict()

    def _endSimulation(self):
        import app.simulation.Simulation as ps
        if simTime() % Config.nrOfTicks == 0:
            ps.simulationEnded = True

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

            if CO2Emission >= 0:
                veh.reportedCO2Emissions.append(CO2Emission)

            if COEmission >= 0:
                veh.reportedCOEmissions.append(COEmission)

            if HCEmission >= 0:
                veh.reportedHCEmissions.append(HCEmission)

            if PMXEmission >= 0:
                veh.reportedPMXEmissions.append(PMXEmission)

            if NOxEmission >= 0:
                veh.reportedNOxEmissions.append(NOxEmission)

            if FuelConsumption >= 0:
                veh.reportedFuelConsumptions.append(FuelConsumption)

            if NoiseEmission >= 0:
                veh.reportedNoiseEmissions.append(NoiseEmission)

            if speed >= 0:
                veh.reportedSpeeds.append(speed)

    def _updateStatistics(self, veh):
        # we don't need a mean here because it should only be calculated once the vehicle lefts simulation
        durationForTrip = simTime() - veh.currentRouteBeginTick
        self.totalTripAverage = self.addToAverage(self.totalTrips, self.totalTripAverage, durationForTrip)

        co2 = np.mean(veh.reportedCO2Emissions)
        self.totalCO2EmissionAverage = self.addToAverage(self.totalTrips, self.totalCO2EmissionAverage, co2)

        co = np.mean(veh.reportedCOEmissions)
        self.totalCOEmissionAverage = self.addToAverage(self.totalTrips, self.totalCOEmissionAverage, co)

        hc = np.mean(veh.reportedHCEmissions)
        self.totalHCEmissionAverage = self.addToAverage(self.totalTrips, self.totalHCEmissionAverage, hc)

        pmx = np.mean(veh.reportedPMXEmissions)
        self.totalPMXEmissionAverage = self.addToAverage(self.totalTrips, self.totalPMXEmissionAverage, pmx)

        no = np.mean(veh.reportedNOxEmissions)
        self.totalNOxEmissionAverage = self.addToAverage(self.totalTrips, self.totalNOxEmissionAverage, no)

        fuel = np.mean(veh.reportedFuelConsumptions)
        self.totalFuelConsumptionAverage = self.addToAverage(self.totalTrips, self.totalFuelConsumptionAverage, fuel)

        noise = np.mean(veh.reportedNoiseEmissions)
        self.totalNoiseEmissionAverage = self.addToAverage(self.totalTrips, self.totalNoiseEmissionAverage, noise)

        speed = np.mean(veh.reportedSpeeds)
        self.totalSpeedAverage = self.addToAverage(self.totalTrips, self.totalSpeedAverage, speed)

    def addToAverage(self, totalCount, totalValue, newValue):
        """ simple sliding average calculation """
        return ((1.0 * totalCount * totalValue) + newValue) / (totalCount + 1)

    def get_statistics(self):
        config = dict(
            platoonCarCounter=Config.platoonCarCounter,
            nonPlatoonCarCounter=Config.nonPlatoonCarCounter,
        )

        averages = dict(
            totalTripAverage=self.totalTripAverage,
            totalCO2EmissionAverage=self.totalCO2EmissionAverage,
            totalSpeedAverage=self.totalSpeedAverage,
            totalCOEmissionAverage=self.totalCOEmissionAverage,
            totalFuelConsumptionAverage=self.totalFuelConsumptionAverage,
            totalHCEmissionAverage=self.totalHCEmissionAverage,
            totalPMXEmissionAverage=self.totalPMXEmissionAverage,
            totalNOxEmissionAverage=self.totalNOxEmissionAverage,
            totalNoiseEmissionAverage=self.totalNoiseEmissionAverage,
        )

        res = dict(
            averages=averages,
            totalTrips=self.totalTrips,
            config=config,
            simTime=simTime()
        )

        return res

def simTime():
    return traci.simulation.getCurrentTime() / 1000.


