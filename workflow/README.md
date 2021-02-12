## before running:
1. Install snakemake by using conda:  
	source {your_dir}/miniconda3/etc/profile.d/conda.sh  
	conda activate MF  
	conda install -c bioconda -c conda-forge snakemake  
2. Soft-link all cases ({subject}_{sample}.vcf, {subject}_{sample}.???, {subject}.csv) files under the "input" directory
3. Change all directory names and fasta file names in workflow/config.yml

## generate your pipeline figure:
snakemake --dag -np |dot -Tpng > pipeline.png

## dry run test:
snakemake -np

## actual run:
snakemake

## run on slurm:
source {your_dir}/miniconda3/etc/profile.d/conda.sh
conda activate MF
snakemake --unlock
snakemake --rerun-incomplete -j {job_num} --latency-wait 120 --cluster-config slurm.json --cluster "sbatch -p {queue} --account={accountID} -c 1 -t 2-12:00 --mem=5000 -o logs/%j.out -e logs/%j.err "