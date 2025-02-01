import os
import json
import boto3
from datetime import datetime
from botocore.config import Config
from decimal import Decimal

# 配置 S3 客户端，添加签名版本
s3 = boto3.client('s3', 
    config=Config(
        signature_version='s3v4'  # 使用最新的签名版本
    )
)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

# 添加 JSON 编码器来处理 Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)

def handler(event, context):
    # 获取查询参数
    query_params = event.get('queryStringParameters', {})
    device_id = query_params.get('deviceId') if query_params else None
    
    if not device_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'deviceId is required'})
        }
    
    try:
        # 查询最新的截图记录
        response = table.query(
            KeyConditionExpression='deviceId = :deviceId',
            ExpressionAttributeValues={
                ':deviceId': device_id
            },
            Limit=1,
            ScanIndexForward=False  # 最新的记录
        )
        
        if not response['Items']:
            return {
                'statusCode': 404,
                'body': json.dumps({'message': 'No screenshots found'})
            }
        
        latest_item = response['Items'][0]
        
        # 生成预签名URL
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': os.environ['BUCKET_NAME'],
                'Key': latest_item['imageKey']
            },
            ExpiresIn=3600,  # 1小时过期
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',  # 允许跨域访问
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'url': url,
                'timestamp': latest_item['timestamp'],
                'uploadTime': latest_item.get('uploadTime', ''),
                's3Location': latest_item.get('s3Location', {})
            }, cls=DecimalEncoder)  # 使用自定义编码器
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Internal server error'}, cls=DecimalEncoder)
        } 