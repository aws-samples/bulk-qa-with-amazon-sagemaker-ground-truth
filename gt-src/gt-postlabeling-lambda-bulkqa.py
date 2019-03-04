"""
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Information Block.

This code receives an event from SageMaker Groundtruth when a worker completes a task.
    It processes the workers annotations and stores them in a DynamoDB Table.

API Triggers: SageMaker Ground Truth
Services: S3, DynamoDB
Python 3.7 - AWS Lambda - Last Modified 2/1/2019
"""

import decimal
import json
import logging
import os
import re
import boto3
from botocore.exceptions import ClientError


# Initialize Boto3 Clients and Resources
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')


def lambda_handler(event, context):
    setup_logging()
    consolidated_labels = []

    dynamodb_tbl_name = os.environ['DynamoDBTable']
    dynamodb_tbl = dynamodb.Table(dynamodb_tbl_name)

    # Load from s3
    annotations = json.loads(read_s3_object(event['payload']['s3Uri']))

    for dataset in annotations:
        for annotation in dataset['annotations']:

            human_annotation = json.loads(annotation['annotationData']['content'])

            # Load original machine annotation into memory
            machine_annotation_record = json.loads(read_s3_object(dataset['dataObject']['s3Uri']))
            machine_and_worker_annotations = zip(machine_annotation_record, list(map(lambda key: human_annotation[key]['Confirmed'], human_annotation.keys() )))

            # Update Records in DynamoDB
            for new_annotation in machine_and_worker_annotations:
                print(new_annotation)
                if new_annotation[1]: # Confirmed
                    try:
                        response = dynamodb_tbl.update_item(
                            Key={
                                's3_image_url': new_annotation[0]['s3_image_url'],
                                'label': new_annotation[0]['label']
                            },
                            UpdateExpression="ADD WorkerConfirmCount :num",
                            ExpressionAttributeValues={
                                ':num': 1
                            },
                            ReturnValues="ALL_NEW"
                        )
                    except ClientError as e:
                        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                            log.error(e.response['Error']['Message'])
                        else:
                            raise
                    else:
                        log.info("UpdateItem succeeded:")
                        log.info(json.dumps(response, indent=4, cls=DecimalEncoder))
                else:
                    try:
                        response = dynamodb_tbl.update_item(
                            Key={
                                's3_image_url': new_annotation[0]['s3_image_url'],
                                'label': new_annotation[0]['label']
                            },
                            UpdateExpression='ADD WorkerDisconfirmCount :num',
                            ExpressionAttributeValues={
                                ':num': 1
                            },
                            ReturnValues="ALL_NEW"
                        )
                    except ClientError as e:
                        if e.response['Error']['Code'] == "ConditionalCheckFailedException":
                            log.error(e.response['Error']['Message'])
                        else:
                            raise
                    else:
                        log.info("UpdateItem succeeded:")
                        log.info(json.dumps(response, indent=4, cls=DecimalEncoder))

            # Return Label for groundtruth
            labels = {
                'datasetObjectId': dataset['datasetObjectId'],
                'consolidatedAnnotation' : {
                'content': {
                    event['labelAttributeName']: {
                        'workerId': annotation['workerId'],
                        'workerAnnotation': human_annotation,
                        'machineAnnotationRecord': dataset['dataObject']
                        }
                    }
                }
            }
            consolidated_labels.append(labels)
    return consolidated_labels


def read_s3_object(s3_uri):
    # parse full s3 path to get s3 bucket & s3 key
    s3_regex = 's3://([^/]*)/(.*)'
    s3r = re.search(s3_regex, s3_uri)
    s3_bucket = s3r.group(1)
    s3_key = s3r.group(2)
    textFile = s3.get_object(Bucket = s3_bucket, Key = s3_key)
    filecont = textFile['Body'].read()
    return filecont



def setup_logging():
    global log
    log = logging.getLogger()
    valid = ['INFO', 'WARNING', 'ERROR']
    desired = os.environ.get('logging_level', 'ERROR').upper()
    if desired not in valid:
        desired = 'ERROR'
    log.setLevel(desired)


class DecimalEncoder(json.JSONEncoder):
    """
    Helper class to convert a DynamoDB item to JSON.
    """
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)
