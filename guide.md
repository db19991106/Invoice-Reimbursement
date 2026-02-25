# 财务报销智能审核系统 - 实施指南

## 项目概述

基于AI的财务报销智能审核系统，实现发票自动识别、签名验证、风险评估和自动决策。

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                     财务报销智能审核系统                    │
├─────────────────────────────────────────────────────────┤
│  输入层：报销单图片（发票+审批单+签名）支持JPG/PNG/PDF      │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │  身份核验层  │ → │  内容审核层  │ → │  决策输出层  │ │
│  │  (Signature)│    │  (Document) │    │  (Decision) │ │
│  │             │    │             │    │             │ │
│  │ • 签名检测   │    │ • QwenVL OCR│    │ • 规则校验   │ │
│  │ • 笔迹比对   │    │ • 真伪判断   │    │ • 风险评分   │ │
│  │ • 活人检测   │    │ • 金额核对   │    │ • 自动/人工  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
├─────────────────────────────────────────────────────────┤
│  输出层：审核结果（通过/驳回/人工复核）+ 结构化数据          │
└─────────────────────────────────────────────────────────┘
```

## 目录结构

```
/root/autodl-tmp/caiwubaoxiao/
├── backend/                     # FastAPI后端
│   ├── main.py                  # 应用入口
│   ├── config.py                # 配置管理
│   ├── database.py              # SQLite数据库（含Auditor审核人模型）
│   ├── logger_config.py         # 日志配置（中文日志）
│   ├── requirements.txt         # Python依赖
│   ├── init_mock_data.py        # 初始化模拟数据
│   ├── models/                  # 数据模型
│   │   └── schemas.py          # Pydantic模型
│   ├── api/                     # API路由
│   │   ├── upload.py           # 发票上传API
│   │   └── audit.py            # 审核人API
│   └── services/                # 业务逻辑
│       ├── ocr_service.py       # QwenVL发票识别
│       ├── llm_service.py       # Qwen模型调用
│       ├── audit_service.py     # 审核编排
│       ├── auth_service.py      # 审核人认证服务
│       ├── company_validator.py # 公司匹配验证
│       └── duplicate_checker.py # 重复发票检测
├── frontend/                    # Vue3前端
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router.ts
│   │   └── views/
│   │       ├── Dashboard.vue    # 仪表盘
│   │       ├── Upload.vue       # 上传页面
│   │       ├── Result.vue       # 结果页面
│   │       ├── AuditLogin.vue   # 审核人登录
│   │       └── AuditDashboard.vue # 审核工作台
├── ml/                          # AI服务
│   ├── invoice_ocr.py           # PaddleOCR发票专用识别
│   ├── risk_analyzer.py         # 风险分析引擎（BGE向量模型）
│   └── stamp_detector.py        # 印章检测
├── data/                        # 数据存储
│   ├── uploads/                 # 上传文件
│   ├── ocrdata/                 # OCR预览图片
│   ├── invoices.db              # SQLite数据库
│   ├── company_whitelist.json   # 公司白名单配置
│   └── faiss_index/             # FAISS向量索引
├── logs/                        # 日志目录
│   └── app.log                  # 应用日志（中文）
├── ChiSig/                      # 签名数据集 (10,242张)
├── guide.md                     # 本文档
└── start.sh                     # 启动脚本
```

## 当前服务状态

| 服务 | 地址 | 状态 |
|------|------|------|
| 后端API | http://localhost:8000 | ✅ 运行中 |
| API文档 | http://localhost:8000/docs | ✅ 运行中 |
| 前端界面 | http://localhost:5173 | ✅ 运行中 |
| 审核人登录 | http://localhost:5173/audit/login | ✅ 运行中 |

## 模型配置

### 本地模型路径
| 模型 | 路径 | 用途 |
|------|------|------|
| Qwen2.5-VL-7B-Instruct | /root/autodl-tmp/models/Qwen2.5-VL-7B-Instruct | 发票OCR识别、图像理解 |
| Qwen2.5-7B-Instruct | /root/autodl-tmp/models/Qwen2.5-7B-Instruct | 风险推理决策 |
| BGE-large-zh-v1.5 | /root/autodl-tmp/models/bge-large-zh-v1.5 | 文本向量化、相似度检索 |

## 默认账号

### 审核人账号
| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| auditor | auditor123 | 审核员 |

## API接口设计

### 发票相关接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload` | POST | 上传发票图片/PDF |
| `/api/invoices` | GET | 获取发票列表 |
| `/api/invoices/{id}` | GET | 获取发票详情 |
| `/api/invoices/{id}/image` | GET | 获取发票图片 |
| `/api/audit/{id}` | POST | 提交审核请求 |
| `/api/audit/{id}` | GET | 获取审核结果 |
| `/api/ocr/visualize` | POST | OCR预览（生成标注图片） |
| `/api/ocr/image/{name}` | GET | 获取OCR预览图片 |
| `/api/stats` | GET | 获取审核统计 |

