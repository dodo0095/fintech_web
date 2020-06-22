const path = require('path');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CleanWebpackPlugin = require('clean-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

let cleanFolderInit = {
  target: [
    'build',
    'dist'
  ],
  options: {
    root: path.resolve('./'),
    verbose: true
    // exclude: ['*.html']
  }
}

module.exports = {
  // 當前webpack 模式
  mode: 'development',

  // 入口位置，可以是字串，陣列，物件
  // entry: './resources/file1.js' 一個入口，產生一個檔案
  // entry: ['./resources/file1.js', './resources/file2.js'] 一個入口，產生兩個檔案
  // entry: { './resources/file1.js', './resources/file2.js' } 多入口，產生兩個檔案
  entry: {
    main: './resources/entrance.js'
  },

  // 輸出位置
  // [name] 定義同chunk名稱
  // [chunkhash] 定義同hash名稱，適用於瀏覽器長時間快取檔案
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'js/bundle.js',
    sourceMapFilename: '[file].map',
  },

  // 模組Loader設定
  module: {
    rules: [
      {
        //Eslint-Loader
        // 切換loader載入順序，預設是從後往前載
        // enforce: 'post' 後 > 前
        // enforce: 'pre' 前 > 後
        enforce: 'pre',
        test: /\.js$/,
        // 忽略的目錄名稱
        exclude: /(node_modules)/,
        loader: 'eslint-loader',
        options: {
          emitError: true
        }
      },
      {
        //Babel-Loader
        test: /\.m?js$/,
        exclude: /(node_modules|bower_components)/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env'],
            plugins: [
              '@babel/plugin-proposal-object-rest-spread',
              '@babel/plugin-transform-runtime'
            ]
          }
        },
      },
      {
        test: /\.pug$/,
        exclude: /(node_modules)/,
        use: [{
          loader: 'pug-loader',
          options: {
            self: true,
            pretty: true,
           },
        }]
      },
      {
        // Sass-loader + css-loader
        test: /\.(sa|sc|c)ss$/,
        use: [
          MiniCssExtractPlugin.loader,
          'css-loader',
          'sass-loader'
        ]
      }
    ],
    
    // 不用丟到webpack解析與處理的模組，節省處理時間
    noParse: [
      /jquery/
    ]
  },

  // 設定尋找模組（Modules的規則）
  // alias中取代 字串為新的路徑名稱
  // resolve: {
  //   alias: {
  //     test: 'test/test'
  //   },
  // 是否強制寫明匯入檔案的副檔名
  // enforceExtension: false
  // },

  // 套件設定
  plugins: [
    // 清除指定資料夾
    new CleanWebpackPlugin(
      cleanFolderInit.target,
      cleanFolderInit.options
    ),

    // 拷貝複製資料夾
    new CopyWebpackPlugin([
      {
        from: './resources/images/',
        to: './images/',
        force: true
      }
    ]),

    // 產生獨立css檔案並匯入html
    new MiniCssExtractPlugin({
      filename: 'css/[name].css',
      chunkFilename: '[id].css'
    }),

    // 產生html的編譯器
    new HtmlWebpackPlugin({
      chunks: ['main'],
      filename: 'test.html',
      // template: path.resolve(__dirname, './resources/test.html'),
      template: path.resolve(__dirname, './resources/test.pug'),
      // data: require('./resources/test.json'),
      inject: true
    })
  ],

  // 效能檢查
  // performance: {
  //   // 有效能問題時輸出警告
  //   hints: 'warning',
  //   // 最大檔案的大小（bytes)
  //   maxAssetSize: 200000,
  //   // 最大入口檔案的大小（bytes)
  //   maxEntrypointSize: 400000,
  //   // 針對要檢查的檔案類型
  //   assetFilter: function(assetFilename) {
  //     return assetFilename.endsWith('.css') || assetFilename.endsWith('.js');
  //   }
  // },

  // 使用預先載入的(cdn方式) 全域變數
  // externals: {
  //   jquery: 'jQuery'
  // },

  // 開發模式是否產生source-map
  devtool: 'source-map',

  // dev模式設定
  devServer: {
    overlay: {
      warnings: true,
      errors: true
    },
    // 是否開啟https模式
    https: false,
    // 是否產生實體檔案到disk目錄
    writeToDisk: true,
    open: true,
    openPage: 'test.html',
    compress: true,
    watchContentBase: true,
    contentBase: path.join(__dirname, './resources/'),
    port: 3000,
    disableHostCheck: true
  }
}