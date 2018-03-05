# SNS, SQS, Lamda Job Orchestration
This cloudformation script is used to build a series of services to help manage orchestration job across AWS services.

For this solution, Matillion listens to a SQS queue for a configuration JSON object to execute a job in its configuration library.

The format used to store data in DynamoDb for configurations is:
```json
 "jobId":<unique value identifying job>,
  "jobType":"<valid jobType>,
  "config": {
			"<Configuration specific for jobType>":"<value>",
			"<Configuration specific for jobType>":"<value>",
			"<Configuration specific for jobType>":"<value>"            
            }
}
```

Orchestration solution is built to be flexible for a variety of job configurations. The ```jobTypes``` supported are:
- ```MatillionJob``` : Expects configuration in DynamoDb as follows.

	```json
        {
          "jobId":"StartEtlProcess",
          "jobType":"MatillionQueue",
          "config": {
                    "queueUrl":"<matillion listening queue url>",
                    "sqsArn":"<matillion listening queue arn>",
                    "sqsMessageGroupId":"<arbitrary code/id for messages>",
                    "matillionSqsMessage":{
                                            "group":"<Exactly matches the project group where your job resides>",
                                            "project":"<Exactly matches the project name where your job resides>",
                                            "version":"<Exactly matches the version Name>",
                                            "environment":"<Exactly matches the environment Name>",
                                            "job":"<Exactly matches the orchestration Job Name>",
                                            "variables":  {
                                                         "<Name 1>": "<Value 1>",
                                                         "<Name 2>": "<Value 3>"
                                                     }
                                          }
                    }
        }

    ```
### Code used to test functionality.
**Replace values as needed for your use case**

```python
#!/usr/bin/python2
import boto3, json
from dynamoTool import DynamoTool

SNS_ARN='arn:aws:sns:us-west-2:123456789012:edw-event-dev-99'
sns = boto3.client('sns')

configTable = DynamoTool("edw-config-table-dev-99", region_name='us-west-2')

msg = "{\"jobId\":\"StartEtlProcess\"}"

jobConfig= {
  "jobId":"StartEtlProcess",
  "jobType":"MatillionQueue",
  "config": {
            "queueUrl":"https://sqs.us-west-2.amazonaws.com/123456789012/edw-orch-metl-dev-99-queue.fifo",
            "sqsArn":"arn:aws:sqs:us-west-2:123456789012:edw-orch-metl-dev-99-queue.fifo",
            "sqsMessageGroupId":"edw-ingest-kickoff",
            "matillionSqsMessage":{
                                  "group":"Test",
                                  "project":"mario",
                                  "version":"default",
                                  "environment":"edws",
                                  "job":"Step1"
                                  ,"variables":  {
                                                "environment": "test",
                                                "bucket_name": "FA-fca-edms-edw-test-99",
                                                "sns_topic_name":"edw-event-dev-99"
                                            }
                                    }
            }
}
jobConfig2= {
  "jobId":"StartEtlProcess2",
  "jobType":"MatillionQueue",
  "config": {
            "queueUrl":"https://sqs.us-west-2.amazonaws.com/123456789012/edw-orch-metl-dev-99-queue.fifo",
            "sqsArn":"arn:aws:sqs:us-west-2:123456789012:edw-orch-metl-dev-99-queue.fif",
            "sqsMessageGroupId":"edw-ingest-kickoff",
            "matillionSqsMessage":{
                                  "group":"Test",
                                  "project":"mario",
                                  "version":"default",
                                  "environment":"edws",
                                  "job":"Step2"
                                  ,"variables":  {
                                                "environment": "prod",
                                                "bucket_name": "FA-fca-edms-edw-prod-99",
                                                "sns_topic_name":"edw-event-dev-99"
                                            }
                                    }
            }
}
configTable.updateItem(jobConfig)
configTable.updateItem(jobConfig2)

response = sns.publish(
            TopicArn=SNS_ARN,
            Message=msg)

print response

```
