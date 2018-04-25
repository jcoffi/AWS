#!/usr/bin/python
import troposphere,argparse,json,os,sys
from troposphere import Template, Parameter, Ref, Equals
from troposphere import If, Output, Join, GetAtt
from troposphere.sqs import Queue, QueuePolicy
from troposphere.sns import Topic,Subscription
from troposphere.iam import Policy, Role
from troposphere.awslambda import Code, Function, Permission
from troposphere.dynamodb import (Table, KeySchema, AttributeDefinition,
ProvisionedThroughput)

TEMPLATE_NAME = "SnsForMatillion"
LAMBDA_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),'lambda_edw_sns_broker.py')

def buildCloudFormationTemplate():
    global t
    global parameters
    global applicationTags
    t = Template()
    parameters={}
    t.add_version("2010-09-09")
    t.add_description("Creates a queue that will trigger Matillion SQL Jobs")

    applicationTags = troposphere.Tags(
        Application="Enterprise Data Warehouse POC",
        Environment=Ref("Environment"),
        Team="EDMS",
        Project="EDW",
        Category="2",
        HIPPA='No'
        )

    try:
        addParameters()
        addConditions()
        addResources()
        createFiles(TEMPLATE_NAME)
    except Exception as e:
        print e

def addParameters():
    global parameters
    global t
    #parameter for SQS
    parameters["Environment"] = t.add_parameter(Parameter(
        "Environment",
        Description="Type of Environment Deploying into",
        Type="String",
        Default="dev",
        AllowedValues=['dev','test','prod']
    ))
    parameters["EnvironmentTypeIndex"] = t.add_parameter(Parameter(
        "EnvironmentTypeIndex",
        Description="Type of Environment Deploying into",
        Type="String",
        Default="01"    ))

    parameters["HashKeyName"] = t.add_parameter(Parameter(
        "HashKeyName",
        Description="HashType PrimaryKey Name",
        Type="String",
        Default="jobId"
     ))
    parameters["HashKeyType"] = t.add_parameter(Parameter(
         "HashKeyType",
         Description="HashType PrimaryKey Type",
         Type="String",
         Default="S",
         AllowedPattern="[S|N]",
         MinLength="1",
         MaxLength="1",
         ConstraintDescription="must be either S or N"
     ))
    parameters["ReadCapacityUnits"] = t.add_parameter(Parameter(
        "ReadCapacityUnits",
        Description="Provisioned read throughput",
        Type="Number",
        Default="5",
        MinValue="5",
        MaxValue="10000",
        ConstraintDescription="should be between 5 and 10000"
     ))
    parameters["WriteCapacityUnits"] = t.add_parameter(Parameter(
        "WriteCapacityUnits",
        Description="Provisioned write throughput",
        Type="Number",
        Default="5",
        MinValue="5",
        MaxValue="10000",
        ConstraintDescription="should be between 5 and 10000"
     ))

def addConditions():
    pass

