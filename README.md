# Tesla logs
The first recorded fatal incident involving a Tesla vehicle dates from 2016,
where a Model S collided with a semi truck in Florida.
The incident was investigated by the NTSB and the results published in a docket ([HWY16FH018](https://data.ntsb.gov/Docket?ProjectID=93548)).
Tesla provided the NTSB investigators a translation of logged data.
These logs comprise non geo-located data (according to NTSB report) and are stored on an SD card inside the MCU, managed by the gateway.
Various other publications have already been made on the content of the SD card (focusing on vulnerabilities etc. [link](https://2016.zeronights.ru/wp-content/uploads/2016/12/Gateway_Internals_of_Tesla_Motors_v6.pdf)).
However, the contents of the **log** directory is usually left unattended.

This repository contains writeups of the reverse engineering process of these vehicle logs of the Model S, X and 3 vehicles.
Some of these logs have retained their structure over a long period of time, while others change more often.
We would like to enable objective forensic analysis of these logs.
Therefore we are sharing our reverse engineering efforts and developed tools.

## Repository layout
The writeups are placed in the [writeup](writeup) directory.
For each writeup, we included the tools to analyze the logs.
There are example Jupyter notebooks in the [notebooks](notebooks) directory which utilize modules from the [teslalogs](teslalogs) directory.
Even though we tested these tools on a number of vehicles, they are still the result of reverse engineering efforts and therefore incomplete.
They should be used with caution and common sense.
We have not yet encountered any discrepancies between data provided by Tesla and the translation of the log files.

## Writeups
- We initially reverse engineered the Model S and X [logs](writeup/Model_SX_logs.md) based on static data analysis.
- Afterwards we augmented the results by reverse engineering the [gateway firmware](writeup/Gateway_mcu1_mcu2.md).
  Additionally, we were able to validate the extracted logs with recorded CAN data.
- Next came the Model 3 [logs](writeup/Model_3_logs.md), which were used up to software versions 2019.
- In 2020 the logging transitioned to a directory called: [CL](writeup/Model_3_CL.md).
- Model 3 vehicles also record [High Resolution Logging (HRL)](writeup/Model_3_HRL.md) files for certain events.

## Snapshots
For AP2 and AP2.5 vehicles, the autopilot snapshots may be synchronized with the logged data and interactively explored.
Tools to convert video and image data from snapshots can be found in [teslalogs/snapshot_video](teslalogs/snapshot_video).
Here's an example with data from a salvage unit of this [post](https://twitter.com/greentheonly/status/1261456934840008719?s=20) kindly shared by [@greentheonly](https://twitter.com/greentheonly).

![snapshot_interaction](data/snapshot_interaction.gif)

## Getting started
To try out the example notebooks or modules, set up a conda environment using the environment.yml file and start jupyter inside the notebooks directory.

```bash
conda env create -f environment.yml  # This can take a while
conda activate teslalogs
cd notebooks
jupyter-lab 
```
