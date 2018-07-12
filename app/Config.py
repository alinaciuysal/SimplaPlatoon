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
kafkaTopicLoopDetectorOccupancies = "occupancies"
kafkaTopicCarSpeeds = "speeds"
kafkaTopicDurationForTrips = "durations"
kafkaTopicReportedValues = "reportedValues"

# where we receive system changes
kafkaCommandsTopic = "shoulder-control"
kafkaPlatoonConfigTopic = "platoon-config"

# Initial wait time before publishing data
initialWaitTicks = 500

# True if we want to use the SUMO GUI
sumoUseGUI = True

# True if we want to use platooning scenario, False if we want to use regular scenario
platooning = True

# True if we want end simulation at some point and get / publish the results via script
forTests = True

if forTests:
    # number of ticks to run each simulation for test
    nrOfTicks = 2000

# startEdgeID & lastEdgeID denotes lower & upper edges, i.e. extreme points
startEdgeID = "11S"
lastEdgeID = "23805795"

''' one of these will be selected (in randomized manner) as exit edge of each car '''
# edgeIDsForExit = ["135586672#0", "23805795"]

edgeIDsForExit = ["135586672#0", "12N", "286344111", "286344110", "23805795"]

parameters = dict(
    contextual=dict(
        lookAheadDistance=300.0, # distance to find a leader vehicle in the simulation
        switchImpatienceFactor=0.1,
        platoonCarCounter=250,
        totalCarCounter=250
    ),

    changeable=dict(
        maxVehiclesInPlatoon=6,
        catchupDistance=300.0,
        maxPlatoonGap=200.0,
        platoonSplitTime=10.0,
        joinDistance=100.0 # to find extreme positions (-+d) of platoon
    )
)

# simpla paramerers
import random
random.seed(0)

def get_random():
    return random