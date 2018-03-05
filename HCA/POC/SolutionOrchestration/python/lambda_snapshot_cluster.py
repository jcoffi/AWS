###this is the Lambda function that is triggered by lambda_broker_3
###and will take a snapshot of the Matillion Redshift cluster

import json,time
import boto3
from httplib import HTTPException

def lambda_handler(event, context):

    message = json.loads(event['Records'][0]['Sns']['Message'])

    print json.dumps(message, indent=4, sort_keys=True)

    #Create Cluster Snapshot for EDW Solution
    redshift_client = boto3.client('redshift')

    snapshotId=str(int(time.time())) #unique id for snapshotName as EpcoHTime
    clusterIdKeyName = 'clusterIdentifier'

    try:
        clusterIdentifier = message[clusterIdKeyName]
    except KeyError:
        print "Need to provide a '{}' key value to take a snapshot of Redshift Cluster".format(clusterIdKeyName)

    response = redshift_client.create_cluster_snapshot(
        SnapshotIdentifier='manual-{}-{}'.format(clusterIdentifier,snapshotId),
        ClusterIdentifier=clusterIdentifier
    )

    if response['ResponseMetadata']['HTTPStatusCode']!=200:
        raise HTTPException(
            "Lambda failed to take snapshot from Redshift Cluster {} with response: {}".format(
            clusterIdentifier,
            response)
        )