### 审核人相关接口
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/audit/login` | POST | 审核人登录 |
| `/api/audit/logout` | POST | 审核人登出 |
| `/api/audit/me` | GET | 获取当前登录信息 |
| `/api/audit/invoices` | GET | 获取发票列表（审核人权限） |
| `/api/audit/invoices/{id}` | PUT | 修改发票信息 |
| `/api/audit/invoices/{id}/approve` | POST | 通过审核 |
| `/api/audit/invoices/{id}/reject` | POST | 驳回发票 |

## 数据库表结构

### employees 表 - 员工信息
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT,
    signature_path TEXT,
    credit_score REAL DEFAULT 100.0,
    level INTEGER DEFAULT 9,
    created_at DATETIME
);
```

### invoices 表 - 发票记录
```sql
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER,
    file_path TEXT NOT NULL,
    invoice_code TEXT,
    invoice_no TEXT,
    fingerprint TEXT,
    amount REAL,
    tax_amount REAL,
    total_amount REAL,
    date TEXT,
    seller_name TEXT,
    seller_tax_id TEXT,
    seller_address TEXT,
    seller_bank TEXT,
    buyer_name TEXT,
    buyer_tax_id TEXT,
    buyer_address TEXT,
    buyer_bank TEXT,
    items TEXT,
    status TEXT DEFAULT 'pending',
    channel TEXT DEFAULT 'pending',
    expense_type TEXT,
    destination_city TEXT,
    person_count INTEGER DEFAULT 1,
    trip_days INTEGER DEFAULT 1,
    created_at DATETIME,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);
```

### audit_records 表 - 审核记录
```sql
CREATE TABLE audit_records (
    id INTEGER PRIMARY KEY,
    invoice_id INTEGER,
    signature_score REAL,
    ocr_result TEXT,
    ocr_confidence REAL,
    risk_level TEXT,
    risk_score REAL,
    risk_reasons TEXT,
    decision TEXT,
    channel TEXT,
    validation_items TEXT,
    stamp_detected TEXT,
    duplicate_checked BOOLEAN,
    company_matched TEXT,
    reviewed_by INTEGER,
    reviewed_at DATETIME,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id),
    FOREIGN KEY (reviewed_by) REFERENCES auditors(id)
);
```

### auditors 表 - 审核人账号
```sql
CREATE TABLE auditors (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    role TEXT DEFAULT 'auditor',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME,
    last_login DATETIME
);
```

## 核心模块说明

### 1. OCR服务 (qwen_vl_service.py)
- 使用Qwen2.5-VL模型进行发票识别
- 直接输出结构化JSON数据
- 准确率高，支持语义理解
- 字段提取：发票代码、号码、日期、金额、税额、销售方、购买方等

### 2. 公司验证器 (company_validator.py)
- 验证购买方公司是否在白名单中
- 同时验证公司名称和纳税人识别号
- 支持中英文括号自动转换
- 白名单配置文件：`data/company_whitelist.json`

### 3. 重复检测器 (duplicate_checker.py)
- 只检测状态为 `approve` 或 `review` 的发票
- 基于发票代码+号码+金额生成指纹
- 支持Redis分布式锁（可选）

### 4. 审核服务 (audit_service.py)
- 编排OCR + 规则校验流程
- 驳回的发票自动删除记录和文件
- 只有通过或审核中的发票才会被保存

### 5. 风险分析器 (risk_analyzer.py)
- 使用BGE-large-zh-v1.5进行文本向量化
- FAISS向量检索检测相似发票
- 多维度风险评分

## 公司白名单配置

配置文件：`/root/autodl-tmp/caiwubaoxiao/data/company_whitelist.json`

```json
{
  "buyer_companies": [
    {
      "id": 1,
      "name": "中航电测仪器(西安)有限公司",
      "short_name": "中航电测",
      "tax_id": "916101315784145092",
      "aliases": [
        "中航电测仪器（西安）有限公司",
        "中航电测仪器西安有限公司"
      ]
    }
  ],
  "seller_companies": []
}
```

## 审核规则

### 驳回的发票
- 自动删除数据库记录
- 自动删除上传的文件
- 不记录到重复检测系统

### 通过/审核中的发票
- 保存到数据库
- 注册到重复检测系统
- 可在审核工作台查看

### 重复发票检测
- 只检测已通过(`approve`)或审核中(`review`)的发票
- 驳回的发票不会触发重复提示

## 日志系统

### 日志文件位置
```
/root/autodl-tmp/caiwubaoxiao/logs/app.log
```

