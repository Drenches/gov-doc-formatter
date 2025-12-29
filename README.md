# 公文自动排版工具

基于大模型（通义千问）的党政机关公文自动排版agent工具，支持上传Word文档，自动识别文档结构并按照《党政机关公文格式》(GB/T 9704-2012) 国家标准进行排版。

（目前还处于初级阶段，正在持续优化中）

## 功能特点

- 自动识别公文结构（标题、一至四级标题、正文、发文机关、日期）
- 按照国标自动应用公文格式
- 混合字体处理（中文使用规定字体，英文和数字使用 Times New Roman）
- 自动标准化括号（将各种异常括号统一转换为中文全角括号）
- **支持两种输入方式**：
  - 文件上传：支持 .doc 和 .docx 格式（.doc 需要 LibreOffice 自动转换）
  - 文本粘贴：直接粘贴公文文本内容进行排版
- Web界面，支持拖拽上传
- 即时下载排版后的文档
- **支持打包成 Windows EXE**，方便非技术用户使用

## 工具原理

使用LLM识别并标记各个文段性质（标题、一级标题、正文等），然后采用公文规则对各个文段进行格式映射转换，最后输出排版后 Word 文稿。

---

## 使用方式

本工具提供两种使用方式：**直接使用打包版** 和 **开发模式运行**。

---

## 方式一：直接使用打包版（推荐普通用户）

适合不熟悉代码的用户，无需安装 Python 和任何依赖。

### 使用步骤

1. **下载发布包**
   - 从 [Releases](../../releases) 页面下载最新的 `公文自动排版工具.zip`
   - 或直接使用项目中已有的打包文件

2. **解压并运行**
   ```
   解压 公文自动排版工具.zip
   双击运行 公文自动排版工具.exe
   ```

3. **首次配置**
   - 程序启动后会自动打开浏览器
   - 首次使用需要配置通义千问 API Key
   - API Key 获取地址：https://dashscope.console.aliyun.com/

4. **开始使用**
   - 配置完成后自动跳转到主界面
   - 上传 Word 文档或粘贴文本即可自动排版

### 配置文件位置

EXE 运行时会在用户目录下创建配置文件夹：
- Windows: `C:\Users\<用户名>\.公文排版工具\`
  - `config.json` - API Key 配置
  - `uploads/` - 临时上传目录
  - `outputs/` - 输出文件目录

---

## 方式二：开发模式运行（开发者/高级用户）

适合需要修改代码或进行二次开发的用户。

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 LibreOffice（可选，用于 .doc 文件转换）

如需支持 .doc 格式文件，需要安装 LibreOffice：

```bash
# Ubuntu/Debian/WSL
sudo apt update && sudo apt install -y libreoffice

# CentOS/RHEL
sudo yum install -y libreoffice

# macOS
brew install --cask libreoffice

# Windows
# 方法1: 从官网下载安装 https://www.libreoffice.org/download/
# 方法2: 使用 winget
winget install TheDocumentFoundation.LibreOffice
# 方法3: 使用 choco
choco install libreoffice
```

> 如果仅使用 .docx 格式文件，可跳过此步骤

### 3. 配置 API Key

复制 `.env.example` 为 `.env` 并填入你的通义千问 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```
DASHSCOPE_API_KEY=your_api_key_here
```

也可以将 API Key 直接配置到系统环境变量，具体操作可以参考阿里云百炼官网-API参考：

> 获取 API Key: https://dashscope.console.aliyun.com/

### 4. 启动服务

```bash
python run.py
```

### 5. 访问

- 前端页面: http://localhost:8000/static/index.html
- API文档: http://localhost:8000/docs

---

## 打包成 EXE（开发者）

如果你修改了代码，需要重新打包成 EXE 分发给用户。

### 一键打包

项目提供了一键打包脚本，在 Windows 环境下执行：

```bash
.\build.bat
```

脚本会自动完成：
1. 清理旧的构建文件
2. 生成应用图标
3. 执行 PyInstaller 打包
4. 压缩成 ZIP 文件

最终生成的 `公文自动排版工具.zip` 可直接分发给用户。

### 手动打包

如需手动打包，执行以下步骤：

```bash
# 1. 安装打包依赖
pip install pyinstaller pillow

