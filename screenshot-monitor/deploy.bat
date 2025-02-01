@echo off
setlocal enabledelayedexpansion

echo [33m开始部署...[0m

REM 检查 AWS 配置
if "%AWS_PROFILE%"=="" (
    echo [33m未设置 AWS_PROFILE，使用默认配置[0m
)

REM 切换到脚本所在目录
cd /d "%~dp0"

REM 创建并激活虚拟环境
echo [33m正在设置 Python 虚拟环境...[0m
if not exist ".venv" (
    python -m venv .venv
)

REM 激活虚拟环境
call .venv\Scripts\activate.bat

REM 安装 Python 依赖
echo [33m正在安装 Python 依赖...[0m
pip install -r requirements.txt

REM 1. CDK 部署
echo [33m正在部署 CDK Stack...[0m
call cdk deploy --require-approval never

REM 获取输出值
for /f "tokens=* usebackq" %%a in (`aws cloudformation describe-stacks --stack-name ScreenshotMonitorStack --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" --output text`) do set "FRONTEND_BUCKET=%%a"
for /f "tokens=* usebackq" %%a in (`aws cloudformation describe-stacks --stack-name ScreenshotMonitorStack --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDomain'].OutputValue" --output text`) do set "CLOUDFRONT_DOMAIN=%%a"
for /f "tokens=* usebackq" %%a in (`aws cloudformation describe-stacks --stack-name ScreenshotMonitorStack --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text`) do set "API_URL=%%a"

if "!FRONTEND_BUCKET!"=="" (
    echo [31m无法获取 FRONTEND_BUCKET[0m
    exit /b 1
)
if "!CLOUDFRONT_DOMAIN!"=="" (
    echo [31m无法获取 CLOUDFRONT_DOMAIN[0m
    exit /b 1
)
if "!API_URL!"=="" (
    echo [31m无法获取 API_URL[0m
    exit /b 1
)

REM 2. 更新前端配置
echo [33m正在更新前端 API 配置...[0m
echo export const API_BASE_URL = '%API_URL%'; > frontend\src\config.js

REM 3. 构建前端
echo [33m正在构建前端...[0m
cd frontend
call npm install
call npm run build
cd ..

REM 4. 部署到 S3
echo [33m正在部署前端到 S3...[0m
aws s3 sync frontend\build\ s3://%FRONTEND_BUCKET% --delete

REM 5. 清理 CloudFront 缓存
echo [33m正在清理 CloudFront 缓存...[0m
for /f "tokens=* usebackq" %%a in (`aws cloudfront list-distributions --query "DistributionList.Items[?DomainName=='%CLOUDFRONT_DOMAIN%'].Id" --output text`) do set "DISTRIBUTION_ID=%%a"
if not "!DISTRIBUTION_ID!"=="" (
    aws cloudfront create-invalidation --distribution-id !DISTRIBUTION_ID! --paths "/*"
)

REM 退出虚拟环境
deactivate

echo [32m部署完成！[0m
echo [32m前端访问地址: https://%CLOUDFRONT_DOMAIN%[0m
echo [32mAPI 地址: %API_URL%[0m

endlocal 