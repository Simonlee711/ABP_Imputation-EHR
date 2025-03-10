import os
import glob
import numpy as np
import pandas as pd
import pickle
import sys
from tqdm import tqdm

import matplotlib as mpl
import platform
if platform.system() == 'Darwin':
    mpl.use('MacOSX')

sys.path.append("../../")
import src.project_configs as project_configs
import src.models.abp_model as abp_model
import src.utils as utils

# file name configurations
model_weights = "../../models/trained_models/2020-03-07_21:25:11_vnet_4s_no_noise.hdf5"

# for plotting individual window input and output waveforms
plot_windows = True
train_or_val_or_test = "test"
save_dir = os.path.join(project_configs.project_dir, os.path.basename(os.path.dirname(model_weights)) + "_predictions")
wave_or_scaler = "wave"

os.environ["KERAS_BACKEND"] = "plaidml.keras.backend"

add_noise = project_configs.add_nibp_noise
overwrite = False

if __name__ == "__main__":
    # get the demographic data
    demo_df = utils.get_demo_df()

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # randomly select record from list of records
    if train_or_val_or_test == "train":
        record_list = glob.glob(os.path.join(project_configs.train_dir, "*.npy"))
    elif train_or_val_or_test == "val":
        record_list = glob.glob(os.path.join(project_configs.val_dir, "*.npy"))
    elif train_or_val_or_test == "test":
        record_list = glob.glob(os.path.join(project_configs.test_dir, "*.npy"))
    else:
        raise ValueError("ERROR: train_or_val_or_test must either be 'train' or 'val' or 'test'.")

    # create data frame
    record_df = pd.DataFrame(record_list, columns=["file_path"])
    # get list of patient IDs
    record_df["patient_ID"] = record_df["file_path"].apply(lambda x: utils.get_patient_from_file(x))
    record_df["win_num"] = record_df["file_path"].apply(lambda x: utils.get_window_from_file(x))

    # read in scaler objects
    X_train_scaler, y_train_scaler = utils.load_scaler_objects(project_configs.X_scaler_pickle,
                                                               project_configs.y_scaler_pickle)
    # read in model and load weights
    model = abp_model.create_model_vnet()
    model.load_weights(model_weights)

    print("Number of patients: {}".format(record_df["patient_ID"].unique().shape[0]))

    # sort window files so that we process in chronological order
    record_df.sort_values(by=["patient_ID", "win_num"], inplace=True)

    # for each patient, iterate through all windows and predict waveform
    for p, window_files in tqdm(record_df.groupby("patient_ID")["file_path"]):
        window_count = 0

        # get demographic data for this patient
        # TODO: see why some patients don't have clinical data
        try:
            patient_id = p
            X_demo = np.repeat(demo_df.loc[patient_id], project_configs.window_size).values.reshape(
                project_configs.window_size, demo_df.shape[1])
        except KeyError:
            continue

        for f in tqdm(window_files[:min(len(window_files), 50)]):
        #for f in tqdm(window_files):
            rec = np.load(f, allow_pickle=True)
            num_windows = int(rec.shape[0] / project_configs.window_size)
            window_num = utils.get_window_from_file(f)
            # skip this file if it already exists and we don't want to overwrite
            if os.path.exists(os.path.join(save_dir, "{}_{}_predictions.csv.gz".format(p, window_num))) and not overwrite:
                continue
            result_df = pd.DataFrame()
            # if we do, use model to predict waveform for this continuous stretch
            for i in range(num_windows):
                window_count += 1
                idx = i * project_configs.window_size

                nibp_sys = rec[idx:idx + project_configs.window_size, project_configs.nibp_sys_col].mean()
                nibp_dias = rec[idx:idx + project_configs.window_size, project_configs.nibp_dias_col].mean()
                nibp_mean = rec[idx:idx + project_configs.window_size, project_configs.nibp_mean_col].mean()

                ecg = rec[idx:idx + project_configs.window_size, project_configs.ecg_col]
                ppg = rec[idx:idx + project_configs.window_size, project_configs.ppg_col]

                # Fix for build_features.py bug..
                if nibp_sys <= 0 or nibp_dias <= 0 or nibp_mean <= 0:
                    continue

                if add_noise:
                    # add "cuff noise" to measurement
                    noise_val = np.random.normal(loc=11.8, scale=28.9, size=1)
                    for c in [project_configs.nibp_sys_col,
                              project_configs.nibp_dias_col,
                              project_configs.nibp_mean_col]:
                        rec[idx:idx + project_configs.window_size, c] += noise_val

                X_scaled = X_train_scaler.transform(rec[idx:idx + project_configs.window_size, 0:-1])
                X_scaled = np.concatenate((X_scaled, X_demo), axis=1)
                input_window = np.pad(X_scaled, ((project_configs.padding_size, project_configs.padding_size), (0, 0)),
                                      'edge')
                # get rid of any NaN values
                input_window = np.nan_to_num(input_window)

                # get proximity from NIBP measurement
                prox = rec[idx:idx + project_configs.window_size, project_configs.prox_col]

                # get true BP waveform
                y_true = rec[idx:idx + project_configs.window_size, -1]

                # get predicted BP waveform
                pred_abp = model.predict(np.array([input_window]), batch_size=1)[0]
                y_pred_scaled = y_train_scaler.inverse_transform(pred_abp)[:, 0]

                # create dataframe with prediction results
                pred_df = pd.DataFrame.from_dict({"y_true": list(y_true),
                                                  "y_pred": list(y_pred_scaled),
                                                  "prox": list(prox),
                                                  "ecg": list(ecg),
                                                  "ppg": list(ppg)},
                                                 orient="columns")
                # add additional columns
                pred_df["nibp_sys"] = nibp_sys
                pred_df["nibp_dias"] = nibp_dias
                pred_df["patient_ID"] = p
                pred_df["window_count"] = i
                pred_df["window_number"] = window_count
                pred_df["date"] = "-".join((os.path.basename(f).split("_")[0]).split("-")[1:])
                # append to result dataframe
                result_df = result_df.append(pred_df)

            result_df.to_csv(os.path.join(save_dir, "{}_{}_predictions.csv.gz".format(p, window_num)), sep=",",
                             header=True, index=False)
