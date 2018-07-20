# Eclipse SUMO, Simulation of Urban MObility; see https://eclipse.org/sumo
# Copyright (C) 2017-2017 German Aerospace Center (DLR) and others.
# This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v2.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v20.html

"""
simpla - A simple platooning plugin for TraCI

simpla is a configurable, simple platooning plugin for TraCI.
A platooning configuration has to be created before using.
Its possible elements are given in the example configuration file
'simpla_example.cfg.xml'

Information about vType mappings between original and
platooning vTypes has to be supplied. This can be done directly
in the configuration xml-file by using 'vTypeMapLeader', 'vTypeMapFollower' and 'vTypeMapCatchup'
elements or by reference to seperate files which define the mappings as
'originalVType : mappedVType'

All specified vTypes should be available within the simulation, the "default" type
is optional and used whenever information is missing for some original type
if no default is specified, the original type remains unchanged within the platoon.

For the definition of platooning vTypes for existing basic vTypes,
and generating vTypeMapping-files see the script generateModifiedVTypes.py.

Usage:
1) import simpla into your traci script.
3) Only applies to SUMO version < 0.30: After starting simpla, call simpla.update() after each call to traci.simulationStep()
"""
from app.entity.SimulationManager import *

_mgr = None
_useStepListener = 'addStepListener' in dir(traci)
_emergencyDecelImplemented = 'VAR_EMERGENCY_DECEL' in dir(traci.constants)

if not _emergencyDecelImplemented:
    # Set emergency decel to decel
    traci.constants.VAR_EMERGENCY_DECEL = 0x7b
    traci.vehicletype.getEmergencyDecel = traci.vehicletype.getDecel


def load():
    '''
    Creates a SimulationManager
    '''
    global _mgr
    _mgr = SimulationManager()
    if _useStepListener:
        # For SUMO version >= 0.30
        traci.addStepListener(_mgr)
    return _mgr


def stop():
    '''
    Stops the SimulationManager
    '''
    global _mgr
    if _mgr is not None:
        _mgr.stop()
        traci.removeStepListener(_mgr)
    _mgr = None


def update():
    '''
    Function called each simulation step. Only to be used for SUMO version < 1.0
    '''
    global _mgr, warn
    if _mgr is not None:
        _mgr.step()
    else:
        print("SimulationManager is None")