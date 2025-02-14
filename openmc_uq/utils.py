import numpy as np
import os
import re
import warnings
from pathlib import Path
from sandy import Endf6
import openmc

###
#   Pattern matches nuclides with ENDF files, and returns their path
###
def get_nuclide_paths(endf_path, nuclides):
    file_list = np.array(os.listdir(endf_path))

    if len(file_list) == 0:
        raise OSError(f"{endf_path} is empty")

    nuclide_paths = []

    for (i, nuc) in enumerate(nuclides):
        atomic_sym = " ".join(re.findall("[a-zA-Z]+", nuc))
        mass_num = " ".join(re.findall(r'\d+', nuc))

        atomic_in = np.array([atomic_sym in files for files in file_list])
        mass_in = np.array([mass_num in files for files in file_list])

        this_file = file_list[atomic_in * mass_in]

        if len(this_file) == 0:
            nuclide_paths.append("")
            raise OSError(f"No files matched for {nuc}")

        elif len(this_file) == 1:
            nuc_path = endf_path + '/' + this_file[0]
            nuclide_paths.append(nuc_path)
            print(f"Using {this_file[0]} for {nuc}")
            print("\n")

        elif len(this_file) > 1:
            shortest = min(this_file, key=len)
            nuclide_paths.append(endf_path + '/' + shortest)
            warning_message=f"Multiple files matched for {nuc}: {this_file}"
            warning_message=warning_message+f"Using shortest: {shortest}"
            warnings.warn(warning_message)
            
    return nuclide_paths


###
#   Creates error and pendf files from endf file
###
def process_with_njoy(Nuclide, endf_path):

    FILE = get_nuclide_paths(endf_path, [Nuclide])[0]

    endf6 = Endf6.from_file(FILE)

    if len(endf6.mat) == 1:
        MAT = endf6.mat[0]
    else: 
        raise ValueError("ENDF file conatains multiple nuclides (MAT) numbers. Function only allows for files containing a single nuclide")

    error = endf6.get_errorr(
        err=0.001,
        irespr=0
    )['errorr33']

    pendf = endf6.get_pendf(err=0.001, verbose=True)
    
    return error, pendf


##
#   Replaces the nuclides in mat.xml with the random nuclides of NuclideStream
#   Returns openmc materials object with changed nuclides
##
def replace_string_in_file(nuc, newNuc,filename,cwd=None):
    if not cwd:
        cwd=os.getcwd()

    file_orig=os.path.join(cwd,filename)
    file_tmp=os.path.join(cwd,"tmp"+filename)
    fin = open(file_orig, "rt")
    fout = open(file_tmp, "wt")

    for line in fin:
        #read replace the string and write to output file
        fout.write(line.replace(nuc, newNuc))
    
    fin.close()
    fout.close()
    os.remove(file_orig)
    os.rename(file_tmp,file_orig)
