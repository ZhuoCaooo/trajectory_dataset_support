import os
import json
from multiprocessing.dummy import Pool as ThreadPool
import time

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import matplotlib.transforms as mtransforms
import numpy as np
import pandas as pd
import seaborn as sns


mpl.rcParams.update(
    {
        "figure.dpi": 300,
        "font.family": "FreeSerif",
        "font.size": 10,
        "font.stretch": "semi-expanded",
    }
)


def merge_dictionary(dict1, dict2):
    for key, value in dict2.items():
        if key not in dict1:
            dict1[key] = value
        else:
            if isinstance(value, dict):
                merge_dictionary(dict1[key], value)
            else:
                dict1[key] += value
    return dict1


def _get_plot_range(df: pd.DataFrame):
    x_min = df["x"].min()
    x_max = df["x"].max()
    y_min = df["y"].min()
    y_max = df["y"].max()

    x_min = x_min // 1
    x_max = x_max // 1 + 1
    y_min = y_min // 1 - 3
    y_max = y_max // 1 + 4

    return x_min, x_max, y_min, y_max


def plot_map_and_trajectories(
    map_name, data_path, img_path, transform, type_order, configs
):
    map_img = mpimg.imread(os.path.join(img_path, map_name + ".png"))

    file_id = configs[map_name]["trajectory_files"][0]
    trajectory_path = os.path.join(data_path, "%02d_tracks.csv" % file_id)
    df_trajectory = pd.read_csv(trajectory_path, chunksize=100000)
    trajectory_metadata_path = os.path.join(data_path, "%02d_tracksMeta.csv" % file_id)
    df_metadata = pd.read_csv(trajectory_metadata_path)

    trajectory_types = dict()
    for _, line in df_metadata.iterrows():
        trajectory_types[int(line["id"])] = line["class"]

    locations = list()
    for chunk in df_trajectory:
        for _, line in chunk.iterrows():
            locations.append([line["x"], line["y"], trajectory_types[int(line["id"])]])

    df = pd.DataFrame(locations, columns=["x", "y", "class"])
    x_min, x_max, y_min, y_max = _get_plot_range(df)

    fig, ax = plt.subplots()
    fig.set_figwidth(12)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    im = ax.imshow(map_img, aspect="equal")
    trans_data = transform + ax.transData
    im.set_transform(trans_data)
    sns.scatterplot(
        df,
        x="x",
        y="y",
        hue="class",
        s=0.05,
        palette="husl",
        hue_order=type_order,
        legend=True,
        ax=ax,
    )
    plt.legend(bbox_to_anchor=(1.0, 1.0), loc="upper left")
    plt.show()


def plot_speed_distribution(dataset, data_path, type_order, configs):
    for key, value in configs.items():
        if not dataset in key:
            continue

        speeds = list()
        for file_id in value["trajectory_files"]:
            trajectory_metadata_path = os.path.join(
                data_path, "%02d_tracksMeta.csv" % file_id
            )

            df = pd.read_csv(trajectory_metadata_path)

            for _, line in df.iterrows():
                speeds.append([key, line["class"], line["meanXVelocity"]])

    df = pd.DataFrame(speeds, columns=["map", "class", "meanSpeed"])
    plot = sns.FacetGrid(
        df,
        col="map",
        col_wrap=2,
        sharex=True,
        sharey=False,
        aspect=1.5,
        hue="class",
        palette="husl",
        hue_order=type_order,
    )
    plot.map(sns.kdeplot, "meanSpeed", fill=True, alpha=0.5)
    plot.add_legend()
    plt.show()


def _count_lane_change(trajectory_file_path):
    df = pd.read_csv(trajectory_file_path)
    count = dict()
    for _, line in df.iterrows():
        if line["class"] not in count:
            count[line["class"]] = dict()

        if line["numLaneChanges"] not in count[line["class"]]:
            count[line["class"]][line["numLaneChanges"]] = 0

        count[line["class"]][line["numLaneChanges"]] += 1

    return count


def plot_lane_change_distribution(dataset, data_path, type_order, configs):
    maps = dict()
    files = dict()
    for key, value in configs.items():
        if dataset in key:
            maps[key] = dict()
            for file_id in value["trajectory_files"]:
                files[file_id] = key

    for file_id, map_key in files.items():
        trajectory_metadata_path = os.path.join(
            data_path, "%02d_tracksMeta.csv" % file_id
        )
        lane_change_distribution = _count_lane_change(trajectory_metadata_path)
        if map_key not in maps:
            maps[map_key] = lane_change_distribution
        else:
            merge_dictionary(maps[map_key], lane_change_distribution)

    df = pd.DataFrame(columns=["map", "class", "numLaneChanges", "count"])
    for map_key, lane_change_dist in maps.items():
        for class_, lane_change_count in lane_change_dist.items():
            for num_lane_changes, count in lane_change_count.items():
                df.loc[len(df.index)] = [
                    map_key,
                    class_,
                    int(num_lane_changes),
                    int(count),
                ]

    plot = sns.FacetGrid(
        df,
        col="map",
        col_wrap=3,
        sharex=True,
        sharey=False,
        hue="class",
        palette="husl",
        hue_order=type_order,
    )
    plot.map(sns.lineplot, "numLaneChanges", "count", markers=True)
    plot.add_legend()
    plt.show()
