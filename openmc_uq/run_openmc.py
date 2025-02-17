import os
import shlex
import subprocess
from pathlib import Path
from shutil import copyfile
import openmc.data
from .utils import replace_string_in_file

def run_openmc(openmc_xml_dir, random_nuclides, cross_sections_xml,
               n_tasks=1,
               n_tasks_per_node=1,
               n_threads = 1,
               max_time=86400,
               run_dir="openmc_sim"):

    # ==============================================================================
    # Make openmc sim directory

    working_dir = os.getcwd()

    out_dir = Path(run_dir).resolve()
    out_dir.mkdir(exist_ok=True)

    openmc_xml_dir = Path(openmc_xml_dir).resolve()
    input_files  = ["materials.xml", "settings.xml", "tallies.xml", "geometry.xml"]

    for file in input_files:
        copyfile(openmc_xml_dir/file, out_dir/file)

    for file in os.listdir(openmc_xml_dir):
        if file.endswith(".h5m"):
            copyfile(openmc_xml_dir/file, out_dir/file)
        if file.endswith(".e"):
            copyfile(openmc_xml_dir/file, out_dir/file)

    # ==============================================================================
    # Create xml library
    lib = openmc.data.DataLibrary()
    lib = lib.from_xml(cross_sections_xml)  # Gets current

    for nuc in random_nuclides:
        # TODO check for correct type rather than just None
        if not nuc:
            raise TypeError("User provided nuclide has None type.")
        lib.register_file(nuc.path)

    post = out_dir / "cross_sections_rand.xml"
    lib.export_to_xml(post)

    # ==============================================================================
    # Change openmc inputs
    for inputfile in ["materials.xml","tallies.xml"]:
        for nuc in random_nuclides:
            replace_string_in_file(nuc.nuclide, nuc.perturbed_name, inputfile, out_dir)

    materials   = openmc.Materials.from_xml(out_dir /"materials.xml")
    materials.cross_sections = str(post)
    materials.export_to_xml(out_dir /"materials.xml")

    # Define openmc run command
    # TODO make aware of which mpi flavour! (ppn is intel)
    openmc_command = "mpirun -np {} -ppn {}  --bind-to none openmc -s {}".format(
        n_tasks,
        n_tasks_per_node,
        n_threads)
    args=shlex.split(openmc_command)

    # Open log files and run
    log_stem= "run_openmc"
    out_file = os.path.join(out_dir, log_stem+".out")
    err_file = "run_openmc.err"
    err_file = os.path.join(out_dir, log_stem+".err")
    with open(out_file, 'w') as fout:
        with open(err_file, 'w') as ferr:
            print("Running openmc in {}".format(out_dir))
            process = subprocess.run(args,stdout=fout,stderr=ferr,cwd=out_dir)

    # Check for success/failure, raise CalledProcessError on fail
    process.check_returncode()
