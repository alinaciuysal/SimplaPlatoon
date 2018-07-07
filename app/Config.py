# The network config (links to the net) we use for our simulation
sumoConfig = "A9_conf.sumocfg"

# The network net we use for our simulation
sumoNet = "A9.net.xml"



# should use kafka for config changes (else it uses json file)
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
initialWaitTicks = 300

# True if we want to use the SUMO GUI
sumoUseGUI = False

# True if we want to use platooning scenario, False if we want to use regular scenario
platooning = True
stats = "mean" # can also be median, min, max for now

# start & end edges for destinations of all cars
startEdgeID = "11S"
endEdgeID = "135586672#0"

# number of ticks to run each simulation
nrOfTicks = 2000

# changeable variables
maxVehiclesInPlatoon = 6
lookAheadDistance = 200.0 # distance to find a leader vehicle in the simulation
platoonCarCounter = 100
nonPlatoonCarCounter = 200
nrOfNotTravelledEdges = 5 # to select last n edges of each platoon car route
joinDistance = 100.0 # the term "d" that is used to find extreme positions (-+d) of platoon