### 日志格式（中文）
```
2026-02-24 23:08:45 [INFO] 财务审核系统 - 日志系统初始化完成
2026-02-24 23:08:45 [INFO] 财务审核系统 - 发票上传功能已就绪
2026-02-24 23:08:45 [WARNING] 财务审核系统 - 这是一个警告信息
2026-02-24 23:08:45 [ERROR] 财务审核系统 - 这是一个错误信息
```

### 实时查看日志
```bash
tail -f /root/autodl-tmp/caiwubaoxiao/logs/app.log
```

## 前端页面

### 1. 仪表盘 (Dashboard.vue)
- 审核统计概览（总数、待审核、已通过、已驳回）
- 最近上传的发票列表
- 快速上传入口

### 2. 上传页面 (Upload.vue)
- 支持JPG、PNG、JPEG、PDF格式
- 拖拽上传支持
- 多文件批量上传
- 员工选择、费用类型、目的地等
- OCR识别预览功能

### 3. 结果页面 (Result.vue)
- 发票图片展示
- 审核结果展示
- 风险评分和风险因素
- 发票详细信息表格

### 4. 审核人登录 (AuditLogin.vue)
- 审核人账号登录
- 默认账号提示

### 5. 审核工作台 (AuditDashboard.vue)
- 待审核、复核中、已通过发票列表
- 发票详情查看
- 通过/驳回操作
- 发票信息修改

## 启动流程

### 方式一：使用启动脚本（推荐）
```bash
cd /root/autodl-tmp/caiwubaoxiao
./start.sh
```

### 方式二：手动启动

#### 后端启动
```bash
cd /root/autodl-tmp/caiwubaoxiao/backend
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True python main.py
```

#### 前端启动
```bash
cd /root/autodl-tmp/caiwubaoxiao/frontend
npm run dev
```

## 功能清单

| 功能 | 说明 | 状态 |
|------|------|------|
| 发票上传 | 支持JPG/PNG/JPEG/PDF格式 | ✅ 完成 |
| QwenVL OCR识别 | 高精度发票信息提取 | ✅ 完成 |
| OCR预览 | 生成标注图片 | ✅ 完成 |
| 公司匹配 | 验证购买方名称和税号 | ✅ 完成 |
| 重复检测 | 只检测已通过发票 | ✅ 完成 |
| 驳回删除 | 驳回发票自动删除记录 | ✅ 完成 |
| 审核人系统 | 登录、权限管理 | ✅ 完成 |
| 审核工作台 | 发票查看、修改、审批 | ✅ 完成 |
| 中文日志 | 实时日志记录 | ✅ 完成 |
| PDF支持 | PDF转图片后识别 | ✅ 完成 |
| BGE向量化 | 本地向量模型 | ✅ 完成 |

## 风险评分规则

### 高风险 (≥0.8)
- 签名不匹配
- 发票金额异常高
- 疑似假发票
- 重复报销

### 中风险 (0.5-0.8)
- 金额略高于平均
- 发票日期异常
- 信息不完整

### 低风险 (<0.5)
- 正常发票
- 金额合理
- 信息完整

## 决策规则

| 风险等级 | 决策 | 通道 | 处理方式 |
|----------|------|------|----------|
| 低 | approve | green | 自动通过 - 打款 |
| 中 | review | yellow | 人工复核 - 财务确认 |
| 高 | reject | red | 自动驳回 - 删除记录 |

## 环境依赖

### Python包
```
fastapi>=0.109.0
uvicorn>=0.27.0
python-multipart>=0.0.6
sqlalchemy>=2.0.25
paddleocr>=3.4.0
paddlepaddle>=3.3.0
transformers>=4.37.0
torch>=2.10.0
Pillow>=10.2.0
faiss-cpu>=1.8.0
sentence-transformers>=2.2.0
PyMuPDF>=1.23.0
qwen-vl-utils
```

### 硬件要求
- GPU: NVIDIA RTX 3090 24GB
- 内存: 32GB+
- 存储: 100GB+

## 常见问题

### Q: OCR识别慢？
A: QwenVL模型首次加载需要时间，后续会使用缓存实例

### Q: PDF上传后无法识别？
A: 确保安装了PyMuPDF：`pip install PyMuPDF`

### Q: 公司匹配失败？
A: 检查`data/company_whitelist.json`配置，确保公司名称和税号正确

### Q: 审核人登录失败？
A: 默认账号：admin/admin123 或 auditor/auditor123

### Q: 如何查看日志？
A: `tail -f /root/autodl-tmp/caiwubaoxiao/logs/app.log`

### Q: 驳回的发票为什么找不到？
A: 驳回的发票会自动删除记录和文件，这是预期行为

## 维护说明

- 定期备份数据库文件: `cp data/invoices.db data/invoices.db.bak`
- 监控日志文件大小，适时清理
- 定期更新模型版本
- 监控API响应时间

---

**创建日期**: 2026-02-23
**版本**: 2.0.0
**最后更新**: 2026-02-24