import json
import boto3
def lambda_handler(event, context):
    redshift = boto3.client('redshift')
    print 'Event contents'
    print json.dumps(event)
    print 'Message Contents'
    message = json.loads(event['Records'][0]['Sns']['Message'])
    print json.dumps(message)
    for dimension in message['Trigger']['Dimensions']:
        if dimension['name']=='ClusterIdentifier':
            clusterId=dimension['value']
    if not clusterId is None:
        print 'Shutting down redshift clusterId: {}'.format(clusterId)
        response = redshift.delete_cluster(ClusterIdentifier=clusterId,SkipFinalClusterSnapshot=True)
        print 'Shutdown Response:{}'.format(response)
