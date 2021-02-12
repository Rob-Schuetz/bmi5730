# Bmi5370
This repository serves as a pipeline for extracting inputs from WES, RNAseq and clinical data and passing them to a deep learning algorithm to uncover associations with treatment outcomes.
The baseline data is provided from the ORIEN network; description provided from oriencancer.org:
"The Oncology Research Information Exchange Network (ORIEN) is an alliance of cancer centers, powered by M2GEN, working in close collaboration to accomplish more in the fight against cancer."
Ohio State has submitted ~2,000 cases to the ORIEN network, and these cases are available for us to study.
The ORIEN data will be used as the "test" set, TCGA will be used as the "training" set.  The cancer cases will be divided by disease site, training and testing will be disease site specific.

## Inputs
Input files for WES, RNAseq and clinical data must follow specific naming conventions.  By default, input directories are set up in the "input" directory, which is located in the repository root.

Current file formats for each are data type:
    WES: {subject}_{sample}.vcf
    RNAseq: {subject}_{sample}.???
    Clinical: {subject}.csv

Useful upstream information for ORIEN .vcf files:
    Aligner: Mutect2
    Filtering: GNOMAD v3
    Build: hg19 (to be updated to hg38 in the near future)
    Panel of Normals: ORIEN has a PON that has been used to filter out sequencing artifacts

## Outputs
Best performing deep learning models for predicting treatment outcome.