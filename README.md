# ABPImputation

ABPImputation is a package for imputing the arterial blood pressure (ABP) waveform using non-invasive physiological waveforms (photoplethysmogram, or PPG, and electrocardiogram, or ECG/EKG). 
For detailed information, please see [our paper](https://www.nature.com/articles/s41598-021-94913-y).  

<p align="center">
  <img src="https://github.com/brianhill11/media/blob/master/abpimputation/ABPImputation.gif" alt="imputation-gif">
</p>


## Installation

## Data format 

We assume that the input waveform data has been sampled at 100 Hz. 

The raw data should be in the following format: 
```
,ekg,ppg,art,pseudo_NIBP_sys_5min,pseudo_NIBP_dias_5min,pseudo_NIBP_mean_5min
2192-01-15 18:05:13.000,0.2942022306679429,0.00014857817077067377,0.01588212121779295,,,
2192-01-15 18:05:13.010,0.3923739047014039,-0.000148964018089602,-0.0159184022120733,,,
2192-01-15 18:05:13.020,0.36888112077855467,0.00014878046741923878,0.015916127098078936,,,
2192-01-15 18:05:13.030,0.39216988733528724,-0.0001497382374610061,-0.0159912403262073,,,
2192-01-15 18:05:13.040,0.36341014241462266,0.00014898555592997471,0.015950437232792714,,,
2192-01-15 18:05:13.050,0.3878550380346896,-0.00014980310141308973,-0.016016143459373855,,,
```

The first column is the timestamp index, which is assumed to be in sorted order. 
Column names for each signal must either be 'ekg' for electrocardiogram, 
'ppg' for photoplethysmogram, and 
'art' (if available) for arteral line blood pressure, or they should be mapped to such 
using the `signal_column_names` dict in the [project_configs.py](abpimputation/project_configs.py) file. 

Non-invasive blood pressure (NIBP) columns should be specified using the `nibp_column_names` variable 
in the [project_configs.py](abpimputation/project_configs.py) file, using the order: systolic, diastolic, mean. 


## Preprocessing

## Generating predictions with pre-trained model

Generating predictions using the pre-trained model generally
requires 3 steps: 

1. loading waveform data (in the expected format, see [Data format section](#data-format))
2. preprocessing the waveform data to add additional features
3. load the pre-trained model and generated the imputed waveform(s)

An example code segment can be found in:

```
abp_imputer.ipynb
```

## Calibrating the model using additional data

## Training from scratch

Simply change in the 5th cell of ```abp_imputer.ipynb```, the ```train_or_test = 'train'``` variable

