###this is the lambda function that will be triggered after the completion of the SSIS package that loads data into S3
###Created by Slalom LLC, 2/18/2018
import os, re, json, boto3, time
from boto3.dynamodb.conditions import Key, Attr
from httplib import HTTPException

DISABLE_DEDUPING=True

def lambda_handler(event, context):
    message = json.loads(event['Records'][0]['Sns']['Message'])
    DYNAMO_TABLE = os.environ['TABLE_NAME']
    jobId = message[os.environ['TABLE_PRIMARY_KEY']]
    #Get message from SNS
    print 'Json Message from Event Argument'
    print json.dumps(json.dumps(message, indent=4, sort_keys=True))
    #Lookup variables from DynamoDb Table for Job in messages
    dynamodb_client = boto3.client('dynamodb')
    config = dynamodb_client.get_item(
        TableName=DYNAMO_TABLE,
        Key={
            'jobId': {'S': jobId}
            }
    )
    #Get Configuration Details for Job
    try:
        jobConfiguration = config['Item']
    except KeyError:
        raise ValueError("DynamoDB Table Key '{}' not found in table '{}'".format(jobId,DYNAMO_TABLE))

    #Handle Job Type
    if jobConfiguration['jobType']['S']=='MatillionQueue':
        #Get Specific Deatalls for MatillionQueue Job Type
        sqs_client = boto3.client('sqs')

        #Build Matillion Message
        sqsMsg = jobConfiguration['config']['M']['matillionSqsMessage']['M']

        #Iterate through keys in message that are required for Matillion Queue
        metl_msg_keys = ['group','environment','project','job','version']
        metl_message = {
            key:returnPythonValue(val)
            for key, val in sqsMsg.items()
            if key in metl_msg_keys
        }

        if 'variables' in sqsMsg:
            #Parse through variables if they exist.
            if DISABLE_DEDUPING:
                jobId = int(time.time())
            metl_message['variables'] = {
                key:returnPythonValue(val)
                for key, val in sqsMsg['variables']['M'].items()
            }
            metl_message['variables']['lambdaId']=jobId

        print "Submitting Message\n", metl_message
        #Publish message to Sqs
        queueUrl = jobConfiguration['config']['M']['queueUrl']['S']
        print "Sns Url\t",queueUrl
        sqs_response = sqs_client.send_message(
            QueueUrl=queueUrl,
            MessageBody=json.dumps(metl_message),
            MessageGroupId=jobConfiguration['config']['M']['sqsMessageGroupId']['S']
        )
        if sqs_response['ResponseMetadata']['HTTPStatusCode']!=200:
            raise HTTPException(
                "Lambda failed to publish to SQS queue '{}' with response: {}".format(
                queueUrl,
                repsonse)
            )
            #sns_client('sns').publish

    elif jobConfiguration['jobType']=='EMR':
        #Handle EMR Job
        pass
    else:
        raise ValueError("Job type '{}' not supported".format(jobConfiguration['jobType']['S']))

def returnPythonValue(dct):
    try:
        if 'BOOL' in dct:
            return dct['BOOL']
        if 'S' in dct:
            val = dct['S']
            try:
                return datetime.strptime(val, '%Y-%m-%dT%H:%M:%S.%f')
            except:
                return str(val)
        if 'SS' in dct:
            return list(dct['SS'])
        if 'N' in dct:
            if re.match("^-?\d+?\.\d+?$", dct['N']) is not None:
                return float(dct['N'])
            else:
                try:
                    return int(dct['N'])
                except:
                    return int(dct['N'])
        if 'B' in dct:
            return str(dct['B'])
        if 'NS' in dct:
            return set(dct['NS'])
        if 'BS' in dct:
            return set(dct['BS'])
        if 'M' in dct:
            return dct['M']
        if 'L' in dct:
            return dct['L']
        if 'NULL' in dct and dct['NULL'] is True:
            return None
    except:
        return dct
