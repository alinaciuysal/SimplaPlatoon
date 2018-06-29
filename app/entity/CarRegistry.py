from app import Config

from app.entity.Car import Car


class NullCar:
    """ a car with no function used for error prevention """
    def __init__(self):
        pass

    def setArrived(self, tick):
        pass


class CarRegistry(object):
    """ central registry for all our cars we have in the sumo simulation """

    # the total amount of cars that should be in the system
    totalCarCounter = Config.totalCarCounter
    # always increasing counter for carIDs
    carIndexCounter = 0
    # list of all cars, type: dict(str, Car)
    cars = {}
    # counts the number of finished trips
    totalTrips = 0
    # average of all trip durations
    totalTripAverage = 0
    # average of all trip overheads (overhead is TotalTicks/PredictedTicks)
    totalTripOverheadAverage = 0

    @classmethod
    def applyCarCounter(cls):
        """ syncs the value of the carCounter to the SUMO simulation """
        while len(CarRegistry.cars) < cls.totalCarCounter:
            # to less cars -> add new
            cls.carIndexCounter += 1
            c = Car(cls.carIndexCounter)
            cls.cars[c.id] = c
            c.addToSimulation(0)
        while len(CarRegistry.cars) > cls.totalCarCounter:
            # to many cars -> remove cars
            (k, v) = CarRegistry.cars.popitem()
            v.remove()

    @classmethod
    def findById(cls, carID):
        """ returns a car by a given carID """
        try:
            return CarRegistry.cars[carID]
        except:
            return NullCar()

    @classmethod
    def processTick(cls, tick):
        """ processes the simulation tick on all registered cars """
        for key in CarRegistry.cars:
            CarRegistry.cars[key].processTick(tick)
