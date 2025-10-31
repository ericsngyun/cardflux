const path = require('path');
const webpack = require('webpack');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const isDevelopment = process.env.NODE_ENV !== 'production';

module.exports = [
  // Main process config
  {
    mode: isDevelopment ? 'development' : 'production',
    devtool: isDevelopment ? 'eval-source-map' : 'source-map',
    entry: './src/main/index.ts',
    target: 'electron-main',
    output: {
      path: path.resolve(__dirname, 'dist/main'),
      filename: 'index.js',
    },
    resolve: {
      extensions: ['.ts', '.js'],
    },
    module: {
      rules: [
        {
          test: /\.ts$/,
          use: 'ts-loader',
          exclude: /node_modules/,
        },
      ],
    },
    plugins: [
      new CopyWebpackPlugin({
        patterns: [
          { from: 'src/python', to: '../python' },
        ],
      }),
    ],
    node: {
      __dirname: false,
      __filename: false,
    },
  },
  // Preload process config
  {
    mode: isDevelopment ? 'development' : 'production',
    devtool: isDevelopment ? 'eval-source-map' : 'source-map',
    entry: './src/preload/preload.ts',
    target: 'electron-preload',
    output: {
      path: path.resolve(__dirname, 'dist/preload'),
      filename: 'preload.js',
    },
    resolve: {
      extensions: ['.ts', '.js'],
    },
    module: {
      rules: [
        {
          test: /\.ts$/,
          use: 'ts-loader',
          exclude: /node_modules/,
        },
      ],
    },
  },
  // Renderer process config
  {
    mode: isDevelopment ? 'development' : 'production',
    devtool: isDevelopment ? 'eval-source-map' : 'source-map',
    performance: {
      hints: isDevelopment ? false : 'warning',
      maxAssetSize: 512000, // 500 KB
      maxEntrypointSize: 512000, // 500 KB
    },
    entry: './src/renderer/app.tsx',
    target: 'electron-renderer',
    output: {
      path: path.resolve(__dirname, 'dist/renderer'),
      filename: isDevelopment ? '[name].js' : '[name].[contenthash:8].js',
      chunkFilename: isDevelopment ? '[name].chunk.js' : '[name].[contenthash:8].chunk.js',
      clean: true, // Clean output directory before build
      globalObject: 'globalThis', // Fix webpack 5 global reference for Electron
    },
    resolve: {
      extensions: ['.tsx', '.ts', '.js'],
    },
    optimization: {
      // Enable optimizations in production
      minimize: !isDevelopment,
      // Split chunks for better caching and smaller bundles
      splitChunks: {
        chunks: 'all',
        cacheGroups: {
          // Vendor chunk for node_modules
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendors',
            priority: 10,
            reuseExistingChunk: true,
          },
          // React/ReactDOM in separate chunk (frequently updated)
          react: {
            test: /[\\/]node_modules[\\/](react|react-dom)[\\/]/,
            name: 'react-vendor',
            priority: 20,
            reuseExistingChunk: true,
          },
          // Common components shared across multiple chunks
          common: {
            minChunks: 2,
            priority: 5,
            reuseExistingChunk: true,
            name: 'common',
          },
        },
      },
      // Runtime chunk for webpack runtime code
      runtimeChunk: {
        name: 'runtime',
      },
      // Module IDs optimization
      moduleIds: 'deterministic',
    },
    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: {
            loader: 'ts-loader',
            options: {
              transpileOnly: isDevelopment, // Faster builds in dev
              compilerOptions: {
                module: 'esnext', // Enable tree-shaking
              },
            },
          },
          exclude: /node_modules/,
        },
        {
          test: /\.css$/,
          use: ['style-loader', 'css-loader'],
        },
      ],
    },
    plugins: [
      new HtmlWebpackPlugin({
        template: 'src/renderer/index.html',
        filename: 'index.html',
        inject: 'body', // Inject all scripts at end of body
        scriptLoading: 'defer', // Use defer for better performance
        minify: isDevelopment ? false : {
          removeComments: true,
          collapseWhitespace: true,
          removeRedundantAttributes: true,
          useShortDoctype: true,
          removeEmptyAttributes: true,
          removeStyleLinkTypeAttributes: true,
          keepClosingSlash: true,
          minifyJS: true,
          minifyCSS: true,
          minifyURLs: true,
        },
      }),
    ],
  },
];
