# import glob
import os, json
import matplotlib.pyplot as plt
from app.tests.experiments import make_sure_path_exists

avgParams = ["totalCO2EmissionAverage", "totalCOEmissionAverage", "totalFuelConsumptionAverage",
             "totalHCEmissionAverage", "totalNOxEmissionAverage", "totalNoiseEmissionAverage",
             "totalPMXEmissionAverage", "totalSpeedAverage", "totalTripAverage"]

otherParams = ["nrOfPlatoonsFormed", "nrOfPlatoonsSplit", "overallPlatoonDuration", "totalTrips"]


def get_folder_paths():
    folder_paths = [os.path.relpath(x) for x in os.listdir(os.path.join("..", "results", "platooning"))]
    for folder_path in folder_paths:
        if "plots" in folder_path:
            folder_paths.remove(folder_path)
    return folder_paths


def get_data(folder_path):
    json_data = []
    parameter = folder_path.split(os.sep)[-1]
    parameterFolder = os.path.join(os.getcwd(), "..", "results", "platooning", folder_path)

    for f_name in os.listdir(parameterFolder):
        f_path = os.path.join(parameterFolder, f_name)
        with open(f_path) as f:
            json_data.append(json.load(f))
    return parameter, json_data


def sort_data(parameter, data):
    return sorted(data, key=lambda k: k['config'].get(parameter))


def parse_data(parameter, data, y_label):
    x_values = []
    y_values = []
    for json_obj in data:
        x_values.append(json_obj["config"][parameter])

        if y_label in avgParams:
            y_values.append(json_obj["averages"][y_label])
        else:
            y_values.append(json_obj[y_label])
    return x_values, y_values


def plot_data(x_values, y_values, x_label, y_label):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_title('Effect of ' + x_label + " on " + y_label)

    # set proper units for labels and use another variable for them as original ones are used for plot image files
    yLabelPlot = y_label
    xLabelPlot = x_label
    if yLabelPlot == "overallPlatoonDuration" or yLabelPlot == "totalTripAverage":
        yLabelPlot += " [sim. s]"
    elif "FuelConsumption" in yLabelPlot:
        yLabelPlot += " [ml/s]"
    elif "Speed" in yLabelPlot:
        yLabelPlot += " [m/s]"
    elif "Emission" in yLabelPlot and yLabelPlot != "totalNoiseEmissionAverage":
        yLabelPlot += " [mg/s]"
    elif yLabelPlot == "totalNoiseEmissionAverage":
        yLabelPlot += " [dBA]"

    if xLabelPlot == "totalTripAverage":
        xLabelPlot += " [sim. s]"
    elif xLabelPlot == "platoonSplitTime":
        xLabelPlot += " [s]"
    elif xLabelPlot == "maxPlatoonGap" or xLabelPlot == "catchupDist" or xLabelPlot == "joinDistance" or xLabelPlot == "lookAheadDistance":
        xLabelPlot += " [m]"

    ax.set_ylabel(yLabelPlot)
    ax.set_xlabel(xLabelPlot)

    ax.plot(x_values, y_values, 'o')
    fig_name = y_label + ".pdf"
    fig_folder = os.path.join(os.getcwd(), "..", "results", "platooning", "plots", x_label)
    make_sure_path_exists(fig_folder)
    fig_path = os.path.join(fig_folder, fig_name)
    plt.savefig(fig_path)
    plt.close()

if __name__ == '__main__':
    paths = get_folder_paths()
    for path in paths:
        parameter, data = get_data(path)
        sorted_data = sort_data(parameter, data)
        allParams = avgParams + otherParams
        for y_parameter in allParams:
            x, y = parse_data(parameter, sorted_data, y_parameter)
            # parameter is our x label, y_parameter is our y_label, basic naming convention
            plot_data(x, y, parameter, y_parameter)