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
              "NumberOfCarsInPlatoons",
              "ReportedPlatoonDurationsBeforeSplit"]

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


def draw_box_plot(x_label, y_label, x_values, y_values, outer_folder_name, inner_folder_name):
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

    plots_folder = os.path.join(os.getcwd(), "..", outer_folder_name, inner_folder_name)
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


def run_plotting_process(data, outer_folder_name, inner_folder_name, parameters=None):
    for folder_name in data:
        # iterate all of the given parameters for regular statistics & plotting
        if parameters:
            for y_label in parameters:
                y_values = []
                x_values = []
                # file_name here does not have .json extension
                for file_name in data[folder_name]:
                    x_values.append(file_name)
                    y_value = data[folder_name][file_name]["data"][y_label]
                    y_values.append(y_value)
                draw_box_plot(x_label=folder_name, y_label=y_label, x_values=x_values, y_values=y_values, outer_folder_name=outer_folder_name, inner_folder_name=inner_folder_name)
        else:
            # only executed for best_configurations, as they're already clustered w.r.t y_labels (folder_names)
            y_label = folder_name
            y_values = []
            x_values = []
            # file_name here does not have .json extension
            for file_name in data[folder_name]:
                x_values.append(file_name)
                y_value = data[folder_name][file_name]["data"][y_label]
                y_values.append(y_value)
            draw_box_plot(x_label="Configurations", y_label=y_label, x_values=x_values, y_values=y_values, outer_folder_name=outer_folder_name, inner_folder_name=inner_folder_name)


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
            elif y_label == "ReportedPlatoonDurationsBeforeSplit":
                MeanReportedDurationsBeforeSplit.append((folder_name, mean))
                MedianReportedDurationsBeforeSplit.append((folder_name, median))

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

def find_pairwise_statistics(data):
    for folder_name in data: # folder_name is y-attribute
        print("folder_name", folder_name)
        # first replace extension (json)
        file_names = [os.path.relpath(x).replace('.json', '') for x in os.listdir(os.path.join(os.getcwd(), "..", "best_configurations", folder_name))]
        print("file_names", file_names)
        combinations = list(itertools.combinations(file_names, 2))
        print(combinations)
        res = []
        for tpl in combinations:
            file_name_1 = tpl[0]
            file_name_2 = tpl[1]

            data_1 = data[folder_name][file_name_1]
            data_2 = data[folder_name][file_name_2]
            result = t_test(data_1, data_2, folder_name)
            result["x_parameters"] = [file_name_1, file_name_2]
            res.append(result)

        res_path = os.path.join(os.getcwd(), "..", "best_configurations", "Results", folder_name)
        with open(res_path + ".json", "w") as outfile:
            json.dump(res, outfile, indent=4, ensure_ascii=False)


def t_test(data1, data2, y_parameter):
    # iterate each parameter & get values, perform test, and return result
    y_value_1 = data1["data"][y_parameter]
    y_value_2 = data2["data"][y_parameter]

    mean_1 = np.mean(y_value_1)
    mean_2 = np.mean(y_value_2)
    median_1 = np.median(y_value_1)
    median_2 = np.median(y_value_2)

    statistic, pvalue = stats.ttest_ind(y_value_1, y_value_2, equal_var=False)
    result = dict(
        means=[mean_1, mean_2],
        medians=[median_1, median_2],
        y_parameter=y_parameter,
        statistic=statistic,
        pvalue=pvalue,
        x_parameters=[]
    )
    return result

def get_all_data_from_folder(outer_folder_name):
    inner_folders = [os.path.relpath(x) for x in os.listdir(os.path.join(os.getcwd(), "..", outer_folder_name))]
    if "plots" in inner_folders:
        inner_folders.remove("plots")
    if "statistics" in inner_folders:
        inner_folders.remove("statistics")
    if "Results" in inner_folders:
        inner_folders.remove("Results")
    data = defaultdict(OrderedDict)

    for inner_folder_name in inner_folders:
        print("inner_folder_name", inner_folder_name)
        # first replace extension (json)
        file_names = [os.path.relpath(x).replace('.json', '') for x in os.listdir(os.path.join(os.getcwd(), "..", outer_folder_name, inner_folder_name))]
        for name in file_names:
            file_path = os.path.join(os.getcwd(), "..", outer_folder_name, inner_folder_name, name)
            with open(file_path + ".json") as f:
                d = json.load(f)
            data[inner_folder_name][name] = d
    return data


if __name__ == '__main__':
    first_phase = False # plotting, statistics, finding best configurations

    if first_phase:
        folder_name = "results"
        data = get_all_data_from_folder(outer_folder_name=folder_name)

        plotting = True
        if plotting:
            run_plotting_process(data=data, outer_folder_name=folder_name, inner_folder_name="plots", parameters=parameters)

        statistics = False
        if statistics:
            get_statistics(data=data)

        find_best = False
        if find_best:
            find_best_configuration(data=data)
    else:
        folder_name = "best_configurations"
        data = get_all_data_from_folder(outer_folder_name=folder_name)

        statistics = False
        if statistics:
            find_pairwise_statistics(data=data)

        plotting = True
        if plotting:
            run_plotting_process(data=data, outer_folder_name=folder_name, inner_folder_name="Plots")
