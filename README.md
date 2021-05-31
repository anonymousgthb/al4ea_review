# al4ea_review

## Steps of reproducing the experiments:

- Step 1: Download the repo and put unzipped project to directory `/path/to/proj/`.
- Step 2: If you need to run our strategies on RDGCN, you need to download the open word embedding file 
from [wiki-news-300d-1M.vec](https://dl.fbaipublicfiles.com/fasttext/vectors-english/wiki-news-300d-1M.vec.zip) 
and put the unzipped file under `dataset/`.
Otherwise you can skip this step (BTW, the size of unzipped word embedding file will be 2.26GB).
- Step 3: Install conda environment
```shell script
cd /path/to/proj/al4ea_review/
conda env create -f environment.yml
```

- Step 4: Setting configuration.
The scripts to run are under `scripts/run_strategies/`
The default settings are set in `task_settings.sh`. Before you run any script, set `proj_dir` in the setting file firstly. 
`proj_dir` is like `/path/to/proj/al4ea_review/`.

- Step 5: Run scripts:
    * For trials: customizing script `task_runner_trial.sh`.
    * Run experiments about the "overall performance on 15K data": `task_runner_overall_perf.sh`.
    * Run experiments about the "overall performance on 15K data": `task_runner_overall_perf_100k.sh`.
    * Run experiments about the "effect of bachelors": `task_runner_effect_of_bachelor_percent.sh`.
    * Run experiments about the "effectiveness of bachelor recognizer": intermediate results have been saved with the generated dataset of ActiveEA. 
    For example, its path may be like 
    `dataset/1011/overall_perf/D_W_15K_V1_BACH0.3_Alinet/STRUCT_UNCER_BACH_RECOG_CV_alpha0.1_batchsize100/temp/bach_recog_cv/`.
    * Run experiments about the "sensitivity of parameters": `task_runner_effect_of_alpha.sh` and `task_runner_effect_of_batchsize.sh`.

The generated datasets by different AL strategies will be saved to `dataset/` with naming pattern like `dataset/${seed}/${task_group}/${dataset_name}/${strategy_name}`. 
The evaluation results on test set will be saved to `output/results/`. 

- Step 6: draw plots.
You can draw the plots with python script `al4ea/result/plot_overperf.py`.







 





