import os.path, json, errno
from Run import run
from copy import deepcopy
import app.Config as PlatoonConfig
import xml.etree.ElementTree as ET

'''
    Driver for platooning scenario
    Before running via "python platoonExperiments.py",
    set sumoUseGUI flag to False and platooning flag to True in app.Config.py
'''

# These must be same with the ones in Config.py


current_dir = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
simpla_cfg_xml = os.path.abspath(os.path.join(parent_dir, "map", "simpla.cfg"))
xml_tree = ET.parse(simpla_cfg_xml)
root = xml_tree.getroot()

defaultParameters = deepcopy(PlatoonConfig.parameters)

# variables to be used in each experiment separately
changeableVariables = dict(
    catchupDistance=[100.0, 200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 1000.0],
    maxPlatoonGap=[25.0, 50.0, 75.0, 100.0, 150.0, 200.0, 250.0, 300.0, 400.0, 500.0, 600.0, 1000.0],
    platoonSplitTime=[3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 15.0, 20.0]
)

def flush_results(variable_name, value, results):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    results_dir = os.path.join(parent_dir, 'results', variable_name)
    make_sure_path_exists(results_dir)
    file_path = os.path.join(results_dir, str(value))
    with open(file_path + '.json', 'w') as outfile:
        json.dump(results, outfile, sort_keys=True, indent=4, ensure_ascii=False)


# https://stackoverflow.com/a/5032238
def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def changeVariable(variable_name, value):
    # temporarily change a variable to perform an experiment and revert it back
    # these parameters should be loaded/changed within different files, we need to distinguish them based on their names

    # there might be a better way instead of this if/else statements
    if variable_name == "maxVehiclesInPlatoon":
        PlatoonConfig.parameters["changeable"]["maxVehiclesInPlatoon"] = value
    elif variable_name == "catchupDistance":
        PlatoonConfig.parameters["changeable"]["catchupDistance"] = value
        PlatoonConfig.parameters["contextual"]["lookAheadDistance"] = value # TODO: this dependency should be reported in another branch
    elif variable_name == "maxPlatoonGap":
        PlatoonConfig.parameters["changeable"]["maxPlatoonGap"] = value
    elif variable_name == "platoonSplitTime":
        PlatoonConfig.parameters["changeable"]["platoonSplitTime"] = value
    elif variable_name == "joinDistance":
        PlatoonConfig.parameters["changeable"]["joinDistance"] = value
    defaultParameters[variable_name] = value

if __name__ == '__main__':
    originalParameters = deepcopy(defaultParameters)

    if PlatoonConfig.sumoUseGUI and PlatoonConfig.forTests:
        print("SUMO GUI cannot be used to perform sequential tests")
        exit(0)

    PlatoonConfig.platooning = True
    for variable_name in changeableVariables:
        for value in changeableVariables[variable_name]:
            changeVariable(variable_name, value)
            print("New parameter: " + variable_name + " - " + str(value))
            results = run()
            flush_results(variable_name=variable_name, value=value, results=results)
            # now revert back to original
            defaultParameters = deepcopy(originalParameters)