## before running:
1. Soft-link all cases ({sample}.vcf, {sample}.???, {subject}.csv) files under the "input" directory
2. Change all directory names and fasta file names in workflow/config.yml

## generate your pipeline figure:
snakemake --dag -np |dot -Tpng > pipeline.png

## dry run test:
snakemake -np

## actual run:
snakemake --cores {# cores}

## run on slurm:
source {your_dir}/miniconda/etc/profile.d/conda.sh
conda activate bmi5730
snakemake --unlock
snakemake --rerun-incomplete -j {job_num} --latency-wait 120 --cluster-config slurm.json --cluster "sbatch -p {queue} --account={accountID} -c 1 -t 2-12:00 --mem=5000 -o logs/%j.out -e logs/%j.err "
