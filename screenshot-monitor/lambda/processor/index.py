import os
import boto3
from datetime import datetime
import logging
import urllib.parse

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def handler(event, context):
    for record in event['Records']:
        try:
            bucket = record['s3']['bucket']['name']
            # URL 解码 key
            key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            size = record['s3']['object'].get('size', 0)
            
            logger.info(f"Processing file: {key}")
            
            # 检查文件路径格式 - 使用下划线分隔
            parts = key.split('_')
            if len(parts) != 2:
                logger.error(f"Invalid file path format: {key}")
                continue
                
            device_id, filename = parts
            
            # 检查文件名格式
            if not filename.endswith('.png'):
                logger.error(f"Invalid file type: {filename}")
                continue
                
            timestamp = filename.split('.')[0]
            
            # 记录到DynamoDB
            table.put_item(
                Item={
                    'deviceId': device_id,
                    'timestamp': timestamp,
                    'imageKey': key,
                    'uploadTime': datetime.now().isoformat(),
                    's3Location': {
                        'bucket': bucket,
                        'key': key,
                        'size': size,
                        'region': os.environ.get('AWS_REGION', 'us-east-1'),
                        'url': f"s3://{bucket}/{key}"
                    }
                }
            )
            logger.info(f"Successfully processed file: {key}")
            
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}")
            logger.error(f"Record: {record}")
            continue 