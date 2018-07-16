import os
import uuid
import pylab as plt
import matplotlib
from IPython.display import display, HTML, Image

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from rpy2.robjects.packages import importr
from rpy2 import robjects
from rpy2.robjects import Formula
from rpy2.robjects import pandas2ri
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
    sv = robjects.StrVector(col_data['group'].values)
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
