# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %%
import sys
import pickle
import pandas as pd
import holoviews as hv
import panel as pn
from pathlib import Path
from collections import namedtuple

if '..' not in sys.path:
    sys.path.append('..')  # Ugly hack to allow imports below to work
from teslalogs.signals import SignalViewer, decode_log_signal, ModelSXLogviewer
from teslalogs.utils import read_dbc, read_jsons

hv.extension('bokeh')
# %load_ext autoreload
# %autoreload 2

# %%
mapped_sig = namedtuple('mapped_sig', 'bus message signal byte_order scale offset choices unit') # Required for loading the matches pickle file
matches_path = Path('../data/2018.20.mcu2_matches.pickle')
matches = pickle.loads(matches_path.read_bytes())

# %%
store_path = Path('/tmp/store.h5') # You should set this
sd_log_path = Path('/tmp/SD/LOG')  # And this

# Extract log section of interest
# ! python ../teslalogs/model_sx/extract_log.py --force -dtmin 2016,5,30 -dtmax 2016,6,10 {sd_log_path} {store_path}

# %%
with pd.HDFStore(store_path) as store:
    logged_ids = [x[2:] for x in store.keys()]  # strip the leading '/_'
matched_log_ids = set(matches.keys())
log_ids_shown = list(sorted(set(logged_ids) & matched_log_ids))
matches = {log_id: matches[log_id] for log_id in log_ids_shown}  # Filter out anything not present in the log

# %%
viewer = ModelSXLogviewer(store_path, matches, plot_type='Curve')
# The viewer will default to translating enum values to their corresponding strings and also switching to a better suiting interpolation (steps-post)
# In some situations this is not helpful, and you'll want to manually override it using the checkboxes
viewer.nbview()


# %%
# Search for strings in matches
# There is a panel autocomplete widget, but it only matches at start of strings, this will look for any substring as quick fix
def search_term(term):
    term = term.lower()
    for log_id, match in matches.items():
        if (term in match.bus.lower() or 
            term in match.message.lower() or 
            term in match.signal.lower() or
            (match.choices and any(term in choice.lower() for choice in match.choices.values()))):
            print(log_id, match)
            


# %%
search_term('speed')

# %%
di_speed = viewer.get_plot('0xd0021161')
di_brake = viewer.get_plot('0xd000710c')
esp_brake = viewer.get_plot('0xd00216e8')
gtw_brake = viewer.get_plot('0xd0004aec')

# %%
(di_speed + di_brake + esp_brake).cols(1).opts({'Curve': {'height': 200}})

# %%

# %%
