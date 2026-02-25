#!/bin/bash

# 设置 PaddlePaddle 环境变量（必须在任何 Python 导入之前设置）
export FLAGS_enable_pir_api=0
export FLAGS_enable_onednn=0
export FLAGS_use_mkldnn=0
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True

echo "=== 财务报销智能审核系统启动脚本 ==="

# 1. 安装后端依赖
echo "[1/4] 安装后端依赖..."
cd /root/autodl-tmp/caiwubaoxiao/backend
pip install -r requirements.txt -q

# 2. 初始化模拟数据
echo "[2/4] 初始化数据库..."
cd /root/autodl-tmp/caiwubaoxiao
python backend/init_mock_data.py

# 3. 安装前端依赖
echo "[3/4] 安装前端依赖..."
cd /root/autodl-tmp/caiwubaoxiao/frontend
npm install

# 4. 启动服务
echo "[4/4] 启动服务..."

# 后台启动FastAPI
echo "启动后端服务 (端口 8000)..."
cd /root/autodl-tmp/caiwubaoxiao/backend
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &

# 前端
echo "启动前端服务 (端口 3000)..."
cd /root/autodl-tmp/caiwubaoxiao/frontend
nohup npm run dev > ../frontend.log 2>&1 &

echo ""
echo "=== 服务启动完成 ==="
echo "后端API: http://localhost:8000"
echo "前端界面: http://localhost:3000"
echo "API文档: http://localhost:8000/docs"
echo ""
echo "查看日志: tail -f backend.log"
echo "查看前端日志: tail -f frontend.log"
