const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = {
  entry: {         // 你的弹出页脚本
    background: './src/background.ts', // 后台服务工作者
    content: './src/content.ts'        // 内容脚本
  },
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: '[name].js', // 每个入口文件生成对应的 JS 文件
  },
  resolve: {
    extensions: ['.ts', '.js'], // 自动解析这些扩展名
  },
  module: {
    rules: [
      {
        test: /\.ts$/,          // 匹配所有 .ts 文件
        use: 'ts-loader',        // 使用 ts-loader 处理
        exclude: /node_modules/,
      },
    ],
  },
  plugins: [
    new CopyWebpackPlugin({
      patterns: [
        { from: 'public', to: '.' }, // 将 public 目录下的 manifest.json, icons 等复制到 dist
      ],
    }),
  ],
  mode: 'development', // 或 'production'
  devtool: 'cheap-module-source-map', // 便于调试
};