import os
import uuid
import pylab as plt
import matplotlib
from IPython.display import display, HTML, Image

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.sandbox.stats.multicomp import multipletests
from sklearn.decomposition import PCA

from rpy2.robjects.packages import importr
from rpy2 import robjects
from rpy2.robjects import Formula
from rpy2.robjects import pandas2ri

from linker.constants import GROUP_COL

pandas2ri.activate()

deseq = importr('DESeq2')
grdevices = importr('grDevices')


def to_pd_df(r_df):
    pd_df = pandas2ri.ri2py_dataframe(r_df)
    pd_df.index = r_df.rownames
    return pd_df


def run_deseq(count_data, col_data, keep_threshold, case, control):
    design = Formula("~ group")
    dds = deseq.DESeqDataSetFromMatrix(countData=count_data, colData=col_data, design=design)
    sv = robjects.StrVector(col_data[GROUP_COL].values)
    condition = robjects.FactorVector(sv)
    runs = col_data.index
    rstring = """
        function(dds, condition, runs, keepThreshold, case, control) {
            # collapse technical replicates
            dds$condition <- condition
            dds$condition <- relevel(dds$condition, ref=control) # set control    
            dds$sample <- runs 
            dds$run <- runs        
            ddsColl <- collapseReplicates(dds, dds$sample, dds$run) 
            # count filter
            keep <- rowSums(counts(ddsColl)) >= keepThreshold
            ddsColl <- ddsColl[keep,]
            # run DESeq2 analysis
            ddsAnalysis <- DESeq(dds)
            res <- results(ddsAnalysis, contrast=c("group", control, case))
            resOrdered <- res[order(res$padj),]  # sort by p-adjusted values
            df = as.data.frame(resOrdered)
            rld <- as.data.frame(assay(rlog(dds, blind=FALSE)))
            list(df, rld, resOrdered)
        }
    """
    rfunc = robjects.r(rstring)
    results = rfunc(dds, condition, runs, keep_threshold, case, control)
    pd_df = to_pd_df(results[0])
    rld_df = to_pd_df(results[1])
    res_ordered = results[2]
    return pd_df, rld_df, res_ordered


def run_ttest(count_data, col_data, case, control):
    count_data = count_data.replace(0, 1) # replace 0 with a small number
    sample_group = col_data[col_data[GROUP_COL] == case]
    case_data = count_data[sample_group.index]
    sample_group = col_data[col_data[GROUP_COL] == control]
    control_data = count_data[sample_group.index]

    nrow, _ = count_data.shape
    pvalues = []
    lfcs = []
    for i in range(nrow):

        # T - test for the means of two independent samples.
        case_df = case_data.iloc[i, :]
        control_df = control_data.iloc[i, :]
        statistics, pvalue = stats.ttest_ind(np.log(case_df), np.log(control_df)) #

        # log2 FC (case/control)
        case_avg = np.log(np.mean(case_df.values))
        control_avg = np.log(np.mean(control_df.values))
        lfc = case_avg - control_avg
        pvalues.append(pvalue)
        lfcs.append(lfc)

    # correct p-values
    reject, pvals_corrected, _, _ = multipletests(pvalues, method='fdr_bh')
    result_df = pd.DataFrame({
        'padj': pvals_corrected,
        'log2FoldChange': lfcs
    }, index=count_data.index)
    return result_df


def plot_notebook(rfunc, res):
    fn = '{uuid}.png'.format(uuid = uuid.uuid4())
    grdevices.png(fn)
    rfunc(res)
    grdevices.dev_off()
    return Image(filename=fn)


def plot_pca(rld_df, n_components):
    df = rld_df.transpose()
    pca = PCA(n_components=n_components)
    X = pca.fit_transform(df)

    fig, ax = plt.subplots()
    ax.scatter(X[:, 0], X[:, 1])
    for i, txt in enumerate(df.index):
        ax.annotate(txt, (X[i, 0], X[i, 1]))
    plt.tight_layout()
    fn = '{uuid}.png'.format(uuid = uuid.uuid4())
    plt.save(fn)

    cumsum = np.cumsum(pca.explained_variance_ratio_)
    return cumsum
