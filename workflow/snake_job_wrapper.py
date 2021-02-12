from __future__ import print_function
import os
import sys
import argparse
import yaml
import gzip
import shutil
import subprocess
from copy import deepcopy
import datetime

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

"""
Tries to make the input string to be safe for filepaths
and for use in filenames.
"""
def safeString(input_str, warn=True):
    output = []
    for char in input_str.replace(" ", "_"):
        if char.isalnum():
            output.append(char)
        elif char in ['.', '_', '-']:
            output.append(char)
    output = "".join(output).replace("__", "_")
    if input_str != output and warn:
        eprint(f"Warning: \"{input_str}\" was converted to safer \"{output}\" format.")
    return output
    # end safeString()


"""
Creates the YAML config file for Snakemake
based on the template file.
"""
def create_config(fastqs, movies, output_dir, sample_name, n_chunks, genome_version, conda_env, sensitive_mode=False):
    pipeline_dir    = os.path.dirname(os.path.realpath(__file__))
    source          = os.path.join(pipeline_dir, "templates/config.yaml.template")
    dest            = os.path.join(output_dir, "config.yaml")
    with open(source, "r") as filein:
        data = yaml.safe_load(filein)

        data["conda_env"]           = conda_env
        data["fastqs"]              = fastqs
        data["movies"]              = movies
        data["sample"]              = sample_name
        data["input_split_count"]   = n_chunks

        if genome_version not in data["genome"]["versions"]:
            eprint(f"Error: Filepaths for genome version \"{genome_version}\" not found in config file.")
            sys.exit(1)

        data['genome']['version'] = genome_version
        for key in ['fasta', 'mmi', 'pbmm2']:
            if key not in data['genome']["versions"][genome_version]:
                eprint(f"Missing definition {key} for genome.")
                sys.exit(1)
            filepath = os.path.join(pipeline_dir, data['genome']["versions"][genome_version][key])
            if not os.path.isfile(filepath):
                eprint(f"Genome reference file {filepath} missing.")
                sys.exit(1)
            data['genome'][key] = filepath

        del data['genome']['versions']

        keys = data["scripts"].keys() # prefect to avoid editing while iterating
        for key in keys:
            filepath = os.path.join(pipeline_dir, data["scripts"][key])
            if not os.path.isfile(filepath):
                eprint(f"Script {filepath} missing.")
                sys.exit(1)
            data['scripts'][key] = filepath

        # Dropping clair out of the pipeline (for now?)
        #filepath = os.path.join(pipeline_dir, data["clair"]["model"])
        #if not os.path.isfile(filepath + ".index"):
        #    eprint(f"Clair model {filepath} missing.")
        #    sys.exit(1)
        #data['clair']['model'] = filepath

        # SV calling settings
        sv_params = data['sv']
        if sensitive_mode:
            data['sv'] = sv_params['sensitive']
        else:
            data['sv'] = sv_params['default']

        # Write out the updated config file in the output dir
        with open(dest, "w") as fileout:
            yaml.dump(data, fileout)
    return True
    # end create_config()

def create_job(output_folder, sample, threads=96, conda_env="hifi"):
    snakemake_jobname   = f"{sample}.{{rule}}.{{jobid}}"
    jobs_file   = os.path.join(output_folder, "run_pipeline.sh")
    error_file  = os.path.join(output_folder, "pipeline.err")
    log_file    = os.path.join(output_folder, "pipeline.log")
    logdir      = os.path.join(output_folder, "99_logs")
    contents    = []
    contents.append(f"#$ -N HiFi-{sample}")
    contents.append(f"#$ -pe smp 1") # only request 1 thread since this is just for the Snakemake runner
    contents.append(f"#$ -o {log_file}")
    contents.append(f"#$ -e {error_file}")
    contents.append("")
    contents.append(". ~/.bashrc")
    contents.append(f"conda activate {conda_env}")
    contents.append(f"cd {output_folder}")
    contents.append(f"mkdir -p {logdir}")
    contents.append(f"snakemake --cores {threads} -c \"qsub -pe smp {{threads}} -o {logdir} -e {logdir}\" --jobname {snakemake_jobname}")
    with open(jobs_file, "w") as fileout:
        for line in contents:
            fileout.write(f"{line}\n")
    fileout.close()
    return jobs_file
    # end create_job()


"""
Extracts the unique movie names from the input FASTQs.
The movie names are used for parallelization in the pipeline.
"""
def extract_movie_names(input_files):
    movie_names = set()
    for filepath in input_files:
        eprint(f"Identifying movie names from input file {filepath} ...")
        # If the file already has a .fai index, scanning through it
        # rather than the entire FASTQ file is going to be a lot faster.
        index_filepath = f"{filepath}.fai"
        if os.path.isfile(index_filepath):
            # Index exists, use it instead.
            eprint(f"Found index for {filepath}, using it instead ...")
            for movie_name in extract_movie_names_from_fai(index_filepath):
                movie_names.add(movie_name)
        else:
            # No index, have to scan through file
            for movie_name in extract_movie_names_from_fastq(filepath):
                movie_names.add(movie_name)            

    movie_names = [m for m in sorted(movie_names)]
    eprint("Identified the following:")
    for m in movie_names:
        eprint(f"- {m}")
    return movie_names
    # end extract_movie_names()


