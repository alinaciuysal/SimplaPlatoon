import os, json
import matplotlib.pyplot as plt
import itertools
import pprint
import numpy as np
import matplotlib.patches as mpatches
import matplotlib.lines as mlines

pp = pprint.PrettyPrinter(indent=4)

from app.tests.platoonExperiments import make_sure_path_exists
from scipy import stats

# These must be same with parameters in data (dict) in _platoonmanager.get_statistics()
parameters = ["TripDurations",
              "FuelConsumptions",
              "Speeds",
              "Overheads",
              "NumberOfCarsInPlatoons",
              "ReportedPlatoonDurationsBeforeSplit"]

def get_file_names(cmds):
    folder_paths = [os.path.relpath(x) for x in os.listdir(os.path.join(*cmds))]
    if 'plots' in folder_paths:
        folder_paths.remove('plots')
    if 'statistics' in folder_paths:
        folder_paths.remove('statistics')
    return folder_paths

def get_json_file_paths(cmds, x_label=None):
    folder_path = os.path.join(*cmds)
    if x_label is not None:
        folder_path = os.path.join(folder_path, x_label)
    file_paths = [os.path.relpath(x) for x in os.listdir(folder_path)]
    for i in xrange(len(file_paths)):
        file_paths[i] = str(file_paths[i]).replace(".json", '')
    return file_paths


def get_data(folder_path):
    json_data = []
    parameter = folder_path.split(os.sep)[-1]
    parameterFolder = os.path.join(os.getcwd(), "..", "results", folder_path)
    for f_name in os.listdir(parameterFolder):
        f_path = os.path.join(parameterFolder, f_name)
        with open(f_path) as f:
            data = json.load(f)
            json_data.append(data)
    return parameter, json_data


def sort_data(x_label, data):
    return sorted(data, key=lambda k: k['config'].get(x_label))

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


def run_plotting_process(f_names):
    for fn in f_names:
        x_label, data = get_data(fn)
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

    stats_dir = os.path.join(parent_dir, 'results', 'statistics')
    make_sure_path_exists(stats_dir)

    results_dir = os.path.join(stats_dir, folder_name)
    make_sure_path_exists(results_dir)

    results_path = os.path.join(results_dir, variable_name)
    with open(results_path + '.json', 'w') as outfile:
        json.dump(result, outfile, indent=4, ensure_ascii=False)


def run_statistics_process(f_names):
    for fn in f_names:
        x_values = get_json_file_paths(["..", "results"], fn)
        x_values = sorted(x_values, key=lambda x: float(x))
        for y_label in parameters:
            res = dict(
                actual_results=[],
                number_of_significant_results=0,
                number_of_non_significant_results=0
            )

            for pair in itertools.combinations(x_values, 2):
                x1 = str(pair[0]) + ".json"
                x2 = str(pair[1]) + ".json"
                # now get the files & their data

                print(x1, x2)
                json_file_path_1 = os.path.join(os.getcwd(), "..", "results", fn, x1)
                with open(json_file_path_1) as f:
                    json_data_1 = json.load(f)
                    orig = json_data_1["data"]["FuelConsumptions"]
                    updated = [item for item in orig if item > 0]
                    json_data_1["data"]["FuelConsumptions"] = updated

                json_file_path_2 = os.path.join(os.getcwd(), "..", "results", fn, x2)
                with open(json_file_path_2) as f:
                    json_data_2 = json.load(f)
                    orig = json_data_2["data"]["FuelConsumptions"]
                    updated = [item for item in orig if item > 0]
                    json_data_2["data"]["FuelConsumptions"] = updated

                # now iterate each parameter & get values from json files, perform test, and write to sep. file
                y1 = json_data_1["data"][y_label]
                y1_mean = np.mean(y1)
                y2 = json_data_2["data"][y_label]
                y2_mean = np.mean(y2)
                statistic, pvalue = stats.ttest_ind(y1, y2, equal_var=False)
                result = dict(
                    x_label=fn,
                    x_parameters=[x1, x2],
                    means_of_x_parameters=[y1_mean, y2_mean],
                    y_parameter=y_label,
                    statistic=statistic,
                    pvalue=pvalue
                )
                if pvalue <= 0.05:
                    res["number_of_significant_results"] += 1
                else:
                    res["number_of_non_significant_results"] += 1
                res["actual_results"].append(result)

            write_results_to_file(folder_name=fn, variable_name=y_label, result=res)


if __name__ == '__main__':

    plotting = True
    if plotting:
        f_names1 = get_file_names(["..", "results"])
        run_plotting_process(f_names=f_names1)

    statistics = True
    if statistics:
        f_names2 = get_file_names(["..", "results"])
        run_statistics_process(f_names=f_names2)

    # this is only used to perform t-tests on default & same configuration of extended-simpla
    # internalStatistics = True
    # if internalStatistics:
    #     json_data = []
    #     cmds = ["dataForStats", "extended-simpla"]
    #     f_names3 = get_json_file_paths(cmds)
    #     for fn in f_names3:
    #         folder = os.path.join(os.getcwd(), *cmds)
    #         exact_file_path = os.path.join(folder, fn)
    #         exact_file_name = exact_file_path + ".json"
    #         with open(exact_file_name) as f:
    #             data = json.load(f)
    #             json_data.append(data)
    #     for json_obj in json_data:
    #         print(json_obj["config"])

    # this is only used to perform t-tests on same configurations of regular-simpla
    # externalStatistics = True
    # if externalStatistics:
    #     f_names4 = get_file_names(["dataForStats", "regular-simpla"])
    #     print(f_names4)
