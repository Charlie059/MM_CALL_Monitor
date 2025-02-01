from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_s3_notifications as s3n,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    RemovalPolicy,
    CfnOutput,
    Duration,
    aws_iam as iam,
)
from constructs import Construct

class ScreenshotMonitorStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for screenshots with lifecycle rule
        screenshot_bucket = s3.Bucket(
            self, "ScreenshotBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET],
                    allowed_origins=['*'],  # 生产环境中要限制
                    allowed_headers=['*']
                )
            ],
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    expiration=Duration.days(365),  # 保留一年
                    # 可选：超过30天后转移到低频访问存储
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30)
                        )
                    ]
                )
            ]
        )

        # DynamoDB table with additional attributes
        screenshot_table = dynamodb.Table(
            self, "ScreenshotTable",
            partition_key=dynamodb.Attribute(
                name="deviceId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # 添加 GSI
        screenshot_table.add_global_secondary_index(
            index_name="ByTimestamp",
            partition_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Lambda for processing S3 events
        processor_function = lambda_.Function(
            self, "ProcessorFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda/processor"),
            environment={
                "TABLE_NAME": screenshot_table.table_name,
                "BUCKET_NAME": screenshot_bucket.bucket_name,
            }
        )

        # Lambda for API
        api_function = lambda_.Function(
            self, "ApiFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda/api"),
            environment={
                "TABLE_NAME": screenshot_table.table_name,
                "BUCKET_NAME": screenshot_bucket.bucket_name,
            }
        )

        # Permissions
        screenshot_bucket.grant_read(api_function)
        screenshot_table.grant_read_write_data(processor_function)
        screenshot_table.grant_read_data(api_function)
        screenshot_bucket.grant_write(processor_function)

        # S3 Event Notification
        screenshot_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(processor_function)
        )

        # API Gateway
        api = apigateway.RestApi(
            self, "ScreenshotApi",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS
            )
        )

        screenshots = api.root.add_resource("screenshots")
        screenshots.add_method(
            "GET",
            apigateway.LambdaIntegration(api_function)
        )

        # 前端S3存储桶
        frontend_bucket = s3.Bucket(
            self, "FrontendBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,  # 强制桶拥有者控制
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.HEAD],
                    allowed_origins=['*'],
                    allowed_headers=['*'],
                    max_age=300  # 5分钟，使用秒数
                )
            ]
        )

        # 创建 Origin Access Identity
        origin_identity = cloudfront.OriginAccessIdentity(
            self, "OriginAccessIdentity",
            comment="Allow CloudFront to access the website bucket"
        )

        # 直接使用 grantRead 方法授予权限
        frontend_bucket.grant_read(origin_identity)

        # 使用更简单的 CloudFront Web Distribution
        distribution = cloudfront.CloudFrontWebDistribution(
            self, "WebDistribution",
            origin_configs=[
                cloudfront.SourceConfiguration(
                    s3_origin_source=cloudfront.S3OriginConfig(
                        s3_bucket_source=frontend_bucket,
                        origin_access_identity=origin_identity
                    ),
                    behaviors=[
                        cloudfront.Behavior(
                            is_default_behavior=True,
                            allowed_methods=cloudfront.CloudFrontAllowedMethods.GET_HEAD,
                            cached_methods=cloudfront.CloudFrontAllowedCachedMethods.GET_HEAD,
                            compress=True,
                            default_ttl=Duration.days(1),
                            max_ttl=Duration.days(365),
                            min_ttl=Duration.minutes(0),
                        )
                    ]
                )
            ],
            error_configurations=[
                cloudfront.CfnDistribution.CustomErrorResponseProperty(
                    error_code=403,
                    response_code=200,
                    response_page_path="/index.html",
                    error_caching_min_ttl=0
                ),
                cloudfront.CfnDistribution.CustomErrorResponseProperty(
                    error_code=404,
                    response_code=200,
                    response_page_path="/index.html",
                    error_caching_min_ttl=0
                )
            ],
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100  # 使用最便宜的价格类别，只在北美和欧洲分发
        )

        # Outputs
        CfnOutput(
            self, "BucketName",
            value=screenshot_bucket.bucket_name
        )
        CfnOutput(
            self, "ApiUrl",
            value=api.url
        )
        CfnOutput(
            self, "FrontendBucketName",
            value=frontend_bucket.bucket_name
        )
        CfnOutput(
            self, "CloudFrontDomain",
            value=distribution.distribution_domain_name
        )
