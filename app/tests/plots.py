import os
import json
import matplotlib.pyplot as plt
import itertools
import pprint
import numpy as np
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import errno
from collections import OrderedDict, defaultdict
from operator import itemgetter

pp = pprint.PrettyPrinter(indent=4)

# These must be same with parameters in data (dict) in _platoonmanager.get_statistics()
parameters = ["TripDurations",
              "FuelConsumptions",
              "Speeds",
              "Overheads",
              "NumberOfCarsInPlatoons"]

from scipy import stats


def get_paths(cmds):
    folder_paths = [os.path.relpath(x) for x in os.listdir(os.path.join(*cmds))]
    if 'plots' in folder_paths:
        folder_paths.remove('plots')
    if 'statistics' in folder_paths:
        folder_paths.remove('statistics')
    return folder_paths


# https://stackoverflow.com/a/5032238
def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


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

    median_legend = mlines.Line2D([], [], color='green', marker='^', linestyle='None',
                                    markersize=5, label='Mean')

    mean_legend = mpatches.Patch(color='red', label='Median')

    plt.legend(handles=[median_legend, mean_legend])

    fig_name = y_label + ".png"

    plots_folder = os.path.join(os.getcwd(), "..", "results", "plots")
    make_sure_path_exists(plots_folder)

    fig_folder = os.path.join(plots_folder, x_label)
    make_sure_path_exists(fig_folder)

    fig_path = os.path.join(fig_folder, fig_name)
    plt.savefig(fig_path, bbox_inches='tight')

    plt.close()


# http://blog.bharatbhole.com/creating-boxplots-with-matplotlib/
def format_box_plot(ax, y_values):
    ## add patch_artist=True option to ax.boxplot()
    ## to get fill color

    bp = ax.boxplot(y_values, showmeans=True, showfliers=False)

    ## change outline color, fill color and linewidth of the boxes
    # for box in bp['boxes']:
    #     # change outline color
    #     box.set(linewidth=2)
    #     # change fill color
    #     box.set( facecolor = '#1b9e77' )
    #
    # ## change linewidth of the whiskers
    # for whisker in bp['whiskers']:
    #     whisker.set(linewidth=2)
    #
    # ## change color and linewidth of the caps
    # for cap in bp['caps']:
    #     cap.set(linewidth=2)
    #
    # ## change color and linewidth of the medians
    for median in bp['medians']:
        median.set_color('red')

    #
    # ## change the style of fliers and their fill
    # for flier in bp['fliers']:
    #     flier.set(marker='o', color='#e7298a', alpha=0.5)
    #
    ## change the style of means and their fill
    for mean in bp['means']:
        mean.set_color('green')


def run_plotting_process(data):
    for folder_name in data:

        for y_label in parameters:
            y_values = []
            x_values = []
            averages = []
            # file_name here does not have .json extension
            for file_name in data[folder_name]:
                x_values.append(file_name)

                y_value = data[folder_name][file_name]["data"][y_label]
                y_values.append(y_value)
                # averages.extend(y_value)

            # to create separate plot for concatenated data of different configurations
            # y_values.append(averages)
            x_values.append("Average")
            draw_box_plot(folder_name, y_label, x_values, y_values)


def write_results_to_file(folder_name, file_name, result):
    current_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

    stats_dir = os.path.join(parent_dir, 'results', 'statistics')
    make_sure_path_exists(stats_dir)

    results_dir = os.path.join(stats_dir, folder_name)
    make_sure_path_exists(results_dir)

    results_path = os.path.join(results_dir, file_name)
    with open(results_path + '.json', 'w') as outfile:
        json.dump(result, outfile, indent=4, ensure_ascii=False)


def get_statistics(data):
    for folder_name in data:
        res = dict()

        for y_label in parameters:
            y_values = []
            # file_name here does not have .json extension
            for file_name in data[folder_name]:
                data_points = data[folder_name][file_name]["data"][y_label]
                y_values.extend(data_points)
            res["mean"] = np.mean(y_values)
            res["median"] = np.median(y_values)
            res["std"] = np.std(y_values)
            res["parameter"] = y_label
            write_results_to_file(folder_name=folder_name, file_name=y_label, result=res)


