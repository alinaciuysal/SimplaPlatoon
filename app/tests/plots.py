# import glob
import os, json
import matplotlib.pyplot as plt
from app.tests.platoonExperiments import make_sure_path_exists

# These must be same with parameters in data (dict) in _platoonmanager.get_statistics()
parameters = ["TripDurations", "CO2Emissions", "FuelConsumptions", "Speeds", "Overheads",
              "TotalTimeSpentInsidePlatoon", "TotalTimeSpentOutsidePlatoon",
              "NumberOfCarsInPlatoons",
              "NumberOfPlatoonsFormed", "NumberOfPlatoonsSplit"]

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


def sort_data(x_label, data):
    return sorted(data, key=lambda k: k['config'].get(x_label))


def parse_data(x_label, data, y_label):
    x_values = []
    y_values = []
    for json_obj in data:
        x_values.append(json_obj["config"][x_label])

        if y_label in parameters:
            y_values.append(json_obj["data"][y_label])
        else:
            # regular parameters like numberOfPlatoonsFormed, numberOfPlatoonsSplit, simTime
            y_values.append(json_obj[y_label])
    return x_values, y_values


def draw_scatter_plot(x_values, y_values, x_label, y_label):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_title('Effect of ' + x_label + " on " + y_label)

    # set proper units for labels and use another variable for them as original ones are used for plot image files
    yLabelPlot = y_label
    xLabelPlot = x_label
    if yLabelPlot == "totalTripAverage":
        yLabelPlot += " [s]"
    elif "FuelConsumption" in yLabelPlot:
        yLabelPlot += " [ml/s]"
    elif "Speed" in yLabelPlot:
        yLabelPlot += " [m/s]"
    elif "Emission" in yLabelPlot:
        yLabelPlot += " [mg/s]"

    if xLabelPlot == "platoonSplitTime":
        xLabelPlot += " [s]"
    elif xLabelPlot == "maxPlatoonGap" or xLabelPlot == "catchupDistance" or xLabelPlot == "joinDistance":
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

def draw_box_plot(x_label, y_label, x_values, y_values):
    # Create a figure instance
    fig = plt.figure(1, figsize=(9, 6))
    # Create an axes instance
    ax = fig.add_subplot(111)

    # Create the boxplot & format it
    # format_box_plot(ax, y_values)
    bp = ax.boxplot(y_values)

    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)

    # Custom x-axis labels for respective samples
    ax.set_xticklabels(x_values)

    # Remove top axes and right axes ticks
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()

    fig_name = y_label + ".pdf"
    fig_folder = os.path.join(os.getcwd(), "..", "results", "platooning", "plots", x_label)
    make_sure_path_exists(fig_folder)
    fig_path = os.path.join(fig_folder, fig_name)
    plt.savefig(fig_path, bbox_inches='tight')
    plt.close()


# http://blog.bharatbhole.com/creating-boxplots-with-matplotlib/
def format_box_plot(ax, y_values):
    ## add patch_artist=True option to ax.boxplot()
    ## to get fill color
    bp = ax.boxplot(y_values, patch_artist=True)

    ## change outline color, fill color and linewidth of the boxes
    for box in bp['boxes']:
        # change outline color
        box.set( color='#7570b3', linewidth=2)
        # change fill color
        box.set( facecolor = '#1b9e77' )

    ## change color and linewidth of the whiskers
    for whisker in bp['whiskers']:
        whisker.set(color='#7570b3', linewidth=2)

    ## change color and linewidth of the caps
    for cap in bp['caps']:
        cap.set(color='#7570b3', linewidth=2)

    ## change color and linewidth of the medians
    for median in bp['medians']:
        median.set(color='#b2df8a', linewidth=2)

    ## change the style of fliers and their fill
    for flier in bp['fliers']:
        flier.set(marker='o', color='#e7298a', alpha=0.5)

if __name__ == '__main__':
    paths = get_folder_paths()
    for path in paths:
        x_label, data = get_data(path)
        # x_label is the catchupDistance, joinDistance etc. i.e. last element of file path

        # sorted_data = sort_data(x_label, data)
        # print(sorted_data)
        # y_label = TripDurations, CO2Emissions, COEmissions etc.
        for y_label in parameters:

            x_values, y_values = parse_data(x_label, data, y_label)
            print("x_label", x_label, "y_label", y_label, "x_values", x_values)
            # x_labels = [50.0, 100.0, 150.0...]
            # draw_scatter_plot(x, y, parameter, y_parameter)
            draw_box_plot(x_label=x_label, y_label=y_label, x_values=x_values, y_values=y_values)
