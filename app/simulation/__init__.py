# Eclipse SUMO, Simulation of Urban MObility; see https://eclipse.org/sumo
# Copyright (C) 2017-2017 German Aerospace Center (DLR) and others.
# This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v2.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v20.html

import traci
import traci.constants as tc

_mgr = None
_useStepListener = 'addStepListener' in dir(traci)
_emergencyDecelImplemented = 'VAR_EMERGENCY_DECEL' in dir(traci.constants)

if not _emergencyDecelImplemented:
    # Set emergency decel to decel
    traci.constants.VAR_EMERGENCY_DECEL = 0x7b
    traci.vehicletype.getEmergencyDecel = traci.vehicletype.getDecel