def find_best_configuration(data):
    MeanTripDurations = []
    MeanFuelConsumptions = []
    MeanSpeeds = []
    MeanOverheads = []
    MeanNumberOfCarsInPlatoons = []
    MeanReportedDurationsBeforeSplit = []

    MedianTripDurations = []
    MedianFuelConsumptions = []
    MedianSpeeds = []
    MedianOverheads = []
    MedianNumberOfCarsInPlatoons = []
    MedianReportedDurationsBeforeSplit = []

    for folder_name in data:
        print("folder_name", folder_name)
        for y_label in parameters:
            data_points = []
            for file_name in data[folder_name]:
                data_points.extend(data[folder_name][file_name]["data"][y_label])
            mean = np.mean(data_points)
            median = np.median(data_points)

            if y_label == "TripDurations":
                MeanTripDurations.append((folder_name, mean))
                MedianTripDurations.append((folder_name, median))
            elif y_label == "FuelConsumptions":
                MeanFuelConsumptions.append((folder_name, mean))
                MedianFuelConsumptions.append((folder_name, median))
            elif y_label == "Speeds":
                MeanSpeeds.append((folder_name, mean))
                MedianSpeeds.append((folder_name, median))
            elif y_label == "Overheads":
                MeanOverheads.append((folder_name, mean))
                MedianOverheads.append((folder_name, median))
            elif y_label == "NumberOfCarsInPlatoons":
                MeanNumberOfCarsInPlatoons.append((folder_name, mean))
                MedianNumberOfCarsInPlatoons.append((folder_name, median))

    MeanTripDurations.sort(key=itemgetter(1))
    MeanFuelConsumptions.sort(key=itemgetter(1))
    MeanOverheads.sort(key=itemgetter(1))

    MedianTripDurations.sort(key=itemgetter(1))
    MedianFuelConsumptions.sort(key=itemgetter(1))
    MedianOverheads.sort(key=itemgetter(1))

    # higher values are better for the rest, so sort them in descending order
    MeanSpeeds.sort(key=itemgetter(1), reverse=True)
    MeanNumberOfCarsInPlatoons.sort(key=itemgetter(1), reverse=True)
    MeanReportedDurationsBeforeSplit.sort(key=itemgetter(1), reverse=True)

    MedianSpeeds.sort(key=itemgetter(1), reverse=True)
    MedianNumberOfCarsInPlatoons.sort(key=itemgetter(1), reverse=True)
    MedianReportedDurationsBeforeSplit.sort(key=itemgetter(1), reverse=True)

    write_results_to_file("overall", "MeanTripDurations", MeanTripDurations)
    write_results_to_file("overall", "MeanFuelConsumptions", MeanFuelConsumptions)
    write_results_to_file("overall", "MeanSpeeds", MeanSpeeds)
    write_results_to_file("overall", "MeanOverheads", MeanOverheads)
    write_results_to_file("overall", "MeanNumberOfCarsInPlatoons", MeanNumberOfCarsInPlatoons)
    write_results_to_file("overall", "MeanReportedDurationsBeforeSplit", MeanReportedDurationsBeforeSplit)

    write_results_to_file("overall", "MedianTripDurations", MedianTripDurations)
    write_results_to_file("overall", "MedianFuelConsumptions", MedianFuelConsumptions)
    write_results_to_file("overall", "MedianSpeeds", MedianSpeeds)
    write_results_to_file("overall", "MedianOverheads", MedianOverheads)
    write_results_to_file("overall", "MedianNumberOfCarsInPlatoons", MedianNumberOfCarsInPlatoons)
    write_results_to_file("overall", "MedianReportedDurationsBeforeSplit", MedianReportedDurationsBeforeSplit)


if __name__ == '__main__':

    folders = [os.path.relpath(x) for x in os.listdir(os.path.join(os.getcwd(), "..", "results"))]

    if "plots" in folders:
        folders.remove("plots")
    if "statistics" in folders:
        folders.remove("statistics")

    myDict = defaultdict(OrderedDict)

    for folder_name in folders:
        # first replace extension (json)
        file_names = [os.path.relpath(x).replace('.json', '') for x in os.listdir(os.path.join(os.getcwd(), "..", "results", folder_name))]
        # sort them
        file_names = sorted(file_names, key=float)
        for name in file_names:
            file_path = os.path.join(os.getcwd(), "..", "results", folder_name, name)
            with open(file_path + ".json") as f:
                data = json.load(f)
            myDict[folder_name][name] = data

    plotting = True
    if plotting:
        run_plotting_process(data=myDict)

    statistics = True
    if statistics:
        get_statistics(data=myDict)

    find_best = True
    if find_best:
        find_best_configuration(myDict)
