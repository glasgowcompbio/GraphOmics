Sys.setenv(LANG = "en")

library(MOFA2)
library(MOFAdata)
library(data.table)
library(ggplot2)
library(tidyverse)
library(Seurat)
library("optparse")


option_list = list(
  make_option(c("-o", "--path"), type="character", default=NULL,
              help="output file path", metavar="character"),
  make_option(c("-f", "--file"), type="character", default=NULL,
              help="dataset file name", metavar="character"),
  make_option(c("-d", "--sample_matadata"), type="character", default=NULL,
              help="matadata file path", metavar="character"),
  make_option(c("-t", "--plot_type"), type="character", default=NULL,
              help="plot type to make", metavar="character"),
  make_option(c("-x", "--factor"), type="integer", default=NULL,
              help="factor to plot", metavar="character"),
  make_option(c("-y", "--to_factor"), type="integer", default=NULL,
              help="end of factor range", metavar="character"),
  make_option(c("-v", "--view"), type="character", default=NULL,
              help="view to plot", metavar="character"),
  make_option(c("-c", "--covariance"), type="character", default=NULL,
              help="covariances to plot", metavar="character"),
  make_option(c("-u", "--method"), type="character", default=NULL,
              help="dimension reduction method", metavar="character")
)

opt_parser = OptionParser(option_list=option_list);
opt = parse_args(opt_parser)

filepath = opt$file
model <- load_model(filepath)

if (!is.null(opt$sample_matadata)){
    metadata <- read.table(file = opt$sample_matadata, sep = ',', header = TRUE, check.names = FALSE)
    stopifnot(all(sort(metadata$sample)==sort(unlist(samples_names(model)))))
    samples_metadata(model) <- metadata
}


if (opt$plot_type == "data_overview") {
  figure = plot_data_overview(model)

  path = paste(opt$path, "data_overview.png", sep="_")
  png(path, height=400, width=600, pointsize=0.8)
  print(figure)
  dev.off()
}


if (opt$plot_type == "correlate_factors_with_covariates") {
  covariances = colnames(metadata)
  figure = correlate_factors_with_covariates(model,
                                             plot="log_pval",
                                             covariates = covariances)

  path = paste(opt$path, "correlate_factors_with_covariates.png", sep="_")
  png(path, height=500, width=600, pointsize=0.8)
  print(figure)
  dev.off()
}


if (opt$plot_type == "factor_combination_plot") {
  figure = plot_factors(model,
                        factors = c(opt$factor,opt$to_factor),
                        color_by = opt$covariance,
                        shape_by = 'group'
  )

  path = paste(opt$path, opt$covariance, opt$factor, opt$to_factor, "factor_combination_plot.png", sep="_")
  png(path, height=500, width=600, pointsize=0.8)
  print(figure)
  dev.off()
}


if (opt$plot_type == "boxplot") {
  figure = plot_factor(model,
                       factors = opt$factor:opt$to_factor,
                       color_by = opt$covariance,
                       add_violin = TRUE,
                       dodge = TRUE
  )

  path = paste(opt$path, opt$covariance, opt$factor, opt$to_factor, "boxplot.png", sep="_")
  png(path, height=500, width=600, pointsize=0.8)
  print(figure)
  dev.off()
}

if (opt$plot_type == "dimension_reduction" && opt$method == 'TSNE') {
  model <- run_tsne(model)
  figure = plot_dimred(model,
                       method = "TSNE",
                       color_by = opt$covariance,
                       shape_by = 'group'
  )

  path = paste(opt$path, opt$covariance, opt$method, "dimension_reduction.png", sep="_")
  png(path, height=500, width=600, pointsize=0.8)
  print(figure)
  dev.off()
}

if (opt$plot_type == "dimension_reduction" && opt$method == 'UMAP') {
  model <- run_umap(model)
  figure = plot_dimred(model,
                       method = "UMAP",
                       color_by = opt$covariance,
                       shape_by = 'group'
  )

  path = paste(opt$path, opt$covariance, opt$method, "dimension_reduction.png", sep="_")
  png(path, height=500, width=600, pointsize=0.8)
  print(figure)
  dev.off()
}


if (opt$plot_type == "heatmap") {
  figure = plot_data_heatmap(model,
                             view = opt$view,
                             factor = opt$factor,
                             features = 20,
                             denoise = TRUE,
                             cluster_rows = TRUE, cluster_cols = TRUE,
                             show_rownames = TRUE, show_colnames = FALSE,
                             scale = "row"
  )
  path = paste(opt$path, opt$view, opt$factor, "heatmap.png", sep="_")
  png(path, height=500, width=600, pointsize=0.8)
  print(figure)
  dev.off()
}







