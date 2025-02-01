@echo off
setlocal

echo Starting deployment...

REM Create and activate virtual environment
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate

REM Install Python dependencies
pip install -r requirements.txt

REM Deploy CDK Stack
cdk deploy --require-approval never

REM ... 其余部分类似，但使用 Windows 命令语法

deactivate 