"""
Extracts movie names from the FASTQ(.gz) file, returning
them as a set.
"""
def extract_movie_names_from_fastq(filepath):
    movie_names = set()
    if filepath.endswith(".gz") or filepath.endswith(".bgz"):
        open_fn     = gzip.open
        open_mode   = "rb"
        decode      = True
    else:
        open_fn     = open
        open_mode   = "r"
        decode      = False

    ln = 0
    with open_fn(filepath, open_mode) as filein:
        for line in filein:
            if ln == 0:
                line = line.strip()
                if decode:
                    line = line.decode("utf-8")
                movie_name = line[1:].split("/")[0]
                movie_names.add(movie_name)
            ln += 1
            if ln > 3:
                ln = 0
        filein.close()    
    return movie_names
    # end extract_movie_names_from_fastq()

"""
Extracts movie names from the FASTQ index (.fai) file,
returning them as a set.
"""
def extract_movie_names_from_fai(filepath):
    movie_names = set()
    open_fn     = open
    open_mode   = "r"
    decode      = False

    with open_fn(filepath, open_mode) as filein:
        for line in filein:
            line = line.strip()
            if len(line):
                movie_name = line.split("\t")[0].split("/")[0]
                movie_names.add(movie_name)
        filein.close()    
    return movie_names
    # end extract_movie_names_from_fai()



if __name__ == "__main__":
    script_name = 'HiFi Analysis Pipeline: Run Creator'
    parser = argparse.ArgumentParser(description=script_name)
    parser.add_argument('--fastq', dest='fastq', type=str, 
        nargs='+',
        required=True,
        help='Filepath to FASTQ(.gz) file(s) with HiFi CCS reads')
    parser.add_argument('--sample-name', dest='sample_name', type=str,
        required=True,
        help='Sample name for outputs') 
    parser.add_argument('--output', dest='output', type=str,
        required=True,
        help='Output directory')
    parser.add_argument('--n-chunks', dest='n_chunks', type=int,
        default=8,
        help='Number parallel alignment chunks to split each input into (default: 8)')
    parser.add_argument('--sensitive', dest='sensitive_mode', action='store_true',
        help='Use more sensitive parameters for SV calling')
    parser.add_argument('--use-37', dest='use_37', action='store_true',
        help='Use hg19/b37 instead of GRCh38/hs38')
    parser.add_argument('--conda-env', dest='conda_env', type=str,
        default='hifi',
        help='conda environment name (default: hifi)')    
    parser.add_argument('--no-queue', dest='no_queue', action='store_true',
        help='Do not submit jobs to SGE queue')
    args = parser.parse_args()

    
    fastq_files             = []
    for filepath in args.fastq:
        filepath = os.path.abspath(filepath)
        if not os.path.isfile(filepath):
            eprint(f"Error: {filepath} does not exist!")
            sys.exit(1)
        fastq_files.append(filepath)

    if len(fastq_files) is 0:
        eprint("Error: No input FASTQs specified!")
        sys.exit(1)

    sample_name         = safeString(args.sample_name)
    output_dir          = os.path.abspath(args.output)
    n_chunks            = int(args.n_chunks)
    sensitive_mode      = args.sensitive_mode
    conda_env           = safeString(args.conda_env)
    if args.use_37:
        genome_version  = '37'
    else:
        genome_version  = '38'

    if n_chunks < 1:
        eprint("Error: Cannot split input into less than 1 chunk.")
        sys.exit(1)

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
        eprint(f"Info: Created output folder {output_dir}")

    movies              = extract_movie_names(fastq_files)


    """
    Generate the config file for this run.
    """
    create_config(fastq_files, movies, output_dir, sample_name, n_chunks, genome_version, conda_env, sensitive_mode)

    """
    Copy Snakefile to new destination
    """
    pipeline_dir        = os.path.dirname(os.path.realpath(__file__))
    snakefile_source    = os.path.join(pipeline_dir, "templates/Snakefile.template")
    snakefile_dest      = os.path.join(output_dir, "Snakefile")
    shutil.copyfile(snakefile_source, snakefile_dest)

    """
    Create job file and submit it to the SGE queue.
    """
    job_file            = create_job(output_dir, sample_name, conda_env=conda_env)
    if not args.no_queue:
        subprocess.run(["qsub", job_file], cwd=output_dir)

    # end __main__