import aws_cdk as core
import aws_cdk.assertions as assertions

from screenshot_monitor.screenshot_monitor_stack import ScreenshotMonitorStack

# example tests. To run these tests, uncomment this file along with the example
# resource in screenshot_monitor/screenshot_monitor_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ScreenshotMonitorStack(app, "screenshot-monitor")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
