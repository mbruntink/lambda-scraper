from operator import truth
import os
import json
from aws_cdk import (
    Duration, Fn,
    Stack,
    aws_iam,
    aws_lambda,
    aws_secretsmanager,
    aws_apigateway,
)
from aws_cdk.aws_events import Rule, Schedule
from aws_cdk.aws_events_targets import LambdaFunction
from constructs import Construct

class ScraperStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        secret = aws_secretsmanager.Secret(
            scope=self,
            id='APNPortalLogin',
            secret_name='apn-portal-login',
            generate_secret_string=aws_secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps(dict(Username='')),
                generate_string_key='Password',
                password_length=32,
            )
        )

        scraper_function = aws_lambda.DockerImageFunction(
            scope=self,
            id="ScraperFunction",
            code=aws_lambda.DockerImageCode.from_image_asset("lambda/scraper"),
            environment={
                "CERT_TABLE_NAME": "certifications",
                "SECRET_NAME": secret.secret_name
            },
            memory_size=2048,
            timeout=Duration.minutes(5),
        )      
      
        # Allow the function to read / write to the DynamoDB table
        scraper_function.role.add_to_principal_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                   "dynamodb:BatchGetItem",
                   "dynamodb:GetItem",
                   "dynamodb:Scan",
                   "dynamodb:Query",
                   "dynamodb:BatchWriteItem",
                   "dynamodb:PutItem",
                   "dynamodb:UpdateItem",
                   "dynamodb:DeleteItem",
                   "dynamodb:CreateTable",
                   "dynamodb:DeleteTable",
                   "dynamodb:DescribeTable"
                ],
                resources=[
                    "arn:aws:dynamodb:{}:{}:table/certifications".format(self.region, self.account)
                ],
            )
        )
        
        # Allow function to read secret
        scraper_function.role.add_to_principal_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:ListSecretVersionIds"
                ],
                resources=[
                    secret.secret_arn
                ]
            )
        )

        # Add event to trigger Lambda
        rule = Rule(
            scope=self, 
            id="ScraperScheduleRule",
            schedule=Schedule.cron(minute="0", hour="20")
        )   
        rule.add_target(target=LambdaFunction(scraper_function))
