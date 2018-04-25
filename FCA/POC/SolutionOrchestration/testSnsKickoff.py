#!/usr/bin/python2
import boto3,json

sns = boto3.client('sns')
msg= {
  "jobId":"StartEtlProcess",
  "type":"MatillionQueue",
  "config": {
            "sqsArn":"arn:aws:sns:us-west-2:123456789012:edw-event-dev-01",
            "matillionSqsMessage":{
                                  "group":"EDW",
                                  "project":"DataOnboarding",
                                  "version":"v2_1 Release",
                                  "environment":"Medicaid_Dev",
                                  "job":"Run All Ingest Jobs",
                                  # "variables":  {
                                  #              "<Name 1>": "<Value 1>",
                                  #              "<Name 2>": "<Value 3>"
                                  #          }
                                    }
            }
}
sns.publish(
            Topic="",
            Message=json.dumps(msg)
)
