# The network config (links to the net) we use for our simulation
sumoConfig = "./app/map/A9_conf.sumocfg"

# The network net we use for our simulation
sumoNet = "./app/map/A9.net.xml"

# should use kafka for config changes (else it uses json file)
kafkaUpdates = True

# the kafka host we want to send our messages to
kafkaHost = "kafka:9092"

# the topics we send the kafka messages to
kafkaTopicTicks = "ticks"
kafkaTopicLoopDetectorOccupancies = "occupancies"
kafkaTopicCarSpeeds = "speeds"

# where we receive system changes
kafkaCommandsTopic = "shoulder-control"

# True if we want to use the SUMO GUI (always of in parallel mode)
sumoUseGUI = False

# True if we want to use platooning scenario, False if we want to use regular scenario
platooning = True