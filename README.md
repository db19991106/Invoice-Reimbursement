# 财务报销智能审核系统

基于 AI 的企业财务发票报销智能审核系统，采用 FastAPI + Vue 3 构建，集成了 OCR 识别、大语言模型分析和规则引擎，实现发票的自动分类、风险评估和智能审核。

## 技术栈

### 后端
- **FastAPI** - 高性能 Python Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **PaddleOCR** - 中文发票 OCR 识别
- **Qwen2.5-VL** - 视觉语言模型用于发票信息提取
- **vLLM** - 高性能 LLM 推理加速
- **规则引擎** - 可配置的审核规则

### 前端
- **Vue 3** - 渐进式前端框架
- **Element Plus** - UI 组件库
- **Vite** - 构建工具
- **Vue Router** - 路由管理
- **Axios** - HTTP 客户端

## 功能特性

### 发票管理
- 发票上传与批量处理
- OCR 自动识别发票信息（金额、日期、发票代码等）
- 发票图片存储与查看

### 智能审核
- **规则引擎** - 基于配置规则的自动审核
- **AI 分析** - 使用 Qwen VL 模型智能分析发票内容
- **风险评估** - 多维度风险评分（低/中/高）
- **公司名称验证** - 白名单验证
- **重复检测** - 基于 FAISS 的相似发票检索
- **签名验证** - 印章检测与验证

### 用户角色
- **员工** - 提交报销申请、查看进度
- **审核员** - 审核发票、批量处理
- **管理员** - 用户管理、系统配置

### 数据统计
- 报销金额统计
- 审核效率分析
- 风险分布可视化

## 项目结构

```
.
├── backend/                    # 后端服务
│   ├── api/                    # API 路由
│   │   ├── upload.py           # 发票上传接口
│   │   ├── audit.py            # 审核接口
│   │   └── user.py             # 用户管理接口
│   ├── services/               # 业务服务
│   │   ├── ocr_service.py      # OCR 识别服务
│   │   ├── audit_service.py    # 审核服务
│   │   ├── llm_service.py      # LLM 分析服务
│   │   ├── qwen_vl_service.py  # Qwen VL 模型服务
│   │   ├── vllm_service.py     # vLLM 推理服务
│   │   └── ...
│   ├── rules/                  # 审核规则
│   │   └── engine.py           # 规则引擎
│   ├── main.py                 # FastAPI 应用入口
│   └── config.py               # 配置文件
├── frontend/                   # 前端应用
│   └── src/
│       ├── views/              # 页面组件
│       ├── router.ts           # 路由配置
│       └── main.ts             # 前端入口
├── ml/                         # ML 相关
│   ├── invoice_ocr.py          # 发票 OCR
│   ├── stamp_detector.py       # 印章检测
│   └── risk_analyzer.py        # 风险分析
└── start.sh                    # 启动脚本
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- CUDA 11.8+ (GPU 支持)

### 安装

```bash
# 方式一：使用启动脚本（推荐）
bash start.sh

# 方式二：手动安装
# 1. 安装后端依赖
cd backend
pip install -r requirements.txt

# 2. 初始化数据库
cd ..
python backend/init_mock_data.py

# 3. 安装前端依赖
cd frontend
npm install

# 4. 启动服务
# 后端
cd ../backend
uvicorn main:app --host 0.0.0.0 --port 8000

# 前端 (新终端)
cd frontend
npm run dev
```

### 访问

- 后端 API: http://localhost:8000
- 前端界面: http://localhost:3000
- API 文档: http://localhost:8000/docs

## 配置

主要配置项在 `backend/config.py`:

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| USE_VLLM | 启用 vLLM 加速 | true |
| USE_COMBINED_OCR_LLM | 合并 OCR + LLM 分析 | true |
| QWEN_VL_MODEL | Qwen VL 模型名称 | Qwen2.5-VL-7B-Instruct |
| OCR_USE_GPU | GPU 加速 OCR | true |

## 默认账号

系统初始化时会创建默认审核员账号：
- 用户名: `auditor`
- 密码: `auditor123`

## API 示例

### 上传发票

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@invoice.jpg" \
  -F "user_id=1"
```

### 获取审核列表

```bash
curl "http://localhost:8000/api/audit/list?status=pending"
```

### 提交审核

```bash
curl -X POST "http://localhost:8000/api/audit/submit" \
  -H "Content-Type: application/json" \
  -d '{"invoice_id": 1, "status": "approved", "comment": "审核通过"}'
```

## 许可证

MIT License
