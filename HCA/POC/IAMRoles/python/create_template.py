import troposphere,argparse,json, os,sys
from troposphere import Template, Parameter, Ref, Equals
from troposphere import If, Output, Join, GetAtt
from troposphere.iam import Policy, Role, ManagedPolicy

TEMPLATE_NAME = "IamPoliciesEDW"

def buildCloudFormationTemplate():
    global t
    global parameters
    global applicationTags
    t = Template()
    parameters={}
    t.add_version("2010-09-09")
    t.add_description("Deploys required IAM Policies and Roles for solution")

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
    pass
    # parameters["AlarmPeriod"] = t.add_parameter(Parameter(
    #     "AlarmPeriod",
    #     Description="The amount of seconds to gather data for this alarm",
    #     Type="Number",
    #     Default=300,
    # ))
def addConditions():
    pass

def addResources():
    global t
    global applicationTags
    #Redshift Cluster Resource

    #Add all policy documents from folder
    folderpath=os.path.dirname(os.path.abspath(sys.argv[0]))
    policies={}
    for  root, dirs, files in os.walk(folderpath):
        for file_ in files:
            if file_.endswith('.policy'):
                print file_
                policyName = file_.replace('.policy','')
                with open(file_,'r') as f:
                    policyDoc = json.load(f)
                    policies[policyName] = t.add_resource(Policy(
                                                policyName,
                                                PolicyDocument=policyDoc,
                                                PolicyName=policyName
                                            ))

    name='Ec2MatillionRole'
    matillionRole = t.add_resource(Role(
        name,
        AssumeRolePolicyDocument={
                                   "Version" : "2012-10-17",
                                   "Statement": [ {
                                      "Effect": "Allow",
                                      "Principal": {
                                         "Service": [ "ec2.amazonaws.com" ]
                                      },
                                      "Action": [ "sts:AssumeRole" ]
                                   } ]
                                },
        #ManagedPolicyArns=[ String, ... ],
        #Path="/",
        Policies=[Ref(policies['Ec2MatillionPolicy'])],
        RoleName=Join('',[Ref('AWS::Region'),name])
    ))

    name='RedshiftDatalakeSpectrum'
    RedshiftDatalakeSpectrum = t.add_resource(Role(
        name,
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
        #ManagedPolicyArns=[ String, ... ],
        #Path="/",
        Policies=[Ref(policies['SpectrumDatalakePolicy'])],
        RoleName=Join('',[Ref('AWS::Region'),name])
    ))

    name='RedshiftOdsSpectrum'
    RedshiftOdsSpectrum = t.add_resource(Role(
        name,
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
        #ManagedPolicyArns=[ String, ... ],
        #Path="/",
        RoleName=Join('',[Ref('AWS::Region'),name])
    ))



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
