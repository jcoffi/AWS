import troposphere,argparse,json
from troposphere import Template, Parameter, Ref, Equals
from troposphere import If, Output, Join, GetAtt
from troposphere.s3 import Bucket, BucketPolicy, Private, VersioningConfiguration, Private
from troposphere.sns import Topic, SubscriptionResource
from troposphere.awslambda import Function, Code, EventSourceMapping,Permission

TEMPLATE_NAME = "S3-Bucket-Encrypted"

def buildCloudFormationTemplate():
    global t
    global parameters
    global applicationTags
    t = Template()
    parameters={}
    t.add_version("2010-09-09")
    t.add_description("Deploys necessary s3 buckets for EDW POC")

    applicationTags = troposphere.Tags(
        Application="Enterprise Data Warehouse POC",
        Environment="dev",
        Team="EDMS"
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

    parameters["BucketName"] = t.add_parameter(Parameter(
        "BucketName",
        Description="The name of the bucket used for this solution. Buckets must be globally unique.",
        Type="String",
        Default="mybucket",
    ))
    parameters["EncryptKMSKey"] = t.add_parameter(Parameter(
        "EncryptKMSKey",
        Description="KMS Key to use for bucket encryption",
        Type="Number",
        Default=12,
    ))


def addConditions():
    #Prepare Conditions
    pass

def addResources():
    global t
    global applicationTags
    #Redshift Cluster Resource
    bucket = t.add_resource(Bucket(
        "Bucket",
        AccessControl=Private,
        #AccelerateConfiguration=AccelerateConfiguration,
        #AnalyticsConfigurations=[ AnalyticsConfiguration, ... ],
        BucketName=Ref('BucketName'),
        #CorsConfiguration=CorsConfiguration,
        #InventoryConfigurations=[ InventoryConfiguration, ... ],
        #LifecycleConfiguration=LifecycleConfiguration,
        #LoggingConfiguration=LoggingConfiguration,
        #MetricsConfigurations=[ MetricsConfiguration, ... ]
        #NotificationConfiguration=NotificationConfiguration,
        #ReplicationConfiguration=ReplicationConfiguration,
        Tags=applicationTags,
        VersioningConfiguration=VersioningConfiguration(Status='Enabled'),
        #WebsiteConfiguration=WebsiteConfiguration

    ))
    # bucketPolicy = t.add_resource(BucketPolicy(
    #     "BucketPolicy",
    #     Bucket=Ref(bucket),
    #     PolicyDocument={
    #           "Version": "2012-10-17",
    #           "Id": "PutObjPolicy",
    #           "Statement": [
    #             {
    #               "Sid": "DenyIncorrectEncryptionHeader",
    #               "Effect": "Deny",
    #               "Principal": "*",
    #               "Action": "s3:PutObject",
    #               "Resource": Join('/',[GetAtt(bucket,'Arn'),'*']),
    #               "Condition": {
    #                 "StringNotEquals": {
    #                   "s3:x-amz-server-side-encryption": "AES256"
    #                 }
    #               }
    #             },
    #             {
    #               "Sid": "DenyUnEncryptedObjectUploads",
    #               "Effect": "Deny",
    #               "Principal": "*",
    #               "Action": "s3:PutObject",
    #               "Resource": Join('/',[GetAtt(bucket,'Arn'),'*']),
    #               "Condition": {
    #                 "Null": {
    #                   "s3:x-amz-server-side-encryption": "true"
    #                 }
    #               }
    #             }
    #           ]
    #         }
    # ))
    #Create necessary Lambda IAM Roles
    #EDW Subnet Groups

    t.add_output(Output(
        'BucketArn',
        Value=GetAtt(bucket, 'Arn')
        ),
    )

def createFiles(fileName):
    global t
    global parameters
    #Create Cloudformation Templates and Parameter files
    #Write template out to file.
    with open('../Template-{}.json'.format(fileName),'wb') as f:
        f.write(t.to_json())
        json.encoder
    # Write a parameter file for Template with default values or empty strings
    with open('../Parameters-{}.json'.format(fileName),'wb') as f:
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
