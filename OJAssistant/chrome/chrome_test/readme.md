## 文件结构
my-extension/
├── dist/                     # 打包输出目录（编译后的文件）
│   ├── manifest.json         # 复制过来的清单文件
│   ├── popup.html            # 生成的弹出页面
│   ├── popup.js              # 编译后的弹出脚本
│   ├── background.js         # 编译后的后台脚本
│   ├── content.js            # 编译后的内容脚本
│   └── icons/                # 图标文件（复制自 public）
├── public/                    # 静态资源（复制到 dist）
│   ├── manifest.json
│   └── icons/
│       ├── icon16.png
│       ├── icon48.png
│       └── icon128.png
├── src/                       # 源代码目录
│   ├── popup.ts               # 弹出页面的 TypeScript 入口
│   ├── popup.html             # 弹出页面的 HTML 模板
│   ├── background.ts          # 后台 Service Worker
│   ├── content.ts             # 内容脚本
│   └── utils/                 # 可选：工具模块
│       └── storage.ts
├── package.json               # npm 项目配置和依赖
├── tsconfig.json              # TypeScript 编译器配置
├── webpack.config.js          # Webpack 构建配置
├── .gitignore                 # Git 忽略文件
└── readme.md

## 构建命令 
npm run dev