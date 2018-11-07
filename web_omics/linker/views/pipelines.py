import uuid
import pylab as plt

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.sandbox.stats.multicomp import multipletests
from sklearn.decomposition import PCA
from sklearn import preprocessing

from rpy2.robjects.packages import importr
from rpy2 import robjects
from rpy2.robjects import Formula
from rpy2.robjects import pandas2ri

from linker.constants import GROUP_COL, IDS, PKS


class WebOmicsInference(object):
    def __init__(self, data_df, design_df, data_type, remove_cols=None, min_value=0):

        data_df = data_df.copy()

        # remove all the default columns from dataframe if nothing provided
        if remove_cols is None:
            remove_cols = ['padj_', 'FC_', 'significant_', 'obs', PKS[data_type], IDS[data_type]]
        remove_cols = tuple([x.lower() for x in remove_cols])
        to_drop = list(filter(lambda x: x.lower().startswith(remove_cols), data_df.columns))
        df = data_df.drop(to_drop, axis=1)

        # remove rows that are all NAs and all 0s
        df = df.dropna(how='all')
        df = df.loc[~(df == 0).all(axis=1)]

        self.data_df = df
        self.design_df = design_df
        self.data_type = data_type

        # data imputation:
        # - if all zero in group then replace with min_value
        # - replace any other zeros with mean of group
        self._impute_data(min_value)

    def heatmap(self, N=None, standardize=True, log=False):
        if standardize:
            data_df = self.standardize_df(self.data_df, log=log)
        else:
            data_df = self.data_df
        if N is not None:
            plt.matshow(data_df[0:N])
        else:
            plt.matshow(data_df)
        plt.colorbar()

    def standardize_df(self, data_df, log=False):
        if data_df.empty:
            return data_df
        data_df = data_df.copy()
        scaled_data = np.array(data_df)
        if log:
            scaled_data = np.log(np.array(data_df))
        scaled_data = preprocessing.scale(scaled_data, axis=1)
        sample_names = data_df.columns
        data_df[sample_names] = scaled_data
        return data_df

    def run_deseq(self, keep_threshold, case, control):
        pandas2ri.activate()
        deseq = importr('DESeq2')
        design = Formula("~ group")
        count_data = self.data_df
        col_data = self.design_df
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
        pd_df = self._to_pd_df(results[0])
        rld_df = self._to_pd_df(results[1])
        res_ordered = results[2]
        return pd_df, rld_df, res_ordered

    def run_ttest(self, case, control):
        count_data = self.data_df
        col_data = self.design_df
        sample_group = col_data[col_data[GROUP_COL] == case]
        case_data = count_data[sample_group.index]
        sample_group = col_data[col_data[GROUP_COL] == control]
        control_data = count_data[sample_group.index]

        nrow, _ = count_data.shape
        pvalues = []
        lfcs = []
        indices = []
        for i in range(nrow):

            case = case_data.iloc[i, :].values
            control = control_data.iloc[i, :].values
            idx = count_data.index[i]

            # remove 0 values, which were originally NA when exported from PiMP
            case = case[case != 0]
            control = control[control != 0]

            # T-test for the means of two independent samples
            case_log = np.log2(case)
            control_log = np.log2(control)
            statistics, pvalue = stats.ttest_ind(case_log, control_log)
            if not np.isnan(pvalue):
                lfc = np.mean(case_log) - np.mean(control_log)
                pvalues.append(pvalue)
                lfcs.append(lfc)
                indices.append(idx)

        # correct p-values
        reject, pvals_corrected, _, _ = multipletests(pvalues, method='fdr_bh')
        result_df = pd.DataFrame({
            'padj': pvals_corrected,
            'log2FoldChange': lfcs
        }, index=indices)
        return result_df

    def get_pca(self, rld_df, n_components, plot=False):
        df = rld_df.transpose()
        pca = PCA(n_components=n_components)
        X = pca.fit_transform(df)

        if plot:
            fig, ax = plt.subplots()
            ax.scatter(X[:, 0], X[:, 1])
            for i, txt in enumerate(df.index):
                ax.annotate(txt, (X[i, 0], X[i, 1]))
            plt.tight_layout()
            fn = '{uuid}.png'.format(uuid=uuid.uuid4())
            plt.save(fn)

        cumsum = np.cumsum(pca.explained_variance_ratio_)
        return X, cumsum

    def _impute_data(self, min_value):
        if self.design_df is not None:
            grouping = self.design_df.groupby('group')
            for group, samples in grouping.groups.items():
                # If all zero in group then replace with minimum
                temp = self.data_df.loc[:, samples]
                temp = (temp == 0).all(axis=1)
                self.data_df.loc[temp, samples] = min_value

                # Replace any other zeros with mean of group
                subset_df = self.data_df.loc[:, samples]
                self.data_df.loc[:, samples] = subset_df.mask(subset_df == 0, subset_df.mean(axis=1), axis=0)

    def _to_pd_df(self, r_df):
        pd_df = pandas2ri.ri2py_dataframe(r_df)
        pd_df.index = r_df.rownames
        return pd_df