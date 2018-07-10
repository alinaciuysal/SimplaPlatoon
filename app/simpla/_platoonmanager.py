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

from _exceptions import SimplaException
from traci.exceptions import TraCIException
from _platoonmode import PlatoonMode
from _collections import defaultdict

import _config as cfg
import _reporting as rp
import _pvehicle
import _platoon
import traci
import traci.constants as tc
import app.Config as Config
import random, traceback, os.path, json

from app.simpla._reporting import simTime
from app.streaming import KafkaForword, KafkaConnector

warn = rp.Warner("PlatoonManager")
report = rp.Reporter("PlatoonManager")


_destinations = {}

class PlatoonManager(traci.StepListener):

    '''
    A PlatoonManager coordinates the initialization of platoons
    and adapts the vehicles in a platoon to change their controls accordingly.
    To use it, create a PlatoonManager and call its update() method in each
    simulation step.
    Do not create more than one PlatoonManager, if you cannot guarantee that
    the associated vehicle types are exclusive for each.
    '''

    edges = []
    tick = None

    # keeps track of added vehicles with this index
    carIndex = None
    platoonCarCounter = None
    totalCarCounter = None

    # parameters to be used as output
    nrOfPlatoonsFormed = None
    nrOfPlatoonsSplit = None

    # number of simulation ticks that does not include durations of platoons with single vehicle
    overallPlatoonDuration = None

    TripDurations = None
    CO2Emissions = None
    COEmissions = None
    HCEmissions = None
    PMXEmissions = None
    NOxEmissions = None
    FuelConsumptions = None
    NoiseEmissions = None
    Speeds = None



    def __init__(self):
        ''' PlatoonManager()

        Creates and initializes the PlatoonManager
        '''

        self.carIndex = 0
        self.platoonCarCounter = Config.platoonCarCounter
        self.totalCarCounter = Config.totalCarCounter

        self.nrOfPlatoonsFormed = 0
        self.nrOfPlatoonsSplit = 0
        self.overallPlatoonDuration = 0

        self.TripDurations = []
        self.CO2Emissions = []
        self.COEmissions = []
        self.HCEmissions = []
        self.PMXEmissions = []
        self.NOxEmissions = []
        self.FuelConsumptions = []
        self.NoiseEmissions = []
        self.Speeds = []

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

        # integration step-length
        self._DeltaT = traci.simulation.getDeltaT() / 1000.

        # rate for executing the platoon logic
        if 1. / cfg.CONTROL_RATE < self._DeltaT:
            if rp.VERBOSITY >= 1:
                warn("Restricting given control rate (= %d per sec.) to 1 per timestep (= %g per sec.)" % (cfg.CONTROL_RATE, 1./self._DeltaT), True)
            self._controlInterval = self._DeltaT
        else:
            self._controlInterval = 1. / cfg.CONTROL_RATE

        self._timeSinceLastControl = 1000.
        self.tick = simTime()


        # Check for undefined vtypes and fill with defaults
        for origType, specialTypes in cfg.PLATOON_VTYPES.items():
            if specialTypes[PlatoonMode.FOLLOWER] is None:
                if rp.VERBOSITY>=2:
                    report("Setting unspecified follower vtype for '%s' to '%s'"%(origType, specialTypes[PlatoonMode.LEADER]),True)
                specialTypes[PlatoonMode.FOLLOWER] = specialTypes[PlatoonMode.LEADER]
            if specialTypes[PlatoonMode.CATCHUP] is None:
                if rp.VERBOSITY>=2:
                    report("Setting unspecified catchup vtype for '%s' to '%s'"%(origType, origType),True)
                specialTypes[PlatoonMode.CATCHUP] = origType
            if specialTypes[PlatoonMode.CATCHUP_FOLLOWER] is None:
                if rp.VERBOSITY>=2:
                    report("Setting unspecified catchup-follower vtype for '%s' to '%s'"%(origType, specialTypes[PlatoonMode.FOLLOWER]),True)
                specialTypes[PlatoonMode.CATCHUP_FOLLOWER]=specialTypes[PlatoonMode.FOLLOWER]
                ## Commented snippet generated automatically a catchup follower type with a different color
                catchupFollowerType = origType + "_catchupFollower"
                specialTypes[PlatoonMode.CATCHUP] = catchupFollowerType
                if rp.VERBOSITY >= 2:
                    print("Catchup follower type '%s' for '%s' dynamically created as duplicate of '%s'" %
                      (catchupFollowerType, origType, specialTypes[PlatoonMode.CATCHUP_FOLLOWER]))
                # copy(self, origTypeID, newTypeID) documentation:
                # Duplicates the vType with ID origTypeID. The newly created vType is assigned the ID newTypeID
                traci.vehicletype.copy(specialTypes[PlatoonMode.CATCHUP_FOLLOWER], catchupFollowerType)
                traci.vehicletype.setColor(catchupFollowerType, (0, 255, 200, 0))

        # fill global lookup table for vType parameters (used below in safetycheck)
        knownVTypes = traci.vehicletype.getIDList()
        for origType, mappings in cfg.PLATOON_VTYPES.items():
            if origType not in knownVTypes:
                raise SimplaException("vType '%s' is unknown to sumo! Note: Platooning vTypes must be defined at startup." % origType)
            origLength = traci.vehicletype.getLength(origType)
            origEmergencyDecel = traci.vehicletype.getEmergencyDecel(origType)
            for typeID in list(mappings.values()) + [origType]:
                if typeID not in knownVTypes:
                    raise SimplaException("vType '%s' is unknown to sumo! Note: Platooning vTypes must be defined at startup." % typeID)
                mappedLength = traci.vehicletype.getLength(typeID)
                mappedEmergencyDecel = traci.vehicletype.getEmergencyDecel(typeID)
                if origLength != mappedLength:
                    if rp.VERBOSITY>=1:
                        warn("length of mapped vType '%s' (%sm.) does not equal length of original vType '%s' (%sm.)\nThis will probably lead to collisions." % (
                        typeID, mappedLength, origType, origLength), True)
                if origEmergencyDecel != mappedEmergencyDecel:
                    if rp.VERBOSITY>=1:
                        warn("emergencyDecel of mapped vType '%s' (%gm.) does not equal emergencyDecel of original vType '%s' (%gm.)" % (
                        typeID, mappedEmergencyDecel, origType, origEmergencyDecel), True)
                _pvehicle.vTypeParameters[typeID][tc.VAR_TAU] = traci.vehicletype.getTau(typeID)
                _pvehicle.vTypeParameters[typeID][tc.VAR_DECEL] = traci.vehicletype.getDecel(typeID)
                _pvehicle.vTypeParameters[typeID][tc.VAR_MINGAP] = traci.vehicletype.getMinGap(typeID)
                _pvehicle.vTypeParameters[typeID][tc.VAR_EMERGENCY_DECEL] = traci.vehicletype.getEmergencyDecel(typeID)

        self.edges = traci.simulation.findRoute(fromEdge=Config.startEdgeID, toEdge=Config.endEdgeID).edges

        warn("end of platoon manager", True)

    def step(self, t=0):
        '''step(int)

        Manages platoons at each time step.
        NOTE: argument t is unused, larger step sizes than DeltaT are not supported.
        '''

        if not t == 0 and rp.VERBOSITY >= 1:
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
            self._timeSinceLastControl = 0
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
            veh.state.lanePosition = self._subscriptionResults[veh.getID()][tc.VAR_LANEPOSITION]
            veh.state.leaderInfo = traci.vehicle.getLeader(veh.getID(), self._catchupDist)

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
                veh.state.reportedCO2Emissions.append(CO2Emission)

            if COEmission > 0:
                veh.state.reportedCOEmissions.append(COEmission)

            if HCEmission > 0:
                veh.state.reportedHCEmissions.append(HCEmission)

            if PMXEmission > 0:
                veh.state.reportedPMXEmissions.append(PMXEmission)

            if NOxEmission > 0:
                veh.state.reportedNOxEmissions.append(NOxEmission)

            if FuelConsumption > 0:
                veh.state.reportedFuelConsumptions.append(FuelConsumption)

            if NoiseEmission > 0:
                veh.state.reportedNoiseEmissions.append(NoiseEmission)

            if veh.state.speed > 0:
                veh.state.reportedSpeeds.append(veh.state.speed)

            if veh.state.leaderInfo is None:
                veh.state.leader = None
                veh.state.connectedVehicleAhead = False
                continue

            # try to find a connected leader within the provided distance
            # this case is special when there's a non-connected car in front of veh, but there's a leader in front of non-connected car and it's within the catchupDist
            if veh.state.leader is None or veh.state.leader.getID() != veh.state.leaderInfo[0]:
                leaderID = veh.state.leaderInfo[0]
                distanceBetweenLeader = veh.state.leaderInfo[1]
                if self._isConnected(leaderID):
                    veh.state.leader = self._connectedVehicles[leaderID]
                    veh.state.connectedVehicleAhead = True
                else:
                    # leader is not connected -> check whether a connected vehicle is located further downstream
                    veh.state.leader = None
                    veh.state.connectedVehicleAhead = False

                    # getLength returns the length of the given vehicle (in m)
                    dist = distanceBetweenLeader + traci.vehicle.getLength(leaderID)
                    while dist < self._catchupDist:
                        # http://www.sumo.dlr.de/daily/pydoc/traci._vehicle.html#VehicleDomain-getLeader
                        nextLeaderInfo = traci.vehicle.getLeader(leaderID, self._catchupDist - dist)
                        if nextLeaderInfo is None:
                            break
                        vehAheadID = nextLeaderInfo[0]
                        # TODO: investigate why gap is negative
                        if nextLeaderInfo[1] < 0:
                            break

                        if self._isConnected(vehAheadID):
                            veh.state.connectedVehicleAhead = True
                            if rp.VERBOSITY >= 4:
                                report("Found connected vehicle '%s' downstream of vehicle '%s' (at distance %s)" %
                                       (vehAheadID, veh.getID(), dist + nextLeaderInfo[1]))
                            break
                        dist += nextLeaderInfo[1] + traci.vehicle.getLength(vehAheadID)

    def _manageFollowers(self):
        '''_manageFollowers()

        Iterates over platoon-followers and
        1) checks whether a Platoon has to be split due to incoherence persisting over some time
        '''
        newPlatoons = []
        for pltnID, pltn in self._platoons.items():
            # encourage all vehicles to adopt the current mode of the platoon
            # NOTE: for switching between platoon modes, there may be vehicles not
            #       complying immediately. They are asked to do so, here in each turn.
            pltn.adviseMemberModes()
            # splitIndices: indices of vehicles that request a split
            splitIndices = []
            for ix, veh in enumerate(pltn.getVehicles()[1:]):
                # check whether to split the platoon at index ix
                leaderInfo = veh.state.leaderInfo
                if leaderInfo is None or not self._isConnected(leaderInfo[0]) or leaderInfo[1] > self._maxPlatoonGap:
                    # no leader or no leader that allows platooning
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
                            report("Platoon order for platoon '%s' is violated: real leader '%s' is not registered as leader of '%s'" % (
                                pltnID, leaderID, veh.getID()), 1)
                        veh.setSplitConditions(False)
                    else:
                        # leader is connected but belongs to a different platoon
                        veh.setSplitConditions(True)
                if veh.splitConditions():
                    # eventually increase isolation time
                    timeUntilSplit = veh.splitCountDown(self._timeSinceLastControl)
                    if timeUntilSplit <= 0:
                        splitIndices.append(ix + 1)
            # try to split at the collected splitIndices
            for ix in reversed(splitIndices):
                self.nrOfPlatoonsSplit += 1
                newPlatoon = pltn.split(ix)
                if newPlatoon is not None:
                    # if the platoon was split, register the splitted platoons and find its arrivalInterval
                    newPlatoon.adjustInterval()
                    newPlatoons.append(newPlatoon)
                    if rp.VERBOSITY >= 2:
                        report("Platoon '%s' splits (ID of new platoon: '%s'):\n" % (pltn.getID(), newPlatoon.getID()) +
                               "    Platoon '%s': %s\n    Platoon '%s': %s" % (pltn.getID(), str([veh.getID() for veh in pltn.getVehicles()]),
                                                                       newPlatoon.getID(), str([veh.getID() for veh in newPlatoon.getVehicles()])))
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
            # get leading vehicle of the leader
            # leaderInfo = (string = id of the leading vehicle, double = distance)
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

            # get leader vehicle
            leaderID, leaderDist = leaderInfo
            leader = self._connectedVehicles[leaderID]

            # Commented out -> isLastInPlatoon should not be a hindrance to join platoon
            # tryCatchup = leader.isLastInPlatoon() and leader.getPlatoon() != pltn
            # join = tryCatchup and leaderDist <= self._maxPlatoonGap

            # Check if leader is on pltnLeader's route
            # (sometimes a 'linkLeader' on junction is returned by traci.getLeader())
            # XXX: This prevents joining attempts on internal lanes (probably doesn't hurt so much)
            pltnLeaderRoute = traci.vehicle.getRoute(pltnLeader.getID())
            # index of the current edge within the vehicles route
            pltnLeaderRouteIx = traci.vehicle.getRouteIndex(pltnLeader.getID())
            leadersCurrentEdge = leader.state.edgeID
            leadersArrivalPos = leader.arrivalPos

            # DEPRECATED: edges from pltnLeaderRouteIx to the end
            # if leadersCurrentEdge not in pltnLeaderRoute[pltnLeaderRouteIx:]:
            #     continue

            leadersArrivalEdge = leader.arrivalEdge
            pltnLeaderLastEdgeID = pltnLeaderRoute[-1]
            # for now, we support only this case: "cars should form platoons if their route end in same edge"
            if leadersArrivalEdge != pltnLeaderLastEdgeID:
                continue

            if leader.getPlatoon() == pltn:
                # Platoon order is corrupted, don't join own platoon.
                continue

            # if arrivalPos is not within the range of platoon, it won't join (merge)
            pltnArrivalInterval = pltnLeader.getPlatoon().getArrivalInterval()
            # interval is always a tuple of (min, max)
            if leadersArrivalPos < pltnArrivalInterval[0] or leadersArrivalPos > pltnArrivalInterval[1]:
                continue

            gapCondition, nrOfVehiclesCondition = self.joiningConditionsSatisfied(leaderInfo, pltn)
            if gapCondition and nrOfVehiclesCondition:
                # Try to join the platoon in front (leader's platoon),
                # i.e. add vehicles of "pltn" to the end of leader's platoon
                if leader.getPlatoon().join(pltn):
                    self.nrOfPlatoonsFormed += 1
                    toRemove.append(pltnID)
                    leader.getPlatoon().adjustInterval()
                    print("joined: pltnArrivalInterval: ", pltnArrivalInterval,
                          " leadersArrivalPos", leadersArrivalPos,
                          " leadersArrivalInterval", leader.getArrivalInterval(),
                          " newInterval", leader.getPlatoon().getArrivalInterval())

                    # Debug
                    if rp.VERBOSITY >= 2:
                        report("Platoon '%s' joined Platoon '%s', which now contains " % (pltn.getID(), leader.getPlatoon().getID()) +
                               "vehicles:\n%s" % str([veh.getID() for veh in leader.getPlatoon().getVehicles()]))
                    continue
                else:
                    if rp.VERBOSITY >= 3:
                        report("Merging of platoons '%s' (%s) and '%s' (%s) would not be safe." % (pltn.getID(), str([veh.getID() for veh in pltn.getVehicles()]),
                                                                                                   leader.getPlatoon().getID(), str([veh.getID() for veh in leader.getPlatoon().getVehicles()])))
            else:
                # Join can fail due to different reasons:
                # 1) too large distance. Try to get closer (change to CATCHUP mode).
                if not gapCondition:
                    if not pltn.setMode(PlatoonMode.CATCHUP):
                        if rp.VERBOSITY >= 3:
                            report("Switch to catchup mode would not be safe for platoon '%s' (%s) chasing platoon '%s' (%s)." % (pltn.getID(), str([veh.getID() for veh in pltn.getVehicles()]),
                                                                                                                                                  leader.getPlatoon().getID(), str([veh.getID() for veh in leader.getPlatoon().getVehicles()])))
                # 2) numberOfVehicles in platoon is already too much.
                if not nrOfVehiclesCondition:
                    if not pltn.setMode(PlatoonMode.FOLLOWER):
                        if rp.VERBOSITY >= 3:
                            report("Switch to follower mode would not be safe for platoon '%s' (%s) chasing platoon '%s' (%s)." % (pltn.getID(), str([veh.getID() for veh in pltn.getVehicles()]),
                                                                                                                                  leader.getPlatoon().getID(), str([veh.getID() for veh in leader.getPlatoon().getVehicles()])))
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
            # increment duration for each platoon
            self.overallPlatoonDuration += 1

            # collect leaders within platoon
            intraPlatoonLeaders = []
            leaderID = None
            for ix, veh in enumerate(pltn.getVehicles()):
                leaderFromSamePlatoon = False
                if veh.state.leaderInfo is not None:
                    # leader detected
                    leaderID = veh.state.leaderInfo[0]
                    if self._isConnected(leaderID):
                        # leader is connected
                        leader = self._connectedVehicles[leaderID]
                        if leader.getPlatoon() == pltn:
                            # leader belongs to same platoon
                            leaderFromSamePlatoon = True
                            intraPlatoonLeaders.append(leader)

                if not leaderFromSamePlatoon:
                    intraPlatoonLeaders.append(None)

                if rp.VERBOSITY >= 4:
                    report("Platoon %s: Leader for veh '%s' is '%s' (%s)"
                           % (pltn.getID(), veh.getID(), str(leaderID), ("same platoon" if (intraPlatoonLeaders[-1] is not None) else "not from same platoon")), 3)

            pltn.setVehicles(self.reorderVehicles(pltn.getVehicles(), intraPlatoonLeaders))

    def _adviseLanes(self):
        '''_adviseLanes()

        At the moment this only advises all platoon followers to change to their leaders' lane
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
                        traci.vehicle.changeLane(veh.getID(), leader.state.laneIX, int(self._controlInterval*1000))
                    except traci.exceptions.TraCIException as e:
                        if rp.VERBOSITY>=1:
                            warn("Lanechange advice for vehicle'%s' failed. Message:\n%s" % (veh.getID(), e.message))
                else:
                    # leader is on another edge, just stay on the current and hope it is the right one
                    try:
                        traci.vehicle.changeLane(veh.getID(), veh.state.laneIX, int(self._controlInterval*1000))
                    except traci.exceptions.TraCIException as e:
                        if rp.VERBOSITY>=1:
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
        '''_hasConnectedType(string) -> bool

        Determines whether the given vehicle should be connected to the platoon manager
        by comparing the vType with the type selector substrings specified in vehicleSelectors of cfg.
        '''
        for selector_str in self._typeSubstrings:
            if selector_str in vType:
                return True
        return False

    def _updateStatistics(self, veh):
        tripDuration = simTime() - veh.currentRouteBeginTick
        self.TripDurations.append(tripDuration)
        self.CO2Emissions.extend(veh.state.reportedCO2Emissions)
        self.COEmissions.extend(veh.state.reportedCOEmissions)
        self.HCEmissions.extend(veh.state.reportedHCEmissions)
        self.PMXEmissions.extend(veh.state.reportedPMXEmissions)
        self.NOxEmissions.extend(veh.state.reportedNOxEmissions)
        self.FuelConsumptions.extend(veh.state.reportedFuelConsumptions)
        self.NoiseEmissions.extend(veh.state.reportedNoiseEmissions)
        self.Speeds.extend(veh.state.reportedSpeeds)

    def joiningConditionsSatisfied(self, leaderInfo, pltn):
        ''' returns two bool:
            1) if gap between leader and platoon is less than maxPlatoonGap
            2) if merge will not exceed maximum number of vehicles for each platoon
        '''
        leaderID, leaderDist = leaderInfo
        gapCondition = leaderDist <= self._maxPlatoonGap

        leader = self._connectedVehicles[leaderID]
        # check if number of maximum allowed vehicles in platoon will not be exceeded upon join
        nrOfVehiclesCondition = (len(leader.getPlatoon().getVehicles()) + len(pltn.getVehicles())) <= Config.maxVehiclesInPlatoon
        return gapCondition, nrOfVehiclesCondition

    @staticmethod
    def addToAverage(totalCount, totalValue, newValue):
        """ simple sliding average calculation """
        return ((1.0 * totalCount * totalValue) + newValue) / (totalCount + 1)

    @staticmethod
    def reorderVehicles(vehicles, actualLeaders):
        '''
        reorderVehicles(list(pVehicle), list(pVehicle)) -> list(pVehicle)

        This method reorders the given vehicles such that the newly ordered vehicles fulfill: [None] + vehicles[:-1] == actualLeaders
        (if not several vehicles have the same actual leader. For those it is only guaranteed that one will be associated correctly, not specifying which one)
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
        while not done and iter_count < nVeh:
            newVehOrder = None
            registeredLeaders = [None] + vehicles[:-1]
            if rp.VERBOSITY >= 4:
                report("vehicles: %s" % rp.array2String(vehicles), 3)
                report("Actual leaders: %s" % rp.array2String(actualLeaders), 3)
                report("registered leaders: %s" % rp.array2String(registeredLeaders), 3)
            for (ego, registeredLeader, actualLeader) in reversed(list(zip(vehicles, registeredLeaders, actualLeaders))):
                if ego == actualLeader:
                    if rp.VERBOSITY >= 1:
                        warn("Platoon %s:\nVehicle '%s' was found as its own leader. Platoon order might be corrupted." % (
                            rp.array2String(vehicles), str(ego)))
                    return vehicles

                if actualLeader is None:
                    # No actual leader was found. Could be due to platoon LC maneuver or non-connected vehicle merging in
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

    def applyCarCounter(self):

        """ add normal car into the system """
        while self.carIndex < self.totalCarCounter - self.platoonCarCounter:
            self._addNormalVehicle()

        """ add platooning car into the system """
        while len(self._connectedVehicles) < self.platoonCarCounter:
            self._addPlatoonVehicle()

    def _addPlatoonVehicle(self):
        '''_addPlatoonVehicle()

        Creates a new PVehicle object for platooning and registers is soliton platoon
        It filters out car types that are not related with platooning logic to ensure a valid platooning car addition to simulation
        '''
        try:
            # Returns a list of ids of currently loaded vehicle types
            knownVTypes = traci.vehicletype.getIDList()
            knownVTypes.remove("DEFAULT_PEDTYPE")
            knownVTypes.remove("DEFAULT_VEHTYPE")
            knownVTypes.remove("normal-car")
            vType = random.choice(knownVTypes)

            # register car within the platooning manager if randomly selected type is specialized for platooning
            # other vehicles are already started moving according to defined flow(s)
            if self._hasConnectedType(vType):
                vehID = "platoon-car-" + str(self.carIndex)
                veh = _pvehicle.PVehicle(ID=vehID, edges=self.edges, tick=simTime())
                routeID = "platoon-car-route-" + str(self.carIndex)
                traci.route.add(routeID, veh.edgesToTravel)
                traci.vehicle.addFull(vehID=vehID, routeID=routeID, typeID=vType, depart=str(simTime()), departLane='random', departPos='base', departSpeed='0', arrivalPos=str(veh.arrivalPos))
                traci.vehicle.setColor(vehID=vehID, color=(255, 255, 255, 255))
                valid = traci.vehicle.isRouteValid(vehID=vehID)
                if valid:
                    veh.setState(self._controlInterval)
                    # Subscribe according to new metrics http://sumo.dlr.de/wiki/TraCI/Vehicle_Value_Retrieval
                    traci.vehicle.subscribe(vehID,
                                            (tc.VAR_ROAD_ID, tc.VAR_LANE_INDEX, tc.VAR_LANE_ID, tc.VAR_SPEED, tc.VAR_LANEPOSITION,
                                             tc.VAR_CO2EMISSION,
                                             tc.VAR_COEMISSION,
                                             tc.VAR_HCEMISSION,
                                             tc.VAR_PMXEMISSION,
                                             tc.VAR_NOXEMISSION,
                                             tc.VAR_FUELCONSUMPTION,
                                             tc.VAR_NOISEEMISSION))
                    if rp.VERBOSITY >= 3:
                        report("Adding vehicle '%s', routeID: '%s', vType:'%s'" % (vehID, routeID, vType))
                    self._connectedVehicles[vehID] = veh
                    self._platoons[veh.getPlatoon().getID()] = veh.getPlatoon()
                    self.carIndex += 1
                    return veh
                else:
                    report("Route of vehicle '%s' is not valid" % vehID)
                    return None
        except TraCIException as traci_exception:
            traceback.print_exc()
            raise traci_exception
        except KeyError as e:
            raise e

    def _addNormalVehicle(self):
        vehID = "normal-car-" + str(self.carIndex)
        typeID = "normal-car" # must be same with <vType> id in flow.rou.xml if used
        routeID = "normal-car-route-" + str(self.carIndex)
        traci.route.add(routeID, self.edges)

        # TODO: hard-coded lane numbers, there should be getLaneNumber(edgeID) method in edge,
        # TODO: but there's no such fcn in current version
        # see: http://www.sumo.dlr.de/daily/pydoc/traci._edge.html#EdgeDomain-getLaneNumber
        # laneNumbers = traci.edge.getLaneNumber("12N")
        laneNumbers = [0, 1, 2, 3]

        # TODO: remove in production
        random.seed(0)

        arrivalLane = str(random.choice(laneNumbers))
        traci.vehicle.addFull(vehID=vehID, routeID=routeID, typeID='DEFAULT_VEHTYPE', depart=str(simTime()), departLane='random', departPos='base', departSpeed='0', arrivalLane=arrivalLane, arrivalPos='random')

        self.carIndex += 1

    def _removeArrived(self):
        ''' _removeArrived()

        Remove all vehicles that have left the simulation from _connectedVehicles.
        Returns the number of removed connected vehicles
        Vehicles are not accessible via traci in this method
        '''

        count = 0
        toRemove = defaultdict(list)
        for ID in traci.simulation.getArrivedIDList():
            # first store arrived vehicles platoonwise
            if not self._isConnected(ID):
                continue
            if rp.VERBOSITY >= 3:
                report("Removing arrived vehicle '%s'" % ID)

            veh = self._connectedVehicles.pop(ID)
            toRemove[veh.getPlatoon().getID()].append(veh)
            count += 1

            self._updateStatistics(veh)

        # adjust platoons
        for pltnID, vehs in toRemove.items():
            pltn = self._platoons[pltnID]
            pltn.removeVehicles(vehs)

            if pltn.size() == 0:
                # remove empty platoons
                self._platoons.pop(pltn.getID())

            else:
                pltn.adjustInterval()

        # Re-add removed cars (both normal & platoon) into the system
        # Returns a list of ids of arrived vehicles (reached their destination and removed from the road network)
        for vehID in traci.simulation.getArrivedIDList():
            # The only way to distinguish the type of arrived car is to look at its id
            # vehID is either "normal-car-idx" or "platoon-car-pltnidx", see _addNormalVehicle & _addPlatoonVehicle
            if "platoon" in vehID:
                self._addPlatoonVehicle()
            else:
                self._addNormalVehicle()

        return count

    def get_statistics(self):
        config = dict(
            catchupDistance=cfg.CATCHUP_DISTANCE,
            maxPlatoonGap=cfg.MAX_PLATOON_GAP,
            platoonSplitTime=cfg.PLATOON_SPLIT_TIME,
            switchImpatienceFactor=cfg.SWITCH_IMPATIENCE_FACTOR,
            maxVehiclesInPlatoon=Config.maxVehiclesInPlatoon,
            lookAheadDistance=Config.lookAheadDistance,
            platoonCarCounter=Config.platoonCarCounter,
            totalCarCounter=Config.totalCarCounter,
            nrOfNotTravelledEdges=Config.nrOfNotTravelledEdges,
            joinDistance=Config.joinDistance
        )

        data = dict(
            TripDurations=self.TripDurations,
            CO2Emissions=self.CO2Emissions,
            COEmissions=self.COEmissions,
            HCEmissions=self.HCEmissions,
            PMXEmissions=self.PMXEmissions,
            NOxEmissions=self.NOxEmissions,
            FuelConsumptions=self.FuelConsumptions,
            NoiseEmissions=self.NoiseEmissions,
            Speeds=self.Speeds,
        )

        res = dict(
            data=data,
            nrOfPlatoonsFormed=self.nrOfPlatoonsFormed,
            nrOfPlatoonsSplit=self.nrOfPlatoonsSplit,
            overallPlatoonDuration=self.overallPlatoonDuration,
            config=config,
            simTime=simTime()
        )
        # if required, total number of trips can be obtained with len(TripDurations)

        return res

    def _endSimulation(self):
        import app.simulation.PlatoonSimulation as ps
        if simTime() % Config.nrOfTicks == 0:
            ps.simulationEnded = True
