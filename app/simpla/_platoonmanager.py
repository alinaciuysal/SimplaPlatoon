# Eclipse SUMO, Simulation of Urban MObility; see https://eclipse.org/sumo
# Copyright (C) 2017-2017 German Aerospace Center (DLR) and others.
# This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v2.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v20.html

# @file    _platoonmanager.py
# @author Leonhard Luecken
# @date   2017-04-09
# @version $Id$


# TODO: For CATCHUP_FOLLOWER mode could also be set active if intra-platoon gap becomes too large

import traci
import traceback
from traci.exceptions import TraCIException
import traci.constants as tc

import _reporting as rp
import _config as cfg
import _pvehicle, _platoon
from _utils import SimplaException
from _reporting import simTime
from _platoonmode import PlatoonMode
from _collections import defaultdict
import app.Config as Config
from collections import namedtuple
warn = rp.Warner("PlatoonManager")
report = rp.Reporter("PlatoonManager")


PWP = namedtuple("PWP", ["first_carID", "second_carID"]) # https://stackoverflow.com/questions/4878881/python-tuples-dictionaries-as-keys-select-sort

class PlatoonManager(traci.StepListener):
    '''
    A PlatoonManager coordinates the initialization of platoons
    and adapts the vehicles in a platoon to change their controls accordingly.
    To use it, create a PlatoonManager and call its update() method in each
    simulation step.
    Do not create more than one PlatoonManager, if you cannot guarantee that
    the associated vehicle types are exclusive for each.
    '''
    carIndex = None
    _platoons = None
    _connectedVehicles = None
    totalCarCounter = Config.parameters["contextual"]["totalCarCounter"]
    platoonCarCounter = Config.parameters["contextual"]["platoonCarCounter"]
    maxVehiclesInPlatoon = Config.parameters["changeable"]["maxVehiclesInPlatoon"]
    pairwise_platoons = None

    def __init__(self):
        ''' PlatoonManager()
        Creates and initializes the PlatoonManager
        '''
        if rp.VERBOSITY >= 2:
            report("Initializing simpla.PlatoonManager...", True)
        # Load parameters from config
        # vehicle type filter
        self._typeSubstrings = cfg.VEH_SELECTORS
        if self._typeSubstrings == [""] and rp.VERBOSITY >= 1:
            warn("No typeSubstring given. Managing all vehicles.", True)
        elif rp.VERBOSITY >= 2:
            report("Managing all vTypes selected by %s" % str(self._typeSubstrings), True)
        # max intra platoon gap
        self._maxPlatoonGap = cfg.MAX_PLATOON_GAP
        # max distance for trying to catch up
        self._catchupDist = cfg.CATCHUP_DISTANCE

        # platoons currently in the simulation
        # map: platoon ID -> platoon objects
        self._platoons = dict()
        # IDs of all potential platoon members currently in the simulation
        # map: ID -> vehicle
        self._connectedVehicles = dict()

        self.pairwise_platoons = dict()

        self.carIndex = 0
        self.totalCarCounter = PlatoonManager.totalCarCounter
        self.platoonCarCounter = PlatoonManager.platoonCarCounter

        self.TripDurations = []
        self.FuelConsumptions = []
        self.Speeds = []
        self.Overheads = []
        self.TimeSpentInsidePlatoon = []
        self.NumberOfCarsInPlatoons = []
        self.ReportedPlatoonDurationsBeforeSplit = [] # it only includes intermediate platooning durations

        # integration step-length
        self._DeltaT = traci.simulation.getDeltaT() / 1000.

        # rate for executing the platoon logic
        if(1. / cfg.CONTROL_RATE < self._DeltaT):
            if rp.VERBOSITY >= 1:
                warn(
                    "Restricting given control rate (= %d per sec.) to 1 per timestep (= %g per sec.)" %
                    (cfg.CONTROL_RATE, 1. / self._DeltaT), True)
            self._controlInterval = self._DeltaT
        else:
            self._controlInterval = 1. / cfg.CONTROL_RATE

        self._timeSinceLastControl = 1000.

        # Check for undefined vtypes and fill with defaults
        for origType, specialTypes in cfg.PLATOON_VTYPES.items():
            if specialTypes[PlatoonMode.FOLLOWER] is None:
                if rp.VERBOSITY >= 2:
                    report("Setting unspecified follower vtype for '%s' to '%s'" %
                           (origType, specialTypes[PlatoonMode.LEADER]), True)
                specialTypes[PlatoonMode.FOLLOWER] = specialTypes[PlatoonMode.LEADER]
            if specialTypes[PlatoonMode.CATCHUP] is None:
                if rp.VERBOSITY >= 2:
                    report("Setting unspecified catchup vtype for '%s' to '%s'" % (origType, origType), True)
                specialTypes[PlatoonMode.CATCHUP] = origType
            if specialTypes[PlatoonMode.CATCHUP_FOLLOWER] is None:
                if rp.VERBOSITY >= 2:
                    report("Setting unspecified catchup-follower vtype for '%s' to '%s'" %
                           (origType, specialTypes[PlatoonMode.FOLLOWER]), True)
                specialTypes[PlatoonMode.CATCHUP_FOLLOWER] = specialTypes[PlatoonMode.FOLLOWER]
        # Commented snippet generated automatically a catchup follower type with a different color
        #                 catchupFollowerType = origType + "_catchupFollower"
        #                 specialTypes[PlatoonMode.CATCHUP]=catchupFollowerType
        #                 if rp.VERBOSITY >= 2:
        #                     print("Catchup follower type '%s' for '%s' dynamically created as duplicate of '%s'" %
        #                       (catchupFollowerType, origType, specialTypes[PlatoonMode.CATCHUP_FOLLOWER]))
        #                 traci.vehicletype.copy(specialTypes[PlatoonMode.CATCHUP_FOLLOWER] , catchupFollowerType)
        #                 traci.vehicletype.setColor(catchupFollowerType, (0, 255, 200, 0))

        # fill global lookup table for vType parameters (used below in safetycheck)
        knownVTypes = traci.vehicletype.getIDList()
        for origType, mappings in cfg.PLATOON_VTYPES.items():
            if origType not in knownVTypes:
                raise SimplaException(
                    "vType '%s' is unknown to sumo! Note: Platooning vTypes must be defined at startup." % origType)
            origLength = traci.vehicletype.getLength(origType)
            origEmergencyDecel = traci.vehicletype.getEmergencyDecel(origType)
            for typeID in list(mappings.values()) + [origType]:
                if typeID not in knownVTypes:
                    raise SimplaException(
                        "vType '%s' is unknown to sumo! Note: Platooning vTypes must be defined at startup." % typeID)
                mappedLength = traci.vehicletype.getLength(typeID)
                mappedEmergencyDecel = traci.vehicletype.getEmergencyDecel(typeID)
                if origLength != mappedLength:
                    if rp.VERBOSITY >= 1:
                        warn(("length of mapped vType '%s' (%sm.) does not equal length of original vType " +
                              "'%s' (%sm.)\nThis will probably lead to collisions.") % (
                                 typeID, mappedLength, origType, origLength), True)
                if origEmergencyDecel != mappedEmergencyDecel:
                    if rp.VERBOSITY >= 1:
                        warn(("emergencyDecel of mapped vType '%s' (%gm.) does not equal emergencyDecel of original " +
                              "vType '%s' (%gm.)") % (
                                 typeID, mappedEmergencyDecel, origType, origEmergencyDecel), True)
                _pvehicle.vTypeParameters[typeID][tc.VAR_TAU] = traci.vehicletype.getTau(typeID)
                _pvehicle.vTypeParameters[typeID][tc.VAR_DECEL] = traci.vehicletype.getDecel(typeID)
                _pvehicle.vTypeParameters[typeID][tc.VAR_MINGAP] = traci.vehicletype.getMinGap(typeID)
                _pvehicle.vTypeParameters[typeID][tc.VAR_EMERGENCY_DECEL] = traci.vehicletype.getEmergencyDecel(
                    typeID)


    def step(self, t=0):
        '''step(int)

        Manages platoons at each time step.
        NOTE: argument t is unused, larger step sizes than DeltaT are not supported.
        '''
        if not t==0 and rp.VERBOSITY >= 1:
            warn("Step lengths that differ from SUMO's simulation step length are not supported and probably lead to undesired behavior.\nConsider decreasing simpla's control rate instead.")
        # Handle vehicles entering and leaving the simulation
        self._removeArrived()
        self._timeSinceLastControl += self._DeltaT
        if self._timeSinceLastControl >= self._controlInterval:
            self._updateVehicleStates()
            self._manageFollowers()
            self._updatePlatoonOrdering()
            self._manageLeaders()
            self._adviseLanes()
            self._timeSinceLastControl = 0.
            if Config.forTests:
                self._endSimulation()

    def stop(self):
        '''stop()

        Immediately resets all vtypes, releases all vehicles from the managers control, and unsubscribes them from traci
        '''
        for veh in self._connectedVehicles.values():
            veh.setPlatoonMode(PlatoonMode.NONE)
            traci.vehicle.unsubscribe(veh.getID())
        self._connectedVehicles = dict()
        _platoon.Platoon._nextID = 0

    def getPlatoonLeaders(self):
        '''getPlatoonLeaders() -> list(PVehicle)

        Returns all vehicles currently leading a platoon (of size > 1).
        These can be in PlatoonMode.LEADER or in PlatoonMode.CATCHUP
        '''
        return [pltn.getVehicles()[0] for pltn in self._platoons.values() if pltn.size() > 1]

    def getSelectionSubstrings(self):
        '''getSelectionSubstring() -> string
        Returns the platoon manager's selection substring.
        '''
        return self._typeSubstrings

    def _updateVehicleStates(self):
        '''_updateVehicleStates()
        This updates the vehicles' states with information from the simulation
        '''
        self._subscriptionResults = traci.vehicle.getSubscriptionResults()
        for veh in self._connectedVehicles.values():
            veh.state.speed = self._subscriptionResults[veh.getID()][tc.VAR_SPEED]
            veh.state.edgeID = self._subscriptionResults[veh.getID()][tc.VAR_ROAD_ID]
            veh.state.laneID = self._subscriptionResults[veh.getID()][tc.VAR_LANE_ID]
            veh.state.laneIX = self._subscriptionResults[veh.getID()][tc.VAR_LANE_INDEX]
            veh.state.leaderInfo = traci.vehicle.getLeader(veh.getID(), self._catchupDist)

            # getDistance returns the distance the vehicle has already driven [in m]
            veh.state.distance = traci.vehicle.getDistance(veh.getID())

            # Emissions
            FuelConsumption = self._subscriptionResults[veh.getID()][tc.VAR_FUELCONSUMPTION]

            # sometimes reported values are always -1001 (error value) so we filter them out
            if FuelConsumption > 0:
                veh.state.reportedFuelConsumptions.append(FuelConsumption)
            if veh.state.speed > 0:
                veh.state.reportedSpeeds.append(veh.state.speed)

            # update respective metrics if there are more than 1 cars or only single car in each vehicle's platoon
            if len(veh.getPlatoon().getVehicles()) > 1:
                veh.state.durationInsidePlatoon += 1
            else:
                veh.state.durationOutsidePlatoon += 1

            if veh.state.leaderInfo is None:
                veh.state.leader = None
                veh.state.connectedVehicleAhead = False
                continue

            if veh.state.leader is None or veh.state.leader.getID() != veh.state.leaderInfo[0]:
                if self._isConnected(veh.state.leaderInfo[0]):
                    veh.state.leader = self._connectedVehicles[veh.state.leaderInfo[0]]
                    veh.state.connectedVehicleAhead = True
                else:
                    # leader is not connected -> check whether a connected vehicle is located further downstream
                    veh.state.leader = None
                    veh.state.connectedVehicleAhead = False
                    vehAheadID = veh.state.leaderInfo[0]
                    dist = veh.state.leaderInfo[1] + traci.vehicle.getLength(vehAheadID)
                    while dist < self._catchupDist:
                        nextLeaderInfo = traci.vehicle.getLeader(vehAheadID, self._catchupDist - dist)
                        if nextLeaderInfo is None:
                            break
                        vehAheadID = nextLeaderInfo[0]
                        if self._isConnected(vehAheadID):
                            veh.state.connectedVehicleAhead = True
                            if rp.VERBOSITY >= 4:
                                report("Found connected vehicle '%s' downstream of vehicle '%s' (at distance %s)" %
                                       (vehAheadID, veh.getID(), dist + nextLeaderInfo[1]))
                            break
                        dist += nextLeaderInfo[1] + traci.vehicle.getLength(vehAheadID)

    def _removeArrived(self):
        ''' _removeArrived()

        Remove all vehicles that have left the simulation from _connectedVehicles.
        Returns the number of removed connected vehicles
        '''
        count = 0
        toRemove = defaultdict(list)
        for ID in traci.simulation.getArrivedIDList():
            # first store arrived vehicles platoonwise
            if not self._isConnected(ID):
                continue
            if rp.VERBOSITY >= 2:
                report("Removing arrived vehicle '%s'" % ID)
            veh = self._connectedVehicles.pop(ID)
            self._updateStatistics(veh)
            toRemove[veh.getPlatoon().getID()].append(veh)
            count += 1

        for pltnID, vehs in toRemove.items():
            pltn = self._platoons[pltnID]
            pltn.removeVehicles(vehs)
            if pltn.size() == 0:
                # remove empty platoons
                self._platoons.pop(pltn.getID())

        # Re-add removed cars (both normal & platoon) into the system
        # Returns a list of ids of arrived vehicles (reached their destination and removed from the road network)
        # for ID in traci.simulation.getArrivedIDList():
        #     # The only way to distinguish the type of arrived car is to look at its id
        #     # vehID is either "normal-car-idx" or "platoon-car-pltnidx", see _addNormalVehicle & _addPlatoonVehicle
        #     if "platoon" in ID:
        #         self._addPlatoonVehicle()
        #     else:
        #         self._addNormalVehicle()

        return count

    def _manageFollowers(self):
        '''_manageFollowers()
        Iterates over platoon-followers and
        1) checks whether a Platoon has to be split due to incoherence persisting over some time
        '''
        newPlatoons = []
        for pltnID, pltn in self._platoons.items():
            # additional metric: in each tick, push number of cars in a platoon (excluding single ones)
            if len(pltn.getVehicles()) > 1:
                self.NumberOfCarsInPlatoons.append(len(pltn.getVehicles()))
            # encourage all vehicles to adopt the current mode of the platoon
            # NOTE: for switching between platoon modes, there may be vehicles not
            #       complying immediately. They are asked to do so, here in each turn.
            pltn.adviseMemberModes()
            # splitIndices: indices of vehicles that request a split
            splitIndices = []
            for ix, veh in enumerate(pltn.getVehicles()[1:]):
                # check whether to split the platoon at index ix
                leaderInfo = veh.state.leaderInfo

                if leaderInfo is None:
                    # no leader or no leader that allows platooning
                    print("case 1: no leader or no leader that allows platooning")
                    veh.setSplitConditions(True)
                elif not self._isConnected(leaderInfo[0]):
                    print("case 2: leader is not connected id: '%s'", leaderInfo[0])
                    veh.setSplitConditions(True)
                elif leaderInfo[1] > self._maxPlatoonGap:
                    print("case 3: leader is too far '%s' > '%s'", leaderInfo[1], self._maxPlatoonGap)
                    veh.setSplitConditions(True)
                else:
                    # ego has a connected leader
                    leaderID = leaderInfo[0]
                    leader = self._connectedVehicles[leaderID]
                    if pltn.getVehicles()[ix] == leader:
                        # ok, this is really the leader as registered in the platoon
                        veh.setSplitConditions(False)
                        veh.resetSplitCountDown()
                    elif leader.getPlatoon() == veh.getPlatoon():
                        # the platoon order is violated.
                        if rp.VERBOSITY >= 2:
                            report(("Platoon order for platoon '%s' is violated: real leader '%s' is not registered " +
                                    "as leader of '%s', actual leader of '%s' is '%s'") % (
                                       pltnID, leaderID, veh.getID(), veh.getID(), veh.state.leaderInfo[0]), 1)
                        print("leaderID:", leader.getID(), str([veh.getID() for veh in leader.getPlatoon().getVehicles()]))
                        veh.setSplitConditions(False)
                    else:
                        # leader is connected but belongs to a different platoon
                        print("++++++++++++++++++ \n")
                        print("case 4: leader is connected but belongs to a different platoon. \n")
                        print("veh-platoonID:", veh.getPlatoon().getID(), "leader-platoonID:", leader.getPlatoon().getID(), "\n")
                        print("leaderID:", leader.getID(),
                              "platoonID of leader:", leader.getPlatoon().getID(),
                              "vehicles in leader's platoon:", str([veh.getID() for veh in leader.getPlatoon().getVehicles()]), "\n")
                        print("vehicleID:", veh.getID(),
                              "platoonID of vehicle:", veh.getPlatoon().getID(),
                              "vehicles in vehicle's platoon:", str([veh.getID() for veh in veh.getPlatoon().getVehicles()]))
                        print("++++++++++++++++++ \n")
                        veh.setSplitConditions(True)
                if veh.splitConditions():
                    # eventually increase isolation time
                    timeUntilSplit = veh.splitCountDown(self._timeSinceLastControl)
                    if timeUntilSplit <= 0:
                        splitIndices.append(ix + 1)
            # try to split at the collected splitIndices
            for ix in reversed(splitIndices):
                newPlatoon = pltn.split(ix)
                if newPlatoon is not None:
                    # if the platoon was split, register the splitted platoons
                    newPlatoons.append(newPlatoon)
                    if rp.VERBOSITY >= 2:
                        report("Platoon '%s' splits (ID of new platoon: '%s'):\n" % (pltn.getID(), newPlatoon.getID()) +
                               "    Platoon '%s': %s\n    Platoon '%s': %s" % (
                                   pltn.getID(), str([veh.getID() for veh in pltn.getVehicles()]),
                                   newPlatoon.getID(), str([veh.getID() for veh in newPlatoon.getVehicles()])))
                    self.remove_from_pairwise_platoons(pltn, newPlatoon)
        for pltn in newPlatoons:
            self._platoons[pltn.getID()] = pltn

    def _manageLeaders(self):
        '''_manageLeaders()
        Iterates over platoon-leaders and
        1) checks whether two platoons (including "one-vehicle platoons") may merge for being sufficiently close
        2) advises platoon-leaders to try to catch up with a platoon in front
        '''
        # list of platoon ids that merged into another platoon
        toRemove = []
        for pltnID, pltn in self._platoons.items():
            # platoon leader
            pltnLeader = pltn.getLeader()
            # try setting back mode to regular platoon mode if leader is kept in FOLLOWER mode due to safety reasons
            # or if the ordering within platoon changed
            if pltnLeader.getCurrentPlatoonMode() == PlatoonMode.FOLLOWER:
                pltn.setModeWithImpatience(PlatoonMode.LEADER, self._controlInterval)
            elif pltnLeader.getCurrentPlatoonMode() == PlatoonMode.CATCHUP_FOLLOWER:
                pltn.setModeWithImpatience(PlatoonMode.CATCHUP, self._controlInterval)
            # get leader of the leader
            leaderInfo = pltnLeader.state.leaderInfo

            if leaderInfo is None or leaderInfo[1] > self._catchupDist:
                # No other vehicles ahead
                # reset vehicle types (could all have been in catchup mode)
                if pltn.size() == 1:
                    pltn.setModeWithImpatience(PlatoonMode.NONE, self._controlInterval)
                else:
                    # try to set mode to regular platoon mode
                    pltn.setModeWithImpatience(PlatoonMode.LEADER, self._controlInterval)
                continue

            if not self._isConnected(leaderInfo[0]):
                # Immediate leader is not connected
                if pltnLeader.state.connectedVehicleAhead:
                    # ... but further downstream there is a potential platooning partner
                    pltn.setModeWithImpatience(PlatoonMode.CATCHUP, self._controlInterval)
                elif pltn.size() == 1:
                    pltn.setModeWithImpatience(PlatoonMode.NONE, self._controlInterval)
                else:
                    # try to set mode to regular platoon mode
                    pltn.setModeWithImpatience(PlatoonMode.LEADER, self._controlInterval)
                continue

            # leader vehicle
            leaderID, leaderDist = leaderInfo
            leader = self._connectedVehicles[leaderID]

            # Commented out -> isLastInPlatoon should not be a hindrance to join platoon
            # tryCatchup = leader.isLastInPlatoon() and leader.getPlatoon() != pltn
            # join = tryCatchup and leaderDist <= self._maxPlatoonGap

            # Check if leader is on pltnLeader's route
            # (sometimes a 'linkLeader' on junction is returned by traci.getLeader())
            # XXX: This prevents joining attempts on internal lanes (probably doesn't hurt so much)
            pltnLeaderRoute = traci.vehicle.getRoute(pltnLeader.getID())
            pltnLeaderRouteIx = traci.vehicle.getRouteIndex(pltnLeader.getID())
            leaderEdge = leader.state.edgeID

            # if leaderArrivalPos is not within arrivalInterval (type tuple = (min, max)) of platoon
            # and if their journey do not end in the same edge, they won't merge
            leaderArrivalPos = leader.arrivalPos
            pltnArrivalInterval = pltnLeader.getPlatoon().getArrivalInterval()
            leadersArrivalEdge = leader.arrivalEdge
            pltnLeaderLastEdgeID = pltnLeaderRoute[-1]

            # usual simpla logic
            if leaderEdge not in pltnLeaderRoute[pltnLeaderRouteIx:]:
                continue

            if leader.getPlatoon() == pltn:
                # Platoon order is corrupted, don't join own platoon.
                continue

            if leadersArrivalEdge != pltnLeaderLastEdgeID:
                continue

            if leaderArrivalPos < pltnArrivalInterval[0] or leaderArrivalPos > pltnArrivalInterval[1]:
                continue

            # print("pltnLeaderLastEdgeID", pltnLeaderLastEdgeID, "pltnArrivalInterval", pltnArrivalInterval, "leadersArrivalEdge", leadersArrivalEdge, "leaderArrivalPos", leaderArrivalPos)

            if leaderDist <= self._maxPlatoonGap:
                # introducing number of vehicles in platoon logic
                nrOfVehiclesCondition = (len(leader.getPlatoon().getVehicles()) + len(pltn.getVehicles())) <= self.maxVehiclesInPlatoon
                # print("number of vehicles in leader's platoon", len(leader.getPlatoon().getVehicles()), " number of vehicles in platoon to join", len(pltn.getVehicles()), "res", nrOfVehiclesCondition)
                print("**************")
                if nrOfVehiclesCondition == True:
                    # Try to join the platoon in front
                    if leader.getPlatoon().join(pltn):
                        toRemove.append(pltnID)
                        # Debug
                        if rp.VERBOSITY >= 2:
                            report("Platoon '%s' joined Platoon '%s', which now contains " % (pltn.getID(),
                                                                                              leader.getPlatoon().getID()) +
                                   "vehicles:\n%s " % str([(veh.getID(), veh.getPlatoon().getID()) for veh in leader.getPlatoon().getVehicles()]))
                        self.add_to_pairwise_platoons(leader.getPlatoon(), pltn)
                        continue
                    else:
                        if rp.VERBOSITY >= 2:
                            report("Merging of platoons '%s' (%s) and '%s' (%s) would not be safe." %
                                   (pltn.getID(), str([veh.getID() for veh in pltn.getVehicles()]),
                                    leader.getPlatoon().getID(),
                                    str([veh.getID() for veh in leader.getPlatoon().getVehicles()])))
                else:
                    # Join failed due to number of cars in platoon. Do not change pltn behavior.
                    if rp.VERBOSITY >= 2:
                        report("Merging of platoons '%s' (%s) and '%s' (%s) failed due to number of vehicles limitation" %
                               (pltn.getID(), str([veh.getID() for veh in pltn.getVehicles()]),
                                leader.getPlatoon().getID(),
                                str([veh.getID() for veh in leader.getPlatoon().getVehicles()])))
                    continue
            else:
                # Join failed due to too large distance. Try to get closer (change to CATCHUP mode).
                if not pltn.setMode(PlatoonMode.CATCHUP):
                    if rp.VERBOSITY >= 2:
                        report(("Switch to catchup mode would not be safe for platoon '%s' (%s) chasing " +
                                "platoon '%s' (%s).") %
                               (pltn.getID(), str([veh.getID() for veh in pltn.getVehicles()]),
                                leader.getPlatoon().getID(),
                                str([veh.getID() for veh in leader.getPlatoon().getVehicles()])))

        # remove merged platoons
        for pltnID in toRemove:
            self._platoons.pop(pltnID)

    def _updatePlatoonOrdering(self):
        '''_manageLeaders()
        Iterates through platoons and checks whether they are in an appropriate order.
        '''
        if rp.VERBOSITY >= 4:
            report("Checking platoon ordering")

        for pltnID, pltn in self._platoons.items():
            if pltn.size() == 1:
                continue
            # collect leaders within platoon
            intraPlatoonLeaders = []
            leaderID = None
            for ix, veh in enumerate(pltn.getVehicles()):
                leaderFromeSamePlatoon = False
                if veh.state.leaderInfo is not None:
                    # leader detected
                    leaderID = veh.state.leaderInfo[0]
                    if self._isConnected(leaderID):
                        # leader is connected
                        leader = self._connectedVehicles[leaderID]
                        if leader.getPlatoon() == pltn:
                            # leader belongs to same platoon
                            leaderFromeSamePlatoon = True
                            intraPlatoonLeaders.append(leader)

                if not leaderFromeSamePlatoon:
                    intraPlatoonLeaders.append(None)

                if rp.VERBOSITY >= 4:
                    report("Platoon %s: Leader for veh '%s' is '%s' (%s)"
                           % (pltn.getID(), veh.getID(), str(leaderID),
                              ("same platoon" if (intraPlatoonLeaders[-1] is not None) else "not from same platoon")),
                           3)

            pltn.setVehicles(self.reorderVehicles(pltn.getVehicles(), intraPlatoonLeaders))

    @staticmethod
    def reorderVehicles(vehicles, actualLeaders):
        '''
        reorderVehicles(list(pVehicle), list(pVehicle)) -> list(pVehicle)
        This method reorders the given vehicles such that the newly ordered vehicles fulfill:
        [None] + vehicles[:-1] == actualLeaders (if not several vehicles have the same actual leader.
        For those it is only guaranteed that one will be associated correctly, not specifying which one)
        '''

        #         if rp.VERBOSITY >= 4:
        #             report("reorderVehicles(vehicles, actualLeaders)\nvehicles = %s\nactualLeaders=%s" %
        #                    (rp.array2String(vehicles), rp.array2String(actualLeaders)), 3)

        done = False
        # this is needed as abort criterion if two have the same leader (This cannot be excluded for sublane at least)
        iter_count = 0
        nVeh = len(vehicles)
        # make a copy to write into
        actualLeaders = list(actualLeaders)
        while(not done and iter_count < nVeh):
            newVehOrder = None
            registeredLeaders = [None] + vehicles[:-1]
            if rp.VERBOSITY >= 4:
                report("vehicles: %s" % rp.array2String(vehicles), 3)
                report("Actual leaders: %s" % rp.array2String(actualLeaders), 3)
                report("registered leaders: %s" % rp.array2String(registeredLeaders), 3)
            for (ego, registeredLeader, actualLeader) in reversed(
                    list(zip(vehicles, registeredLeaders, actualLeaders))):
                if (ego == actualLeader):
                    if rp.VERBOSITY >= 1:
                        warn(("Platoon %s:\nVehicle '%s' was found as its own leader. " +
                              "Platoon order might be corrupted.") % (
                                 rp.array2String(vehicles), str(ego)))
                    return vehicles

                if actualLeader is None:
                    # No actual leader was found. Could be due to platoon LC maneuver or non-connected vehicle
                    # merging in
                    # -> no reordering implications.
                    continue
                if actualLeader == registeredLeader:
                    continue

                # intra-platoon order is corrupted
                if newVehOrder is None:
                    # init newVehOrder
                    newVehOrder = list(vehicles)

                # relocate ego

                if rp.VERBOSITY >= 4:
                    report("relocating: %s to follow %s" % (str(ego), str(actualLeader)), 3)
                    report("prior newVehOrder: %s" % rp.array2String(newVehOrder), 3)
                    report("prior actualLeaders: %s" % rp.array2String(actualLeaders), 3)
                oldEgoIndex = newVehOrder.index(ego)
                del newVehOrder[oldEgoIndex]
                del actualLeaders[oldEgoIndex]

                if rp.VERBOSITY >= 4:
                    report("immed newVehOrder: %s" % rp.array2String(newVehOrder), 3)
                    report("immed actualLeaders: %s" % rp.array2String(actualLeaders), 3)
                actualLeaderIndex = newVehOrder.index(actualLeader)
                newVehOrder.insert(actualLeaderIndex + 1, ego)
                actualLeaders.insert(actualLeaderIndex + 1, actualLeader)
                if rp.VERBOSITY >= 4:
                    report("current newVehOrder: %s" % rp.array2String(newVehOrder), 3)
                    report("current actualLeaders: %s" % rp.array2String(actualLeaders), 3)

            done = newVehOrder is None
            if not done:
                vehicles = newVehOrder
                iter_count += 1

        if iter_count != 0:
            if rp.VERBOSITY >= 3:
                report("Ordering within Platoon %s was corrupted.\nNew Order: %s\nLeaders: %s" %
                       (vehicles[0].getPlatoon().getID(), rp.array2String(vehicles), rp.array2String(actualLeaders)), 3)

        return vehicles

    def _adviseLanes(self):
        '''_adviseLanes()
        At the moment this only advises all platoon followers to change to their leaders lane
        if it is on a different lane on the same edge. Otherwise, followers are told to keep their
        lane for the next time step.
        NOTE: Future, more sophisticated lc advices should go here.
        '''
        for pltn in self._platoons.values():
            for ix, veh in enumerate(pltn.getVehicles()[1:]):
                laneID = veh.state.laneID
                if laneID == "" or laneID[0] == ":":
                    continue
                # Find the leader in the platoon and request a lanechange if appropriate
                leader = pltn.getVehicles()[ix]
                if leader.state.edgeID == veh.state.edgeID:
                    # leader is on the same edge, advise follower to use the same lane
                    try:
                        traci.vehicle.changeLane(veh.getID(), leader.state.laneIX, int(self._controlInterval * 1000))
                    except traci.exceptions.TraCIException as e:
                        if rp.VERBOSITY >= 1:
                            warn("Lanechange advice for vehicle'%s' failed. Message:\n%s" % (veh.getID(), e.message))
                else:
                    # leader is on another edge, just stay on the current and hope it is the right one
                    try:
                        traci.vehicle.changeLane(veh.getID(), veh.state.laneIX, int(self._controlInterval * 1000))
                    except traci.exceptions.TraCIException as e:
                        if rp.VERBOSITY >= 1:
                            warn("Lanechange advice for vehicle'%s' failed. Message:\n%s" % (veh.getID(), e.message))

    def _isConnected(self, vehID):
        '''_isConnected(string) -> bool
        Returns whether the given vehicle is a potential platooning participant
        '''
        if vehID in self._connectedVehicles:
            return True
        else:
            return False

    def _hasConnectedType(self, vType):
        '''_hasConnectedType(vType) -> bool

        Determines whether the given vType & its vehicle should be connected to the platoon manager
        by comparing vType with the type selector substrings specified in vehicleSelectors.
        '''
        for selector_str in self._typeSubstrings:
            if selector_str in vType:
                return True
        return False

    def applyCarCounter(self):

        """ add normal car into the system """
        while self.carIndex < self.totalCarCounter - self.platoonCarCounter:
            self._addNormalVehicle()

        """ add platooning car into the system """
        while len(self._connectedVehicles) < self.platoonCarCounter:
            self._addPlatoonVehicle()

    def _addNormalVehicle(self):
        vehID = "normal-car-" + str(self.carIndex)
        typeID = "normal-car" # must be same with <vType> id in flow.rou.xml if used
        routeID = "normal-car-route-" + str(self.carIndex)
        rnd_edge = Config.get_random().choice(Config.edgeIDsForExit)
        edges = traci.simulation.findRoute(fromEdge=Config.startEdgeID, toEdge=rnd_edge).edges
        traci.route.add(routeID, edges)

        # TODO: hard-coded lane numbers, there should be getLaneNumber(edgeID) method in edge,
        # TODO: but there's no such fcn in current version
        # see: http://www.sumo.dlr.de/daily/pydoc/traci._edge.html#EdgeDomain-getLaneNumber
        # laneNumbers = traci.edge.getLaneNumber("12N")
        laneNumbers = [0, 1, 2, 3]

        # TODO: remove in production
        # random.seed(0)

        arrivalLane = str(Config.get_random().choice(laneNumbers))
        traci.vehicle.addFull(vehID=vehID, routeID=routeID, typeID='DEFAULT_VEHTYPE', depart=str(simTime()), departLane='random', departPos='base', departSpeed='0', arrivalLane=arrivalLane, arrivalPos='random')

        self.carIndex += 1

    def _addPlatoonVehicle(self):
        '''_addPlatoonVehicle()

        Creates a new PVehicle object for platooning and registers is soliton platoon
        It filters out car types that are not related with platooning logic to ensure a valid platooning car addition to simulation
        '''
        # try:
        # Returns a list of ids of currently loaded vehicle types
        knownVTypes = traci.vehicletype.getIDList()
        knownVTypes.remove("DEFAULT_PEDTYPE")
        knownVTypes.remove("DEFAULT_VEHTYPE")
        # knownVTypes.remove("normal-car")
        # print("knownVTypes", knownVTypes)
        vType = Config.get_random().choice(knownVTypes)

        # register car within the platooning manager if randomly selected type is specialized for platooning
        # other vehicles are already started moving according to defined flow(s)
        if self._hasConnectedType(vType):
            vehID = "platoon-car-" + str(self.carIndex)
            veh = _pvehicle.PVehicle(vehID, simTime())
            routeID = "platoon-car-route-" + str(self.carIndex)
            traci.route.add(routeID, veh.edgesToTravel)
            traci.vehicle.addFull(vehID=vehID, routeID=routeID, typeID=vType, depart=str(simTime()), departLane='random', departPos='base', departSpeed='0', arrivalPos=str(veh.arrivalPos))
            traci.vehicle.setColor(vehID=vehID, color=(255, 255, 255, 255))
            valid = traci.vehicle.isRouteValid(vehID=vehID)
            if valid:
                veh.setState(self._controlInterval)
                # Subscribe according to new metrics http://sumo.dlr.de/wiki/TraCI/Vehicle_Value_Retrieval
                traci.vehicle.subscribe(vehID,
                                        (tc.VAR_ROAD_ID,
                                         tc.VAR_LANE_INDEX,
                                         tc.VAR_LANE_ID,
                                         tc.VAR_SPEED,
                                         tc.VAR_LANEPOSITION,
                                         tc.VAR_FUELCONSUMPTION))
                if rp.VERBOSITY >= 3:
                    report("Adding vehicle '%s', routeID: '%s', vType:'%s'" % (vehID, routeID, vType))
                self._connectedVehicles[vehID] = veh
                self._platoons[veh.getPlatoon().getID()] = veh.getPlatoon()
                self.carIndex += 1
                return veh
            else:
                report("Route of vehicle '%s' is not valid" % vehID)
                return None
        else:
            raise Exception
        # except TraCIException as traci_exception:
        #     traceback.print_exc()
        #     raise traci_exception
        # except KeyError as e:
        #     raise e

    def get_statistics(self):
        config = dict(
            switchImpatienceFactor=Config.parameters["contextual"]["switchImpatienceFactor"],
            lookAheadDistance=Config.parameters["contextual"]["lookAheadDistance"],
            platoonCarCounter=Config.parameters["contextual"]["platoonCarCounter"],
            totalCarCounter=Config.parameters["contextual"]["totalCarCounter"],

            catchupDistance=Config.parameters["changeable"]["catchupDistance"],
            maxPlatoonGap=Config.parameters["changeable"]["maxPlatoonGap"],
            maxVehiclesInPlatoon=Config.parameters["changeable"]["maxVehiclesInPlatoon"],
            platoonSplitTime=Config.parameters["changeable"]["platoonSplitTime"],
            joinDistance=Config.parameters["changeable"]["joinDistance"]
        )

        data = dict(
            TripDurations=self.TripDurations,
            FuelConsumptions=self.FuelConsumptions,
            Speeds=self.Speeds,
            Overheads=self.Overheads,
            NumberOfCarsInPlatoons=self.NumberOfCarsInPlatoons,
            ReportedPlatoonDurationsBeforeSplit=self.ReportedPlatoonDurationsBeforeSplit
        )

        res = dict(
            simTime=simTime(),
            config=config,
            data=data,
        )
        # if required, total number of trips can be obtained with len(TripDurations)

        return res

    def _updateStatistics(self, veh):
        # maxSpeed = 44.44 # by observation, maxAllowedSpeed is same for all major lanes in highway
        # as indicated in _setActiveSpeedFactor() method:
        # vehicles' maxSpeed determines determines travel speed, not road's speed limit
        maxSpeed = veh.state.maxSpeed
        theoreticalDuration = veh.state.distance / (maxSpeed * 1.0)
        actualDuration = simTime() - veh.currentRouteBeginTime
        overhead = actualDuration / theoreticalDuration
        # print("veh.state.distance", veh.state.distance, "actualDuration", actualDuration, "theoreticalDuration", theoreticalDuration, "overhead", overhead, "+++++++++")

        self.TripDurations.append(actualDuration)
        self.FuelConsumptions.extend(veh.state.reportedFuelConsumptions)
        self.Speeds.extend(veh.state.reportedSpeeds)
        self.Overheads.append(overhead)
        self.TimeSpentInsidePlatoon.append(veh.state.durationInsidePlatoon / (veh.state.durationOutsidePlatoon * 1.0) )

    def _endSimulation(self):
        import app.simulation.PlatoonSimulation as ps
        if simTime() % Config.nrOfTicks == 0:
            ps.simulationEnded = True


    def add_to_pairwise_platoons(self, leadingPlatoon, joiningPlatoon):
        # here, leadingPlatoon already contains vehicles of joiningPlatoon, as this fcn is called after .join(pltn)
        # so if clause is added to the inner loop
        cars_IDs_in_leading_platoon = [veh.getID() for veh in leadingPlatoon.getVehicles()]
        cars_IDs_in_joining_platoon = [veh.getID() for veh in joiningPlatoon.getVehicles()]

        for first_carID in cars_IDs_in_leading_platoon:
            for second_carID in cars_IDs_in_joining_platoon:
                if first_carID != second_carID:
                    pwp = PWP(first_carID=first_carID, second_carID=second_carID)
                    self.pairwise_platoons[pwp] = simTime()
        # print("self.pairwise_platoons add", self.pairwise_platoons)
        # print("+++++++++++++++++++")

    def remove_from_pairwise_platoons(self, leadingPlatoon, splittedPlatoon):
        tpls_to_be_removed = []

        for veh1 in leadingPlatoon.getVehicles():
            for veh2 in splittedPlatoon.getVehicles():
                # this restriction is needed to avoid key errors when we want to remove vehicle(s) that arrive their destinations
                # as remove_from_pairwise_platoons() is called before the actual removal (pltn.removeVehicles(vehs))
                # i.e. pltn still contains vehs to be removed
                if veh1.getID() != veh2.getID():
                    tpls_to_be_removed.append((veh1.getID(), veh2.getID()))

        # print("removing pltnID: ", splittedPlatoon.getID(), " leadingPltnID: ", leadingPlatoon.getID(), " tpls_to_be_removed", tpls_to_be_removed)
        # print("before removal", self.pairwise_platoons)

        # in some cases, order of keys must be reversed, due to internal reordering of vehicles
        for tpl in tpls_to_be_removed:
            pwp = PWP(first_carID=tpl[0], second_carID=tpl[1])
            reversed = PWP(first_carID=tpl[1], second_carID=tpl[0])

            if pwp in self.pairwise_platoons.keys():
                tick = self.pairwise_platoons[pwp]
                if tick is not None:
                    self.ReportedPlatoonDurationsBeforeSplit.append(simTime() - tick)
                self.pairwise_platoons.pop(pwp)

            elif reversed in self.pairwise_platoons.keys():
                tick = self.pairwise_platoons[reversed]
                if tick is not None:
                    self.ReportedPlatoonDurationsBeforeSplit.append(simTime() - tick)
                self.pairwise_platoons.pop(reversed)
            else:
                print("given tuple should not be in the dict")
                exit(0)
        # print("self.pairwise_platoons remove", self.pairwise_platoons)
        # print("-----------------------")
