import os.path, json, errno
from Run import run
from copy import deepcopy
import app.Config as PlatoonConfig

'''
    Driver for regular scenario (without any platooning logic)
    Before running via "python normalExperiments.py",
    set sumoUseGUI flag to False and platooning flag to False in app.Config.py
'''


defaultVariables = dict(
    totalCarCounter=300
)

# variables to be used in each experiment separately
changeableVariables = dict(
    totalCarCounter=[150, 200, 250, 300, 350, 400, 450, 500, 1000]
)

def flush_results(variable_name, value, results):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    results_dir = os.path.join(parent_dir, 'results', 'regular', variable_name)
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
    if variable_name == "totalCarCounter":
        PlatoonConfig.parameters.changeable.totalCarCounter = value
    defaultVariables[variable_name] = value


if __name__ == '__main__':
    originalVariables = deepcopy(defaultVariables)
    # TODO: uncomment in production
    # if PlatoonConfig.sumoUseGUI:
    #     print("SUMO GUI cannot be used to perform sequential experiments")
    #     exit(0)

    for variable_name in changeableVariables:
        for value in changeableVariables[variable_name]:
            changeVariable(variable_name, value)
            print("New parameter: " + variable_name + " - " + str(value))
            results = run()
            flush_results(variable_name=variable_name, value=value, results=results)
            defaultVariables = deepcopy(originalVariables)
            # now revert back to original
            changeVariable(variable_name, defaultVariables[variable_name])
