import os.path, json, errno
from Run import run
from copy import deepcopy
import app.Config as PlatoonConfig
import xml.etree.ElementTree as ET

variablesOfSimpla = ["catchupDist", "maxPlatoonGap", "platoonSplitTime", "switchImpatienceFactor"]
variablesOfPlatooning = ["maxVehiclesInPlatoon", "lookAheadDistance", "platoonCarCounter", "nonPlatoonCarCounter", "nrOfNotTravelledEdges", "joinDistance"]
current_dir = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
simpla_cfg_xml = os.path.abspath(os.path.join(parent_dir, "map", "simpla.cfg"))
xml_tree = ET.parse(simpla_cfg_xml)
root = xml_tree.getroot()

defaultVariables = dict(
    catchupDist=150.0,
    maxPlatoonGap=100.0,
    platoonSplitTime=5.0,
    switchImpatienceFactor=0.1,
    maxVehiclesInPlatoon=6,
    lookAheadDistance=200.0,
    platoonCarCounter=100,
    nonPlatoonCarCounter=200,
    nrOfNotTravelledEdges=5,
    joinDistance=100.0
)

# variables to be used in each experiment separately
changeableVariables = dict(
    catchupDist=[50.0, 100.0, 150.0, 200.0, 250.0, 300.0],
    maxPlatoonGap=[10.0, 15.0, 20.0, 25.0, 50.0, 100.0, 200.0],
    platoonSplitTime=[1.0, 2.0, 3.0, 4.0, 5.0],
    switchImpatienceFactor=[0.1, 0.2, 0.3, 0.4],
    maxVehiclesInPlatoon=[2, 3, 4, 5, 6, 7, 8, 9, 10],
    lookAheadDistance=[50.0, 100.0, 200.0, 400.0],
    platoonCarCounter=[50, 100, 200],
    nonPlatoonCarCounter=[100, 200, 400],
    nrOfNotTravelledEdges=[0, 5, 10, 20],
    joinDistance=[10.0, 25.0, 50.0, 100.0, 200.0, 500.0]
)


def flush_results(variable_name, value, results):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    results_dir = os.path.join(parent_dir, 'results', 'platooning', variable_name)
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

def changeValueInXML(attribute, newValue):
    global root
    if root is not None:
        tags = [elem.tag for elem in root.iter()]
        if attribute in tags:
            foundElement = root.find(attribute)
            # foundElement.attrib is a dict: {'value': exact value in xml}, and value must be string
            foundElement.attrib["value"] = str(newValue)
            xml_tree.write(simpla_cfg_xml)


def changeVariable(variable_name, value):
    # temporarily change a variable to perform an experiment or for revert back
    # these parameters should be loaded/changed within different files, we need to distinguish them based on their names
    if variable_name in variablesOfSimpla:
        changeValueInXML(variable_name, value)
    else:
        # there must be a better way instead of this
        if variable_name == "maxVehiclesInPlatoon":
            PlatoonConfig.maxVehiclesInPlatoon = value
        elif variable_name == "lookAheadDistance":
            PlatoonConfig.lookAheadDistance = value
        elif variable_name == "platoonCarCounter":
            PlatoonConfig.platoonCarCounter = value
        elif variable_name == "nonPlatoonCarCounter":
            PlatoonConfig.nonPlatoonCarCounter = value
        elif variable_name == "nrOfNotTravelledEdges":
            PlatoonConfig.nrOfNotTravelledEdges = value
        elif variable_name == "joinDistance":
            PlatoonConfig.joinDistance = value
    defaultVariables[variable_name] = value

if __name__ == '__main__':
    originalVariables = deepcopy(defaultVariables)
    if PlatoonConfig.sumoUseGUI:
        print("SUMO GUI cannot be used to perform sequential experiments")
        exit(0)

    for variable_name in changeableVariables:
        for value in changeableVariables[variable_name]:
            changeVariable(variable_name, value)
            print("New parameter: " + variable_name + " - " + str(value))
            results = run()
            flush_results(variable_name=variable_name, value=value, results=results)
            defaultVariables = deepcopy(originalVariables)
            # now revert back to original
            changeVariable(variable_name, defaultVariables[variable_name])
