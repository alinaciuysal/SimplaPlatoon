# Platooning for Traffic Simulation A9

### Description
This is a case study for evaluating the use of OEDA in platooning scenario:
https://github.com/alinaciuysal/OEDA

### Minimal Setup
* Download or checkout the code
* Download and install 32-bit version of [SUMO](http://sumo.dlr.de/wiki/Downloads) & set env_var SUMO_HOME
* Run `python setup.py install` to download all dependencies 
* Set necessary values in app.Config.py. If you want a GUI, set sumoUseGUI to `True` in this file.
* Run `python Run.py`. This will start the simulation.

### Note 
The implementation is based on Simpla project: http://sumo.dlr.de/wiki/Simpla
