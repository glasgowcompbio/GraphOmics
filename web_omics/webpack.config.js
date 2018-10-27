var path = require("path");
var webpack = require('webpack');
var BundleTracker = require('webpack-bundle-tracker');
var IgnorePlugin =  require("webpack").IgnorePlugin;

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
        new webpack.ProvidePlugin({
            $: "jquery",
            jQuery: "jquery",
            'window.jQuery': 'jquery',
            'window.$': 'jquery'
        }),
        // for alasql
        new IgnorePlugin(/(^fs$|cptable|jszip|xlsx|^es6-promise$|^net$|^tls$|^forever-agent$|^tough-cookie$|cpexcel|^path$|^request$|react-native|^vertx$)/),
    ],

    // externals: {
    //     jquery: 'jQuery'
    // },

    module: {
        rules: [
            { test: /\.jsx?$/, exclude: /node_modules/, loader: 'babel-loader' },
            { test: /\.css$/, loaders: ['style-loader', 'css-loader'] },
            { test: /\.(svg|gif|png|eot|woff|ttf)$/, loader: 'url-loader' },
            // { test: /datatables\.net.*/, loader: 'imports-loader?define=>false'},
        ],
    },

    resolve: {
        modules: ['node_modules', 'bower_components'],
        extensions: ['*', '.js', '.jsx'],
    },
}