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

    nuclide_file = get_nuclide_paths(endf_path, [nuclide])[0]
    out_dir = Path(f"ND_sample").resolve()
    out_dir.mkdir(exist_ok=True)
    ace_stem="ace_{}_rand".format(nuclide)
    acetape = os.path.join(out_dir, ace_stem)

    # Run sandy
    sandy_command = "python3 -m sandy.sampling {} --samples 1 --outname {} --S33 {} --mf 33 --acer --temperature {}".format(nuclide_file,acetape,seed33,temperature)
    log_file = "sandy_sample_log_{}_{}_{}.out".format(nuclide,seed33,temperature)
    err_file = "sandy_sample_log_{}_{}_{}.err".format(nuclide,seed33,temperature)
    args = shlex.split(sandy_command)
    process = subprocess.Popen(args,stdout=log_file,stderr=err_file)

    # Check for success/failure (handle exception if process hangs)
    try:
        outs, errs = process.communicate(timeout=300)
        rc = process.returncode
    except TimeoutExpired:
        process.kill()
        outs, errs = process.communicate()

    # Sandy failed!
    if rc!=0:
        error_msg="Sandy failed to sample for nuclide: {} seed33: {} temperature: {}".format(nuclide,seed33,temperature)
        raise ChildProcessError(error_msg)

    fileOut = out_dir / f"{nuclide}_rand.h5"
    data = openmc.data.IncidentNeutron.from_ace(acetape + ".02c")
    data.name = f"{nuclide}_rand"

    # TODO Handle expecption here as well
    data.export_to_hdf5(fileOut, "w")

    random_nuc = RandomData(nuclide, data.name, fileOut)

    return random_nuc
