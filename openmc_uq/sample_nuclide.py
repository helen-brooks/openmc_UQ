# %% Imports
import os
import shlex
import subprocess
import openmc.data
from pathlib import Path
from .utils import get_nuclide_paths

class RandomData:
    def __init__(self, nuclide, perturbed_name, path):

        self.nuclide = nuclide
        self.perturbed_name = perturbed_name
        self.path = path


def sample_nuclide_sandy(nuclide, endf_path, seed33, temperature=293.6):

    # Define data files
    nuclide_file = get_nuclide_paths(endf_path, [nuclide])[0]
    out_dir = Path(f"ND_sample").resolve()
    out_dir.mkdir(exist_ok=True)
    ace_stem="ace_{}_rand".format(nuclide)
    acetape = os.path.join(out_dir, ace_stem)


    # Define sandy run command
    sandy_command = "python3 -m sandy.sampling {} --samples 1 --outname {} --S33 {} --mf 33 --acer --temperature {}".format(nuclide_file,acetape,seed33,temperature)
    args = shlex.split(sandy_command)

    # Open log files and run
    log_stem= "sandy_{}_{}".format(nuclide,seed33)
    out_file= os.path.join(out_dir, log_stem+".out")
    err_file = os.path.join(out_dir, log_stem+".err")
    with open(out_file, 'w') as fout:
        with open(err_file, 'w') as ferr:
            process = subprocess.run(args,stdout=fout,stderr=ferr)

    #fout = open(out_file, 'w'):
    #ferr = open(err_file, 'w'):

    #stdout = process.stdout
    #stderr = process.stderr

    ## Obtain return code (kill if program hangs)
    #try:
    #    stdout, stderr = process.communicate(timeout=300)
    #    rc = process.returncode
    #except TimeoutExpired:
    #    process.kill()
    #    stdout, stderr = process.communicate()

    # Close log file handles
    #f.write(stdout)

    # Check for success/failure, raise CalledProcessError on fail#
    process.check_returncode()
    #if rc!=0:
    #    error_msg="Sandy failed to sample for nuclide: {} seed33: {} temperature: {}".format(nuclide,seed33,temperature)
    #    raise ChildProcessError(error_msg)

    file_out=os.path.join(out_dir,f"{nuclide}_rand.h5")
    data = openmc.data.IncidentNeutron.from_ace(acetape + ".02c")
    data.name = f"{nuclide}_rand"

    # TODO Handle expecption here as well
    data.export_to_hdf5(file_out, "w")

    random_nuc = RandomData(nuclide, data.name, file_out)

    return random_nuc