def addResources():
    global t
    global applicationTags

    #Create Queue
    snsQueue = t.add_resource(Queue(
                              "Sns",
                              ContentBasedDeduplication=True,
                              FifoQueue=True,
                              DelaySeconds=1,
                              QueueName=Join("-",["edw","orch","metl",Ref("Environment"),Ref("EnvironmentTypeIndex"),'queue.fifo'])
                           ))
    #Creating DynamoDB Table
    dynamoTable = t.add_resource(Table(
      "DynamoTable",
      AttributeDefinitions=[
          AttributeDefinition(
              AttributeName=Ref("HashKeyName"),
              AttributeType=Ref("HashKeyType")
          )
      ],
      #SSESpecification=troposphere.dynamodb.SSESpecification('spec',SSEEnabled=True),
      KeySchema=[
          KeySchema(
              AttributeName=Ref("HashKeyName"),
              KeyType="HASH"
          )
       ],
       ProvisionedThroughput=ProvisionedThroughput(
          ReadCapacityUnits=Ref("ReadCapacityUnits"),
          WriteCapacityUnits=Ref("WriteCapacityUnits")
      ),
       TableName=Join("-",["edw","config","table",Ref("Environment"),Ref("EnvironmentTypeIndex")]),
      Tags=applicationTags
    ))

    lambdaBrokerPolicy = Policy(
        "LambdaPolicy",
        PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            
                            "Effect": "Allow",
                            "Action": [
                                "dynamodb:BatchGetItem",
                                "dynamodb:DescribeTable",
                                "dynamodb:GetShardIterator",
                                "dynamodb:GetItem",
                                "sqs:SendMessage",
                                "dynamodb:DescribeContinuousBackups",
                                "dynamodb:Scan",
                                "dynamodb:DescribeStream",
                                "dynamodb:Query",
                                "dynamodb:DescribeBackup",
                                "dynamodb:GetRecords"
                            ],
                            "Resource": [
                                GetAtt(dynamoTable,'Arn'),
                                GetAtt(snsQueue,'Arn')
                            ]
                        },
                        {
                            "Effect": "Allow",
                            "Action": [
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            "Resource": "arn:aws:logs:*:*:*"
                        },
                        {
                            
                            "Effect": "Allow",
                            "Action": [
                                "dynamodb:DescribeReservedCapacityOfferings",
                                "dynamodb:DescribeReservedCapacity",
                                "dynamodb:ListTagsOfResource",
                                "dynamodb:DescribeTimeToLive",
                                "dynamodb:DescribeLimits",
                                "dynamodb:ListStreams"
                            ],
                            "Resource": "*"
                        }
                    ]
                },
        PolicyName=Join("-",["edw","orch","lambda","broker","policy"])
    )

    lambdaRedshiftSnapshotPolicy = Policy(
        "LambdaPolicy",
        PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            
                            "Effect": "Allow",
                            "Action": [
                                "redshift:CreateSnapshot",
                            ],
                            "Resource": [
                                "*",
                            ]
                        }
                    ]
                },
        PolicyName=Join("-",["edw","lambda","redshift","snapshot","policy",Ref("Environment"),Ref("EnvironmentTypeIndex")])
    )

    iamRoleLambdaBroker = t.add_resource(Role(
        "iamLambdaBrokerRole",
        AssumeRolePolicyDocument={
                                  "Version": "2012-10-17",
                                  "Statement": [
                                    {
                                      "Effect": "Allow",
                                      "Principal": {
                                        "Service": "lambda.amazonaws.com"
                                      },
                                      "Action": "sts:AssumeRole"
                                    }
                                  ]
                                },
        #ManagedPolicyArns=[ String, ... ],
        #Path="/",
        Policies=[lambdaBrokerPolicy],
        RoleName=Join('-',[Ref('AWS::Region'),Join("-",["edw","lambda","broker","policy",Ref("Environment"),Ref("EnvironmentTypeIndex")])])
    ))

    iamLambdaRedshiftSnapshot = t.add_resource(Role(
        "LambdaRedshiftSnapshotIamRole",
        AssumeRolePolicyDocument={
                                  "Version": "2012-10-17",
                                  "Statement": [
                                    {
                                      "Effect": "Allow",
                                      "Principal": {
                                        "Service": "lambda.amazonaws.com"
                                      },
                                      "Action": "sts:AssumeRole"
                                    }
                                  ]
                                },
        #ManagedPolicyArns=[ String, ... ],
        #Path="/",
        Policies=[lambdaRedshiftSnapshotPolicy],
        RoleName=Join('-',[Ref('AWS::Region'),Join("-",["edw","lambda","redshift","snapshot","role",Ref("Environment"),Ref("EnvironmentTypeIndex")])])
    ))
    #Lamda function
    #Gets contents for lambda function
    with open(LAMBDA_FILE_PATH,"r") as f:
        lambdaCodeArray = []
        for line in f.readlines():
            lambdaCodeArray.append(line)
        lambdaCode = Code(ZipFile=Join("",lambdaCodeArray))


    #Creates Cloudformation JSON
    LambdaEventBroker = t.add_resource(Function(
        "LambdaEventBroker",
        Code= lambdaCode,
        #DeadLetterConfig=DeadLetterConfig,
        Description='Manages SNS messages and executes necessary actions for FCA Cloud Data Warehouse POC',
        Environment=troposphere.awslambda.Environment(
                                                        Variables={
                                                            "TABLE_NAME":Ref(dynamoTable),
                                                            "TABLE_PRIMARY_KEY":Ref('HashKeyName')
                                                            }
                                                    ),
        FunctionName=Join("-",["edw","broker","function",Ref("Environment"),Ref("EnvironmentTypeIndex")]),#String,
        Handler="index.lambda_handler",#String,
        #KmsKeyArn=String,
        #MemorySize=Integer,
        Role=GetAtt(iamRoleLambdaBroker,'Arn'),
        Runtime="python2.7",#String,
        Timeout=60,
        #TracingConfig="",#TracingConfig,
        #VpcConfig="",#VPCConfig,
        Tags=applicationTags
    ))

    #Creates Cloudformation JSON
    lambdaRedshiftSnapshot = t.add_resource(Function(
        "lambdaRedshiftSnapshot",
        Code= lambdaCode,
        #DeadLetterConfig=DeadLetterConfig,
        Description='Given a ClusterIdentifier, Lambda function will take a manual snapshot.',
        #Environment=Environment,
        FunctionName=Join("-",["edw","redshift","snapshot","function",Ref("Environment"),Ref("EnvironmentTypeIndex")]),#String,
        Handler="index.lambda_handler",#String,
        #KmsKeyArn=String,
        #MemorySize=Integer,
        Role=GetAtt(iamLambdaRedshiftSnapshot,'Arn'),
        Runtime="python2.7",#String,
        Timeout=60,
        #TracingConfig="",#TracingConfig,
        #VpcConfig="",#VPCConfig,
        Tags=applicationTags
    ))

    #SNS Susbcription
    lambdaEdwRedshiftSubscription = Subscription(
        "lambdaEdwEventSubscription",
        Endpoint=GetAtt(lambdaRedshiftSnapshot,'Arn'),
        Protocol="lambda"
    )
    #SNS Susbcription
    lambdaEdwEventSubscription = Subscription(
        "lambdaEdwEventSubscription",
        Endpoint=GetAtt(LambdaEventBroker,'Arn'),
        Protocol="lambda"
    )
    #SNS for a task completion
    snsTaskComplete = t.add_resource(Topic(
        "snsTaskComplete",
        DisplayName="edw-task-complete",
        TopicName=Join("-",["edw","task","complete",Ref("Environment"),Ref("EnvironmentTypeIndex")]),#String,
    ))
    #Event for event within EDW.... should thi be the same as taks complete?
    snsTopicEdwEvent = t.add_resource(Topic(
        "snsTopicEdwEvent",
        DisplayName="edw-event-topic",
        Subscription=[lambdaEdwEventSubscription],
        TopicName=Join("-",["edw","event",Ref("Environment"),Ref("EnvironmentTypeIndex")]),#String,
    ))
    #SNS for a task completion
    snsTopicRedshiftSnapshot = t.add_resource(Topic(
        "snsTopicRedshiftSnapshot",
        DisplayName="edw-take-snapshot",
        Subscription=[lambdaEdwRedshiftSubscription],
        TopicName=Join("-",["edw","take","snapshot",Ref("Environment"),Ref("EnvironmentTypeIndex")]),#String,
    ))
    lambdaPermissionSnsEvent = t.add_resource(Permission(
        "lambdaPermissionSnsBroker",
        Action="lambda:InvokeFunction",
        FunctionName=GetAtt(LambdaEventBroker,'Arn'),
        Principal="sns.amazonaws.com",
        SourceArn=Ref(snsTopicEdwEvent)
    ))
    lambdaPermissionSnsSnapshot = t.add_resource(Permission(
        "lambdaPermissionSnsSnapshot",
        Action="lambda:InvokeFunction",
        FunctionName=GetAtt(lambdaRedshiftSnapshot,'Arn'),
        Principal="sns.amazonaws.com",
        SourceArn=Ref(snsTopicRedshiftSnapshot)
    ))

def createFiles(fileName):
    global t
    global parameters

    scriptFolder = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))
    #Create Cloudformation Templates and Parameter files
    #Write template out to file.
    with open(os.path.join(scriptFolder,'Template-{}.json'.format(fileName)),'wb') as f:
        f.write(t.to_json())
        json.encoder
    # Write a parameter file for Template with default values or empty strings
    with open(os.path.join(scriptFolder,'Parameters-{}.json'.format(fileName)),'wb') as f:
        parameterfile_json=[]
        #loop through parameters in template
        for template_parameter in t.parameters:
            #If the parameter, doesn't have a Default value property, set to empty string
            if not hasattr(parameters[template_parameter],'Default'):
                defaultParameterValue=""
            else:
                defaultParameterValue=parameters[template_parameter].Default

            #Append to json object
            parameterfile_json.append({
                            "ParameterKey":template_parameter,
                            "ParameterValue":defaultParameterValue,
                            "UsePreviousValue":True
                            })
        if len(t.parameters)>0:
            f.write(json.dumps(parameterfile_json, sort_keys=True,indent=4, separators=(',', ': ')))


if __name__ == '__main__':
    buildCloudFormationTemplate()
