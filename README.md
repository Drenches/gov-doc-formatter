# 公文自动排版工具

基于大模型（通义千问）的党政机关公文自动排版工具，支持上传Word文档，自动识别文档结构并按照《党政机关公文格式》(GB/T 9704-2012) 国家标准进行排版。

## 功能特点

- 自动识别公文结构（标题、一至四级标题、正文、发文机关、日期）
- 按照国标自动应用公文格式
- 混合字体处理（中文使用规定字体，英文和数字使用 Times New Roman）
- 自动标准化括号（将各种异常括号统一转换为中文全角括号）
- 支持 .doc 和 .docx 格式（.doc 需要 LibreOffice 自动转换）
- Web界面，支持拖拽上传
- 即时下载排版后的文档

## 快速开始

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

> 获取 API Key: https://dashscope.console.aliyun.com/

#### 方式一：使用 .env 文件（推荐用于开发环境）

复制 `.env.example` 为 `.env` 并填入你的通义千问 API Key：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```
DASHSCOPE_API_KEY=your_api_key_here
```

#### 方式二：设置系统环境变量（推荐用于生产环境）

如果您希望 API Key 环境变量在当前用户的所有新会话中生效，可以添加永久性环境变量。

**Linux/macOS/WSL:**

执行以下命令将环境变量设置追加到 `~/.bashrc` 文件中：

```bash
# 用您的百炼API Key代替 YOUR_DASHSCOPE_API_KEY
echo "export DASHSCOPE_API_KEY='YOUR_DASHSCOPE_API_KEY'" >> ~/.bashrc
```

或者手动编辑 `~/.bashrc` 文件，添加以下内容：

```bash
export DASHSCOPE_API_KEY='YOUR_DASHSCOPE_API_KEY'
```

执行以下命令使变更生效：

```bash
source ~/.bashrc
```

重新打开一个终端窗口，运行以下命令检查环境变量是否生效：

```bash
echo $DASHSCOPE_API_KEY
```

**Windows:**

通过系统设置添加环境变量：
1. 右键点击"此电脑" → "属性" → "高级系统设置"
2. 点击"环境变量"
3. 在"用户变量"中点击"新建"
4. 变量名：`DASHSCOPE_API_KEY`，变量值：你的 API Key
5. 点击确定保存

或者使用 PowerShell：

```powershell
[Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", "YOUR_DASHSCOPE_API_KEY", "User")
```

### 4. 启动服务

```bash
python run.py
```

### 5. 访问

- 前端页面: http://localhost:8000/static/index.html
- API文档: http://localhost:8000/docs

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
│   └── index.html           # 前端页面
├── uploads/                 # 上传文件临时目录
├── outputs/                 # 输出文件目录
├── requirements.txt         # Python依赖包
├── .env.example            # 环境变量示例
├── run.py                  # 启动脚本
└── README.md               # 项目说明
```

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

### POST /api/analyze
仅分析文档结构（不排版）

### GET /api/download/{filename}
下载格式化后的文档

### GET /api/health
健康检查

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

## 技术栈

- 后端: Python + FastAPI
- 大模型: 通义千问 (DashScope)
- Word处理: python-docx
- 文档转换: LibreOffice（用于 .doc 转 .docx）
- 前端: 原生 HTML/CSS/JavaScript

## License

MIT
