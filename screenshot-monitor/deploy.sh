#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}开始部署...${NC}"

# 检查是否有必要的AWS环境变量
if [ -z "$AWS_PROFILE" ]; then
    echo -e "${YELLOW}未设置 AWS_PROFILE，使用默认配置${NC}"
fi

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 创建并激活虚拟环境
echo -e "${YELLOW}正在设置 Python 虚拟环境...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate  # Linux/Mac
# source .venv/Scripts/activate  # Windows

# 安装 Python 依赖
echo -e "${YELLOW}正在安装 Python 依赖...${NC}"
pip install -r requirements.txt

# 1. CDK 部署
echo -e "${YELLOW}正在部署 CDK Stack...${NC}"
cdk deploy --require-approval never

# 获取输出值
FRONTEND_BUCKET=$(aws cloudformation describe-stacks --stack-name ScreenshotMonitorStack --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' --output text)
CLOUDFRONT_DOMAIN=$(aws cloudformation describe-stacks --stack-name ScreenshotMonitorStack --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomain`].OutputValue' --output text)
API_URL=$(aws cloudformation describe-stacks --stack-name ScreenshotMonitorStack --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' --output text)

if [ -z "$FRONTEND_BUCKET" ] || [ -z "$CLOUDFRONT_DOMAIN" ] || [ -z "$API_URL" ]; then
    echo -e "${RED}无法获取必要的输出值${NC}"
    exit 1
fi

# 2. 更新前端配置
echo -e "${YELLOW}正在更新前端 API 配置...${NC}"
cat > frontend/src/config.js << EOF
export const API_BASE_URL = '${API_URL}';
EOF

# 3. 构建前端
echo -e "${YELLOW}正在构建前端...${NC}"
cd frontend
npm install
npm run build

# 4. 部署到 S3
echo -e "${YELLOW}正在部署前端到 S3...${NC}"
aws s3 sync build/ s3://${FRONTEND_BUCKET} --delete

# 5. 清理 CloudFront 缓存
echo -e "${YELLOW}正在清理 CloudFront 缓存...${NC}"
DISTRIBUTION_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?DomainName=='${CLOUDFRONT_DOMAIN}'].Id" --output text)
if [ ! -z "$DISTRIBUTION_ID" ]; then
    aws cloudfront create-invalidation --distribution-id ${DISTRIBUTION_ID} --paths "/*"
fi

# 退出虚拟环境
deactivate

echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}前端访问地址: https://${CLOUDFRONT_DOMAIN}${NC}"
echo -e "${GREEN}API 地址: ${API_URL}${NC}" 