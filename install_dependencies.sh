#!/bin/bash

export PATH=$PATH:$(pwd)

# Ensure Conda is installed
if conda | grep -q "conda is a tool"; then
    echo "conda already installed"

else
    echo "installing conda"
    wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
    chmod +x ~/miniconda.sh
    bash ~/miniconda.sh -b -f -p ~/miniconda
fi

export PATH=$PATH:/home/ubuntu/miniconda/bin/
source ~/miniconda/etc/profile.d/conda.sh
conda env create -f conda_environment.yml
conda activate bmi5730

# Remove conda installer
rm ~/miniconda.sh


# Install ANNOVAR resources
cd ~/bmi5370/workflow/annovar
mkdir humandb
perl annotate_variation.pl --downdb --buildver hg19 refGene humandb
perl annotate_variation.pl --buildver hg19 --downdb seq humandb/hg19_seq
perl retrieve_seq_from_fasta.pl humandb/hg19_refGene.txt --seqdir humandb/hg19_seq/chroms --format refGene --outfile humandb/hg19_refGeneMrna.fa
