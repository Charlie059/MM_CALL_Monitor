import boto3
import pyautogui
from datetime import datetime
import os
import time
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScreenshotUploader:
    def __init__(self, bucket_name, device_id):
        self.bucket_name = bucket_name
        self.device_id = device_id
        self.s3_client = boto3.client('s3')
    
    def capture_screenshot(self):
        try:
            screenshot = pyautogui.screenshot()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            local_path = f'temp_{timestamp}.png'
            screenshot.save(local_path)
            return local_path, timestamp
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            raise

    def upload_to_s3(self, local_path, timestamp):
        try:
            s3_key = f'{self.device_id}/{timestamp}.png'
            self.s3_client.upload_file(local_path, self.bucket_name, s3_key)
            logger.info(f"成功上传截图: {s3_key}")
        except Exception as e:
            logger.error(f"上传失败: {str(e)}")
            raise
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    def run(self):
        try:
            local_path, timestamp = self.capture_screenshot()
            self.upload_to_s3(local_path, timestamp)
        except Exception as e:
            logger.error(f"处理失败: {str(e)}")

def main():
    # 配置信息
    BUCKET_NAME = '从cdk deploy输出中获取的bucket名称'
    DEVICE_ID = 'device-001'          # 替换为实际的设备ID
    INTERVAL = 300                    # 截图间隔（秒）

    uploader = ScreenshotUploader(BUCKET_NAME, DEVICE_ID)
    
    while True:
        uploader.run()
        time.sleep(INTERVAL)

if __name__ == '__main__':
    main() 