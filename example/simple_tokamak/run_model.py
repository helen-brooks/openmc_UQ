#!/usr/bin/env python
import argparse
import json
import os
import sys
import warnings
from glob import glob
from multiprocessing import Pool
from pathlib import Path
import openmc
import openmc_uq


def results_from_statepoint(scores):
    # Lift tallies from statepoint file
    n_max_batches=0
    template=run_dir+'/statepoint.*.h5'
    files=glob(template)
    file_to_open=""
    for filename in files:
        stem=filename.replace('.h5','')
        n_batches=int(stem.replace('statepoint.',''))
        if n_batches > n_max_batches:
            n_max_batches=n_batches
            file_to_open=filename


    print("Opening statepoint file: ",file_to_open)
    sp = openmc.StatePoint(file_to_open)

    results=[]
    errors=[]
    for score in scores:
        tally = sp.get_tally(name=score)
        df = tally.get_pandas_dataframe()
        mean = df['mean'].sum()
        std = df['std. dev.'].sum()
        results.append(mean)
        errors.append(std)

    return results,errors

parser = argparse.ArgumentParser()
parser.add_argument("input_file")
args = parser.parse_args()

print("Configuring from: ", args.input_file)
inputs_dict={}
with open(args.input_file) as handle:
    inputs_dict = json.load(handle)

# Random seeds (one for each nuclide)
seeds = inputs_dict["seeds"]

# Nuclides to sample
nuclides = inputs_dict["nuclides"]

# ENDF directory. Used to generate random data.
endf_path = inputs_dict["endf_dir"]

# Directory of openmc model.
openmc_xml_dir = inputs_dict["openmc_xml_dir"]

# Local directory name to run in
run_dir = inputs_dict["run_dir"]

# XS library.
XS_LIB = inputs_dict["cross_section_path"]

# Scores to extract
scores = inputs_dict["scores"]

# File to save to
output = inputs_dict["output"]

# Number threads / workers / cores
n_cores = int(inputs_dict["n_cores"])

# Generate random HDF5 file of "nuclides".
# Parallel using simple multiprocessing
print(f"Sampling sandy with n_cores={n_cores}")

print("Beginning NJOY processing")
with Pool(n_cores) as pool:
    random_nuc = []
    for (i, nuc) in enumerate(nuclides):

        func_args = (nuc, endf_path, int(seeds[i]))
        try:
            RN = pool.apply_async(openmc_uq.sample_nuclide_sandy, func_args)
            random_nuc.append(RN)
        except ChildProcessError:
            warnings.warn("Failed to sample nuclide {}".format(nuc))

    for r in random_nuc:
        r.wait()

    for (i, r) in enumerate(random_nuc):
        random_nuc[i] = r.get()

# Run openmc with random files
try:
    openmc_uq.run_openmc(openmc_xml_dir, random_nuc, cross_sections_xml=XS_LIB, threads=n_cores,run_dir=run_dir)
    results,errors = results_from_statepoint(scores)
    weight=1

except ChildProcessError(error_msg):
    # Handle failure
    results = [0.0 for score in scores]
    errors = [0.0 for score in scores]
    # Setting weight to zero means we won't count this run later
    weight=0

# Now write to file
result_str="{}".format(weight)
for i_score in range(len(scores)):
    mean=results[i_score]
    std=errors[i_score]
    tally_str = " {} {}".format(mean,std)
    result_str=result_str+tally_str

#   Store results of interest to openmc.out
with open(output, 'w') as f:
    f.write(result_str)
