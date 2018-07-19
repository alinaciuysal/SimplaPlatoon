# The network config (links to the net) we use for our simulation
sumoConfig = "A9_conf.sumocfg"

# The network net we use for our simulation
sumoNet = "A9.net.xml"

# should it use kafka for config changes & publishing data (else it uses json file)
kafkaUpdates = True
mqttUpdates = False

# the kafka host we want to send our messages to
kafkaHost = "kafka:9092"

# the topics we send the kafka messages to
kafkaTopicSpeeds = "platooningSpeeds"
kafkaTopicTripDurations = "platooningTripDurations"
kafkaTopicFuelConsumptions = "platooningFuelConsumptions"
kafkaTopicOverheads = "platooningOverheads"

# where we receive system changes
kafkaPlatoonConfigTopic = "platooningConfig"

# Initial wait time before publishing data
ignore_first_n_results = 500

# True if we want to use the SUMO GUI
sumoUseGUI = True

# startEdgeID & lastEdgeID denotes lower & upper edges, i.e. extreme points of the map
startEdgeID = "11S"
lastEdgeID = "23805795"

''' one of these will be selected (in randomized manner) as exit edge of each car '''
# edgeIDsForExit = ["135586672#0", "12N", "286344111", "286344110", "23805795"]
edgeIDsAndNumberOfLanesForExit = {
    "135586672#0": 4
}
# TODO: uncomment following for production?
# edgeIDsAndNumberOfLanesForExit = {
#     "135586672#0": 4,
#     "12N": 5,
#     "286344111": 3,
#     "286344110": 4,
#     "23805795": 3
# }

# you can also set contextual parameters
parameters = dict(
    contextual=dict(
        lookAheadDistance=500.0, # distance to find a leader vehicle in the simulation
        switchImpatienceFactor=0.1,
        platoonCarCounter=250,
        totalCarCounter=250, # set totalCarCounter as platoonCarCounter, other scenario is not tested excessively
        extended_simpla_logic=True
    ),

    changeable=dict(
        maxVehiclesInPlatoon=10,
        catchupDistance=500.0,
        maxPlatoonGap=500.0,
        platoonSplitTime=10.0,
        joinDistance=3000.0 # to find extreme positions (-+d) of platoon
    )
)