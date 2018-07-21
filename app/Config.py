# The network config (links to the net) we use for our simulation
sumoConfig = "A9_conf.sumocfg"

# The network net we use for our simulation
sumoNet = "A9.net.xml"

# should it use kafka for config changes (else it uses json file)
kafkaUpdates = False

# the kafka host we want to send our messages to
kafkaHost = "kafka:9092"

# the topics we send the kafka messages to
kafkaTopicTicks = "ticks"
kafkaTopicCarSpeeds = "speeds"
kafkaTopicDurationForTrips = "durations"
kafkaTopicReportedValues = "reportedValues"

# where we receive system changes
kafkaPlatoonConfigTopic = "platoon-config"

# Initial wait time before publishing data
ignore_first_n_results = 500

# True if we want to use the SUMO GUI
sumoUseGUI = False

forTests = True

# startEdgeID & lastEdgeID denotes lower & upper edges, i.e. extreme points
startEdgeID = "11S"
lastEdgeID = "23805795"

''' one of these will be selected (in randomized manner) as exit edge of each car '''
# edgeIDsForExit = ["135586672#0", "12N", "286344111", "286344110", "23805795"]
edgeIDsForExit = ["135586672#0"]

# you can also set contextual parameters
parameters = dict(
    contextual=dict(
        lookAheadDistance=500.0, # distance to find a leader vehicle in the simulation
        switchImpatienceFactor=0.1,
        platoonCarCounter=250,
        totalCarCounter=250
    ),

    changeable=dict(
        maxVehiclesInPlatoon=10,
        catchupDistance=500.0,
        maxPlatoonGap=500.0,
        platoonSplitTime=10.0,
        joinDistance=3000.0 # to find extreme positions (-+d) of platoon
    )
)

import random
random.seed(0)

def get_random():
    return random