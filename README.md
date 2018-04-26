# Traffic Simulation A9

### Description
This is a case study for evaluating the use of RTX in traffic control:
https://github.com/Starofall/RTX/tree/traffic-control

### Minimal Setup
* Download or checkout the code
* Run `python setup.py install` to download all dependencies 
* Install [SUMO](http://sumo.dlr.de) & set env var SUMO_HOME
* Install [Kafka](https://kafka.apache.org/) and set kafkaHost in Config.py
* Run `python Run.py`. This will open the SUMO GUI.

### Note 
The implementation is based on the CrowdNav project: https://github.com/Starofall/CrowdNav