# 2. 生成图标（如果没有）
python create_icon.py

# 3. 执行打包
pyinstaller gw-formatter.spec

# 4. 打包成 ZIP
powershell Compress-Archive -Path "dist\公文自动排版工具" -DestinationPath "公文自动排版工具.zip" -Force
```

---

## 公文格式规范

| 元素 | 字体 | 字号 | 其他要求 |
|------|------|------|----------|
| 标题 | 方正小标宋简体 | 二号 | 居中 |
| 一级标题 | 黑体 | 三号 | 序号"一、"，首行缩进2字符 |
| 二级标题 | 楷体_GB2312 | 三号 | 序号"（一）"，首行缩进2字符 |
| 三级标题 | 仿宋_GB2312（加粗） | 三号 | 序号"1."，首行缩进2字符 |
| 四级标题 | 仿宋_GB2312 | 三号 | 序号"（1）"，首行缩进2字符 |
| 正文 | 仿宋_GB2312 | 三号 | 首行缩进2字符，两端对齐 |
| 英文/数字 | Times New Roman | 同所在位置 | 全文统一 |

### 页面设置
- 纸张: A4 (210mm × 297mm)
- 页边距: 上37mm、下35mm、左28mm、右26mm
- 版心: 每页22行，每行28字
- 行距: 固定值28磅

---

## 项目结构

```
公文自动排版agent/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置文件
│   ├── api/
│   │   └── routes.py        # API路由
│   ├── core/
│   │   ├── document_parser.py  # Word文档解析（支持.doc转换）
│   │   ├── llm_analyzer.py     # 大模型结构分析
│   │   ├── formatter.py        # 排版格式化引擎
│   │   └── styles.py           # 公文样式定义
│   ├── models/
│   │   └── schemas.py       # 数据模型
│   └── utils/
│       └── helpers.py       # 辅助函数
├── static/
│   ├── index.html           # 主页面
│   └── setup.html           # API Key 配置页面
├── uploads/                 # 上传文件临时目录
├── outputs/                 # 输出文件目录
├── build.bat               # 一键打包脚本
├── gw-formatter.spec       # PyInstaller 打包配置
├── create_icon.py          # 图标生成脚本
├── config_manager.py       # 配置管理器
├── requirements.txt        # Python依赖包
├── .env.example           # 环境变量示例
├── run.py                 # 启动脚本
└── README.md              # 项目说明
```

---

## API 接口

### POST /api/format
上传并格式化公文文档

**请求**: `multipart/form-data`
- `file`: Word文档 (.docx, .doc)

**响应**:
```json
{
  "success": true,
  "message": "文档格式化成功",
  "output_filename": "formatted_xxx.docx",
  "download_url": "/api/download/formatted_xxx.docx"
}
```

### POST /api/format-text
直接格式化粘贴的文本内容

**请求**: `multipart/form-data`
- `text`: 公文文本内容（最大 50000 字符）

**响应**:
```json
{
  "success": true,
  "message": "文档格式化成功",
  "output_filename": "formatted_text_xxx.docx",
  "download_url": "/api/download/formatted_text_xxx.docx"
}
```

### POST /api/analyze
仅分析文档结构（不排版）

### GET /api/download/{filename}
下载格式化后的文档

### GET /api/health
健康检查

---

## 注意事项

1. **字体安装**: 确保系统安装了以下字体
   - 方正小标宋简体
   - 仿宋_GB2312
   - 黑体
   - 楷体_GB2312
   - Times New Roman

2. **文件大小**: 最大支持 10MB

3. **支持格式**:
   - .docx（直接处理）
   - .doc（需要安装 LibreOffice 进行自动转换）

4. **括号标准化**: 系统会自动将各种异常括号（半角、特殊编码等）统一转换为标准中文全角括号

---

## 技术栈

- 后端: Python + FastAPI
- 大模型: 通义千问 (DashScope)
- Word处理: python-docx
- 文档转换: LibreOffice（用于 .doc 转 .docx）
- 前端: 原生 HTML/CSS/JavaScript
- 打包工具: PyInstaller
- WSGI服务器: waitress（打包模式）/ uvicorn（开发模式）

---

## License

MIT
