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

const PUBLIC_PATH = '/';

module.exports = {
  // 當前webpack 模式
  mode: 'development',

  // 入口位置，可以是字串，陣列，物件
  // entry: './resources/file1.js' 一個入口，產生一個檔案
  // entry: ['./resources/file1.js', './resources/file2.js'] 一個入口，產生兩個檔案
  // entry: { './resources/file1.js', './resources/file2.js' } 多入口，產生兩個檔案
  entry: {
    bot: './resources/bot.js'
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
          {
            loader: 'sass-loader',
            options: {
              sourceMap: true,
              data: () => `$BaseUrl: '${PUBLIC_PATH}';`,
              // Sass變數取代 類似String-replace-loader
              // sassOptions: {
              //   data: () => `$BaseUrl: '${PUBLIC_PATH}';`,
              //   // includePaths: [
              //   //   './resources/sass/mixin',
              //   // ],
              // },
            },
          },
        ]
      }
    ],
    
    // 不用丟到webpack解析與處理的模組，節省處理時間
    noParse: [
      /jquery/
    ]
  },

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
      chunks: ['bot'],
      filename: 'bot.html',
      template: path.resolve(__dirname, './resources/pug/bot.pug'),
      data: {
        topper: require('./resources/words/common/topper.json'),
        base: require('./resources/words/bot.json'),
        footer: require('./resources/words/common/footer.json'),
      },
      inject: true
    })
  ],

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
    openPage: 'bot.html',
    compress: true,
    watchContentBase: true,
    contentBase: path.join(__dirname, './resources/'),
    port: 3000,
    disableHostCheck: true
  }
}