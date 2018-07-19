import json
import numpy as np
from scipy import stats

parameters = ["TripDurations",
             "FuelConsumptions",
             "Speeds",
             "Overheads",
             "NumberOfCarsInPlatoons",
             "ReportedPlatoonDurationsBeforeSplit"]

def get_data(configuration_name):
    with open(configuration_name + ".json") as f:
        data = json.load(f)

    return data
    # Overheads = data["data"]["Overheads"]
    # FuelConsumptions = data["data"]["FuelConsumptions"]
    # TripDurations = data["data"]["TripDurations"]
    # NumberOfCarsInPlatoons = data["data"]["NumberOfCarsInPlatoons"]
    # ReportedPlatoonDurationsBeforeSplit = data["data"]["ReportedPlatoonDurationsBeforeSplit"]
    # Speeds = data["data"]["Speeds"]
    #
    # MeanOverheads = np.mean(Overheads)
    # MeanFuelConsumptions = np.mean(FuelConsumptions)
    # MeanTripDurations = np.mean(TripDurations)
    # MeanNumberOfCarsInPlatoons = np.mean(NumberOfCarsInPlatoons)
    # MeanReportedPlatoonDurationsBeforeSplit = np.mean(ReportedPlatoonDurationsBeforeSplit)
    # MeanSpeeds = np.mean(Speeds)
    #
    # print("MeanOverheads", MeanOverheads, "MeanFuelConsumptions", MeanFuelConsumptions,
    #       "MeanTripDurations", MeanTripDurations, "MeanNumberOfCarsInPlatoons", MeanNumberOfCarsInPlatoons,
    #       "MeanReportedPlatoonDurationsBeforeSplit", MeanReportedPlatoonDurationsBeforeSplit, "MeanSpeeds", MeanSpeeds)

def t_test(data1, data2, idx):
    res = []
    # now iterate each parameter & get values from json files, perform test, and write to sep. file
    for param in parameters:
        y_value_1 = data1["data"][param]
        y_value_2 = data2["data"][param]

        mean_1 = np.mean(y_value_1)
        mean_2 = np.mean(y_value_2)
        print("mean1", mean_1, "mean2", mean_2)
        median_1 = np.median(y_value_1)
        median_2 = np.median(y_value_2)
        print("median_1", median_1, "median_2", median_2)

        statistic, pvalue = stats.ttest_ind(y_value_1, y_value_2)
        result = dict(
            means=[mean_1, mean_2],
            medians=[median_1, median_2],
            y_parameter=param,
            statistic=statistic,
            pvalue=pvalue
        )
        res.append(result)
    with open("overall_results_" + str(idx) + ".json", "w") as outfile:
        json.dump(res, outfile, indent=4, ensure_ascii=False)


default_config_data = get_data("0")
data_7 = get_data("7")
data_25 = get_data("25")
t_test(default_config_data, data_7, 0)
t_test(default_config_data, data_25, 1)
t_test(data_7, data_25, 2)
