const path = require("path");
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = {
    context: __dirname,

    entry: {
        base: './static/js/base',
        submit_analysis: './static/js/submit_analysis',
        explore_data: './static/js/explore_data',
        summary: './static/js/summary',
        inference: './static/js/inference'
    },

    output: {
        filename: "[name]-[fullhash].js",
        path: path.resolve('./static/bundles/'),
    },

    plugins: [
        new BundleTracker({filename: './webpack-stats.json'}),
        new CleanWebpackPlugin({
            cleanAfterEveryBuildPatterns: ['/static/bundles']
        }),
        new MiniCssExtractPlugin({
            filename: "[name]-[fullhash].css",
            chunkFilename: "[id]-[chunkhash].css"
        }),
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            'window.jQuery': 'jquery',
            'window.$': 'jquery',
            d3: 'd3',
            _: "underscore"
        }),
    ],

    module: {
        noParse:[/alasql/],
        rules: [
            {
                test: /\.jsx?$/,
                exclude: /node_modules/,
                loader: 'babel-loader'
            },
            {
                test: /\.s?[ac]ss$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    { loader: 'css-loader', options: { url: false, sourceMap: true } },
                    { loader: 'sass-loader', options: { sourceMap: true } }
                ],
            },
            {
                test: /\.(svg|gif|png|eot|woff|ttf)$/,
                loader: 'url-loader'
            },
            {
                // for django-select2
                // https://stackoverflow.com/questions/47469228/jquery-is-not-defined-using-webpack
                test: require.resolve('jquery'),
                use: [
                  {
                    loader: "expose-loader",
                    options: {
                        exposes: [
                            {
                                globalName: '$',
                                override: true
                            },
                            {
                                globalName: 'jQuery',
                                override: true
                            },
                        ],
                    }
                  }
                ]
            }
        ],
    },

    devtool: 'source-map',

    resolve: {
        modules: ['node_modules', 'bower_components'],
        extensions: ['*', '.js', '.jsx'],
    },
}