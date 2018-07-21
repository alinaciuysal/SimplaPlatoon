import os.path
import json
import errno
from copy import deepcopy
import app.Config as PlatoonConfig
import app.Initiator as Initiator

'''
    Driver for platooning scenario.
    Before running this script via "python Run.py", set proper parameters in parameters.json
'''


defaultParameters = deepcopy(PlatoonConfig.parameters)

# variables to be used in each experiment separately
# changeableVariables = dict(
#     catchupDistance=[100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0],
#     maxPlatoonGap=[50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0],
#     platoonSplitTime=[3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0],
#     joinDistance=[25.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0, 1250.0, 1500.0, 1750.0, 2000.0, 2250.0, 2500.0, 2750.0, 3000.0],
#     maxVehiclesInPlatoon=[3, 5, 10, 15, 20, 25, 30, 50]
# )


def flush_results(results, run_index):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    results_dir = os.path.join(current_dir, 'app', 'results')
    make_sure_path_exists(results_dir)
    file_path = os.path.join(results_dir, str(run_index))
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

    # there should be a better way instead of this
    if variable_name == "maxVehiclesInPlatoon":
        PlatoonConfig.parameters["changeable"]["maxVehiclesInPlatoon"] = value
    elif variable_name == "catchupDistance":
        PlatoonConfig.parameters["changeable"]["catchupDistance"] = value
        PlatoonConfig.parameters["contextual"]["lookAheadDistance"] = value
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

    with open("parameters.json") as f:
        parameters = json.load(f)

    extended_simpla_logic = parameters["extended_simpla_logic"]
    sample_size = parameters["sample_size"]
    ignore_first_n_results = parameters["ignore_first_n_results"]
    knobs = parameters["knobs"]

    PlatoonConfig.forTests = True
    PlatoonConfig.nrOfTicks = sample_size

    run_index = 0
    for knob in knobs:
        for variable_name in knob:
            value = knob[variable_name]
            changeVariable(variable_name, value)
        print("New knob: " + str(knob))
        results = Initiator.initiateSimulation(ignore_first_n_results, sample_size, extended_simpla_logic)
        # flush_results(results=results, run_index=run_index)

        # now revert back to default values
        defaultParameters = deepcopy(originalParameters)
        for param in defaultParameters["changeable"]:
            defaultValue = defaultParameters["changeable"][param]
            changeVariable(param, defaultValue)
        run_index += 1
