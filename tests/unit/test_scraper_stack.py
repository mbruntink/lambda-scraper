import aws_cdk as core
import aws_cdk.assertions as assertions

from scraper.stack import ScraperStack

# example tests. To run these tests, uncomment this file along with the example
# resource in scraper/stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ScraperStack(app, "scraper")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
