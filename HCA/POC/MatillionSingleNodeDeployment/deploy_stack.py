#!/usr/bin/python
import boto3, json, sys

stackName = sys.argv[1]
with open(sys.argv[2],'r') as f:
    templateBody = f.read()

with open(sys.argv[3],'r') as f:
    parametersJson = json.load(f)

print stackName

cf = boto3.client('cloudformation')
wt = cf.get_waiter('stack_create_complete')
#if stack exists and is in failed state, then delete.
#if stack exists and is in succeeded state, then add one.
response = cf.create_stack(
    StackName=stackName,
    TemplateBody=templateBody,
    Parameters=parametersJson,
    Capabilities=[
        'CAPABILITY_IAM'
    ],
    Tags=[
        {
            'Key': 'Application',
            'Value': 'Enterprise Data Warehouse POC'
        },
        {
            'Key': 'Environment',
            'Value': 'Dev'
        },
        {
            'Key': 'Team',
            'Value': 'EDMS'
        },
    ]
    )

wt.wait(StackName=stackName)
print response
