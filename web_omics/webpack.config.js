const path = require("path");
const webpack = require('webpack');
const BundleTracker = require('webpack-bundle-tracker');
const IgnorePlugin =  require("webpack").IgnorePlugin;
const MiniCssExtractPlugin = require("mini-css-extract-plugin");

module.exports = {
    context: __dirname,

    entry: {
        base: './static/js/base',
        explore_data: './static/js/explore_data',
        summary: './static/js/summary',
    },

    output: {
        filename: "[name]-[hash].js",
        path: path.resolve('./static/bundles/'),
    },

    plugins: [
        new BundleTracker({filename: './webpack-stats.json'}),
        new MiniCssExtractPlugin({
            filename: "[name]-[hash].css",
            chunkFilename: "[id]-[chunkhash].css"
        }),
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            'window.jQuery': 'jquery',
            'window.$': 'jquery'
        }),
        // for alasql
        new IgnorePlugin(/(^fs$|cptable|jszip|xlsx|^es6-promise$|^net$|^tls$|^forever-agent$|^tough-cookie$|cpexcel|^path$|^request$|react-native|^vertx$)/),
    ],

    module: {
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
        ],
    },

    devtool: 'source-map',

    resolve: {
        modules: ['node_modules', 'bower_components'],
        extensions: ['*', '.js', '.jsx'],
    },
}