"""
Lambda function to trigger the researcher Lambda directly.
Called by EventBridge on a schedule. Uses async invocation (fire-and-forget).
"""
import os
import json
import boto3


def handler(event, context):
    function_name = os.environ.get("RESEARCHER_FUNCTION_NAME")
    if not function_name:
        raise ValueError("RESEARCHER_FUNCTION_NAME environment variable not set")

    # Build a Lambda Function URL compatible payload for the /research/auto route
    payload = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/research/auto",
        "rawQueryString": "",
        "headers": {"content-type": "application/json"},
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/research/auto",
            }
        },
        "isBase64Encoded": False,
    }

    client = boto3.client("lambda")
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="Event",  # async — don't wait for the research to finish
        Payload=json.dumps(payload),
    )

    status = response["StatusCode"]
    print(f"Researcher Lambda triggered, status: {status}")
    return {"statusCode": 200, "body": json.dumps({"message": "Research triggered", "status": status})}
