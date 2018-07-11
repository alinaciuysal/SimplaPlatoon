import os, json
import matplotlib.pyplot as plt
import itertools
import pprint
pp = pprint.PrettyPrinter(indent=4)

from app.tests.platoonExperiments import make_sure_path_exists
from scipy import stats

# These must be same with parameters in data (dict) in _platoonmanager.get_statistics()
parameters = ["TripDurations",
              "FuelConsumptions",
              "Speeds",
              "Overheads",
              "TimeSpentInsidePlatoon",
              "NumberOfCarsInPlatoons"]

4
def get_folder_paths():
    folder_paths = [os.path.relpath(x) for x in os.listdir(os.path.join("..", "results", "platooning"))]
    for folder_path in folder_paths:
        if "plots" in folder_path:
            folder_paths.remove(folder_path)
    return folder_paths


def get_json_file_paths(x_label):
    file_paths = [os.path.relpath(x) for x in os.listdir(os.path.join("..", "results", "platooning", x_label))]
    for i in xrange(len(file_paths)):
        file_paths[i] = str(file_paths[i]).replace(".json", '')
    return file_paths


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
    format_box_plot(ax, y_values)

    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)

    # Custom x-axis labels for respective samples
    ax.set_xticklabels(x_values)

    # Remove top axes and right axes ticks
    ax.get_xaxis().tick_bottom()
    ax.get_yaxis().tick_left()

    fig_name = y_label + ".png"
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


def run_plotting_process(paths):
    for path in paths:
        x_label, data = get_data(path)
        # x_label is the catchupDistance, joinDistance etc. i.e. last element of file path
        sorted_data = sort_data(x_label, data)
        # print(sorted_data)
        # y_label = TripDurations, CO2Emissions etc.
        for y_label in parameters:
            y_values = []
            x_values = []
            for json_obj in sorted_data:
                x_value = json_obj["config"][x_label]
                y_value = json_obj["data"][y_label]
                y_values.append(y_value)
                x_values.append(x_value)
            draw_box_plot(x_label, y_label, x_values, y_values)


def write_results_to_file(folder_name, variable_name, result):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    results_dir = os.path.join(parent_dir, 'results', 'statisticalResults', folder_name)
    make_sure_path_exists(results_dir)
    results_path = os.path.join(results_dir, variable_name)
    with open(results_path + '.json', 'w') as outfile:
        json.dump(result, outfile, sort_keys=True, indent=4, ensure_ascii=False)

def run_statistics_process(paths):
    for path in paths:


        x_values = get_json_file_paths(path)
        x_values = sorted(x_values, key=lambda x: float(x))

        for pair in itertools.combinations(x_values, 2):
            x1 = str(pair[0]) + ".json"
            x2 = str(pair[1]) + ".json"
            # now get the files & their data

            print(x1, x2)
            json_file_path_1 = os.path.join(os.getcwd(), "..", "results", "platooning", path, x1)
            with open(json_file_path_1) as f:
                json_data_1 = json.load(f)
            # pprint.pprint(json_data_1["config"])

            json_file_path_2 = os.path.join(os.getcwd(), "..", "results", "platooning", path, x2)
            with open(json_file_path_2) as f:
                json_data_2 = json.load(f)
            # pprint.pprint(json_data_2["config"])

            # now iterate each parameter & get values from json files, perform test, and write to sep. file
            for y_label in parameters:
                y1 = json_data_1["data"][y_label]
                y2 = json_data_2["data"][y_label]
                statistic, pvalue = stats.ttest_ind(y1, y2, equal_var=False)
                result = dict(
                    x_label=path,
                    x_parameters=[x1, x2],
                    y_parameter=y_label,
                    statistic=statistic,
                    pvalue=pvalue
                )
                write_results_to_file(folder_name=path, variable_name=y_label + "_" + str(pair[0]) + "_" + str(pair[1]), result=result)


if __name__ == '__main__':
    paths = get_folder_paths()
    plotting = False
    if plotting:
        run_plotting_process(paths=paths)

    statistics = True
    if statistics:
        run_statistics_process(paths=paths)
