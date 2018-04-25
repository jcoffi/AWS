import troposphere,argparse,json,os,sys
from troposphere import Template, Parameter, Ref, Equals
from troposphere import If, Output, Join, GetAtt, Not
from troposphere.redshift import Cluster, ClusterParameterGroup,LoggingProperties, AmazonRedshiftParameter
from troposphere.iam import Role, Policy
from troposphere.constants import LIST_OF_SECURITY_GROUP_IDS

TEMPLATE_NAME = "Edw_Redshift"

def buildCloudFormationTemplate():
    global t
    global parameters
    global applicationTags
    t = Template()
    parameters={}
    t.add_version("2010-09-09")
    t.add_description("Deploys a Redshift Cluster for EDMS EDW Project")

    applicationTags = troposphere.Tags(
        Application="Enterprise Data Warehouse POC",
        Environment=Ref("Environment"),
        Team="EDMS",
        Project="EDW",
        Category="4",
        HIPPA='Yes'
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

    #Begin Redshift Parameters EDWPOCS3Key
    # parameters["EDWPOCS3Key"] = t.add_parameter(Parameter(
    # "EDWPOCS3Key",
    # Description="KMS Key to Encrypt the Database and S3 with.",
    # Type="String",
    # Default="Key Id"
    # # AllowedPattern="([a-z]|[0-9]|\-|_)+"
    # )),
    parameters["KMSS3Key"] = t.add_parameter(Parameter(
    "KMSS3Key",
    Description="KMS Key to Encrypt the Database with.",
    Type="String",
    Default="arn:aws:kms:region:account-id:key/key-id"
    # AllowedPattern="([a-z]|[0-9]|\-|_)+"
    )),
    parameters["KMSRedshiftKey"] = t.add_parameter(Parameter(
        "KMSRedshiftKey",
        Description="KMS Key to Encrypt the Database with.",
        Type="String",
        Default="arn:aws:kms:region:account-id:key/key-id"
        # AllowedPattern="([a-z]|[0-9]|\-|_)+"
    )),
    # parameters["s3LogBucketArn"] = t.add_parameter(Parameter(
    #     "s3LogBucketArn",
    #     Description="Arn of s3 bucket used for logging.",
    #     Type="String",
    #     Default="arn:s3:::mybucketname"
    # )),
    parameters["EDWBucket"] = t.add_parameter(Parameter(
        "EDWBucket",
        Description="Arn of s3 bucket used for data storage.",
        Type="String",
        Default="arn:s3:::mybucketname"
    )),
    # parameters["LoggingBucket"] = t.add_parameter(Parameter(
    #     "LoggingBucket",
    #     Description="Arn of s3 bucket used for data storage.",
    #     Type="String",
    #     Default="arn:s3:::loggingbucketname"
    # )),
    parameters["Environment"] = t.add_parameter(Parameter(
        "Environment",
        Description="Type of Environment being deployed",
        Type="String",
        Default="dev",
        AllowedValues=['dev','test','prod']
    )),
    parameters["EnvironmentTypeIndex"] = t.add_parameter(Parameter(
        "EnvironmentTypeIndex",
        Description="Index integer of envrionment type to distinguish between multiple environments within accounts. I.e. the '01', and '02' in dev-01, dev-02, test-01",
        Type="String",
        Default="01"
    )),
    parameters["ClusterSubnetGroupName"] = t.add_parameter(Parameter(
        "ClusterSubnetGroupName",
        Description="The name of the Cluster Subnet Group where to place your cluster when creating a Cluster in your VPC",
        Type="String",
        Default="edw-subnetgroup",
        AllowedPattern="([a-z]|[0-9]|\-|_)+"
    ))
    parameters["VPCSecurityGroups"] = t.add_parameter(Parameter(
        "VPCSecurityGroups",
        Description="The list of VPC security groups to be associated with cluster.",
        Type=LIST_OF_SECURITY_GROUP_IDS
    ))
    parameters["AdminUserPassword"] = t.add_parameter(Parameter(
        "AdminUserPassword",
        Description="The password associated with the Admin user account for the redshift cluster that is being created.",
        Type="String",
        Default="!Race2Win!",
        NoEcho=True
    )),
    parameters["SnapshotIdentifier"] = t.add_parameter(Parameter(
        "SnapshotIdentifier",
        Description="OPTIONAL. The name of the snapshot from which to create a new cluster.",
        Type="String",
        Default=""
    )),
    parameters['SnapshotClusterIdentifier'] = t.add_parameter(Parameter(
        "SnapshotClusterIdentifier",
        Description="OPTIONAL. The name of the cluster that the source snapshot was created from. This property is required if your IAM policy includes a restriction on the cluster name and the resource element specifies anything other than the wildcard character (*) for the cluster name.",
        Type="String",
        Default=""
    ))

def addConditions():
    #Prepare Conditions
    conditions = {
        "IsProdCluster": Equals(
            Ref("Environment"),
            "prod"
        ),
        "IsSnapshoptRestore":
                        Not(

                                    Equals(Ref("SnapshotIdentifier"),"")

                            )
        ,
        "IsSnapshotClusterIdentifierNotEmpty":
                        Not(

                                    Equals(Ref("SnapshotClusterIdentifier"),"")

                            )
    }
    # "IsEncrypted": Equals(
    #     Ref("Encrypted"),
    #     True
    # ),
    # "IsPubliclyAccessible": Equals(
    #     Ref("PubliclyAccessible"),
    #     True
    # ),
    for k in conditions:
        t.add_condition(k, conditions[k])

def addResources():
    global t
    global applicationTags
    #Redshift Cluster Resource
    redshiftPolicy = Policy(
                            'RedshiftIamPolicy',
                            PolicyDocument= {
                                            "Version" : "2012-10-17",
                                            "Statement": [
                                                            {
                                                                "Sid": "ReadOnlyAccess",
                                                                "Effect": "Allow",
                                                                "Action": ["s3:Get*", "s3:List*"],
                                                                "Resource": [
                                                                            Join("",["arn:aws:s3:::",Ref('EDWBucket'),"/landing/*"]),
                                                                            Join("",["arn:aws:s3:::",Ref('EDWBucket'),"/raw/*"])
                                                                            ]
                                                            },
                                                            # {
                                                            #     "Sid": "EnterpriseLogging",
                                                            #     "Effect": "Allow",
                                                            #     "Action": ["s3:GetBucketAcl", "s3:PutObject"],
                                                            #     "Resource": [
                                                            #                 Join("",["arn:aws:s3:::",Ref('LoggingBucket'),'/*'])
                                                            #                 ,Join("",["arn:aws:s3:::",Ref('LoggingBucket')])
                                                            #                 # Join("",["arn:aws:s3:::",Ref('LoggingBucket'),"/",Join("-",["edw-poc",Ref("Environment"),Ref("EnvironmentTypeIndex")]),"/*"])
                                                            #                 ]
                                                            # },
                                                            {
                                                                "Sid": "KmsS3Encryption",
                                                                "Effect": "Allow",
                                                                   "Action": [
                                                                                "kms:Encrypt",
                                                                                "kms:Decrypt",
                                                                                "kms:ReEncrypt*",
                                                                                "kms:GenerateDataKey*",
                                                                                "kms:DescribeKey",
                                                                                "kms:ListGrants",
                                                                                "kms:CreateGrant",
                                                                                "kms:RevokeGrant"
                                                                            ],
                                                                "Resource": [
                                                                            Ref("KMSRedshiftKey"),
                                                                            Ref("KMSS3Key"),
                                                                            ]
                                                            },
                                                            {
                                                                "Sid": "RWAccessToEdw",
                                                                "Effect": "Allow",
                                                                "Action": ["s3:Get*", "s3:Put*", "s3:List*"],
                                                                "Resource": [
                                                                                Join("",["arn:aws:s3:::",Ref('EDWBucket')]),
                                                                                Join("",["arn:aws:s3:::",Ref('EDWBucket'),"/source/*"]),
                                                                                Join("",["arn:aws:s3:::",Ref('EDWBucket'),"/edw/*"])
                                                                            ]
                                                            }
                                                        ]
                                        }
                            ,
                            PolicyName=Join('-',['edw','redshift','policy',Ref('Environment'),Ref('EnvironmentTypeIndex')])
                        )
    redshiftIamRole = t.add_resource(Role(
        'RedshiftIamRole',
        AssumeRolePolicyDocument={
                                   "Version" : "2012-10-17",
                                   "Statement": [ {
                                      "Effect": "Allow",
                                      "Principal": {
                                         "Service": [ "redshift.amazonaws.com" ]
                                      },
                                      "Action": [ "sts:AssumeRole" ]
                                   } ]
                                },
        Policies=[redshiftPolicy],
        RoleName=Join('-',['edw','redshift','role',Ref('Environment'),Ref('EnvironmentTypeIndex')])
    ))

    redshiftCluster = t.add_resource(Cluster(
        "RedshiftCluster",
        #--Cluster Details
        NodeType=If("IsProdCluster","dc2.8xlarge", "dc2.8xlarge"),
        NumberOfNodes=If("IsProdCluster","2", "2"), #Integer,
        ClusterParameterGroupName=Ref("RedshiftClusterParameterGroup"),
        ClusterType="multi-node",
        #ClusterVersion=Ref("AWS::NoValue"),
        #--Cluster Networking & Security
        Port=5439, #Integer
        #AvailabilityZone=Ref("AvailabilityZone"), #String,
        ClusterSubnetGroupName=Ref("ClusterSubnetGroupName"),
        VpcSecurityGroupIds= Ref("VPCSecurityGroups"),
        PubliclyAccessible=False,
        #ElasticIp=If("PubliclyAccessible",Ref("ElasticIp"), Ref("AWS::NoValue")), #String,
        Encrypted= True,
        KmsKeyId= Ref("KMSRedshiftKey"), #String,
        HsmClientCertificateIdentifier= Ref("AWS::NoValue"), #String,
        HsmConfigurationIdentifier= Ref("AWS::NoValue"), #String,
        IamRoles= [GetAtt(redshiftIamRole,'Arn')], #[ String, ... ],
        ##Only use with EC2 Classic
        #ClusterSecurityGroups=Ref("RedshiftClusterSecurityGroup"),
        #--Database specific properties
        DBName='public',
        MasterUsername='admin',
        MasterUserPassword=Ref("AdminUserPassword"),
        #--Maintenance Items
        #DeletionPolicy=If(Ref("PubliclyAccessible")=="dev",Ref("ElasticIp"), Ref("AWS::NoValue")), #String,
        AllowVersionUpgrade="False",
        AutomatedSnapshotRetentionPeriod=1,
        # LoggingProperties = LoggingProperties(
        #                                     BucketName=Ref("LoggingBucket"),
        #                                     S3KeyPrefix=Join("-",["redshift/edw-poc",Ref("Environment"),Ref("EnvironmentTypeIndex")])
        #                                     ), #LoggingProperties,
        #PreferrEDMSintenanceWindow="Sat:00:00-Sun:23:59", #String
        ##If restoring from snapshot
        ##The name of the cluster that the source snapshot was created from. For more information about restoring from a snapshot, see the
        SnapshotClusterIdentifier=If("IsSnapshotClusterIdentifierNotEmpty",Ref('SnapshotClusterIdentifier'),Ref("AWS::NoValue")), #String,
        ##The name of the snapshot from which to create a new cluster.
        SnapshotIdentifier=If("IsSnapshoptRestore",Ref('SnapshotIdentifier'),Ref("AWS::NoValue")),#String,
        ##When you restore from a snapshot from another AWS account, the 12-digit AWS account ID that contains that snapshot.
        # OwnerAccount==Ref("AWS::NoValue"),#String,
        Tags=applicationTags
    ))

    redshiftclusterparametergroup = t.add_resource(ClusterParameterGroup(
        'RedshiftClusterParameterGroup',
        Description='Cluster Parameter Group for EDW POC',
        ParameterGroupFamily='redshift-1.0',
        Parameters=[
                AmazonRedshiftParameter(
                    'enableUserLogging',
                    ParameterName='enable_user_activity_logging',
                    ParameterValue='true')
                 ,AmazonRedshiftParameter(
                     'requireSsl',
                     ParameterName='require_ssl',
                     ParameterValue='true')
                ]
    ))

    t.add_output(Output(
        'ClusterEndpointPort',
        Value=Join('', [
                        'jdbc:redshift://',
                        GetAtt(redshiftCluster, 'Endpoint.Address'),
                        ':',
                        GetAtt(redshiftCluster, 'Endpoint.Port')
                        ]),
    ))
    t.add_output(Output(
        'ClusterEndpoint',
        Value=GetAtt(redshiftCluster, 'Endpoint.Address')
    ))
    t.add_output(Output(
        'RedshiftIamRole',
        Value=GetAtt(redshiftIamRole,'Arn')
    ))

def createFiles(fileName):
    global t
    global parameters
    #Create Cloudformation Templates and Parameter files
    #Write template out to file.
    buildFolderPath=os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))

    with open(os.path.join(buildFolderPath,'Template-{}.json'.format(fileName)),'wb') as f:
        f.write(t.to_json())
        json.encoder
    # Write a parameter file for Template with default values or empty strings
    with open(os.path.join(buildFolderPath,'Parameters-{}.json'.format(fileName)),'wb') as f:
        parameterfile_json=[]
        #loop through parameters in template
        for template_parameter in t.parameters:
            print template_parameter
            #If the parameter, doesn't have a Default value property, set to empty string
            if not hasattr(parameters[template_parameter],'Default'):
                defaultParameterValue="<insert parameter value here>"
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
