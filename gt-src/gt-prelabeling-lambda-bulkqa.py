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

This code receives an event from SageMaker Groundtruth before a worker starts a task.
    The event contains a URI for a custom labeling input object in S3. The code reads
    the custom labeling input into memory and serializes it into JSON for input into a
    SageMaker Ground Truth labelling task.
API Triggers: SageMaker Ground Truth
Services: S3, DynamoDB
Python 3.7 - AWS Lambda - Last Modified 2/1/2019
"""

import json
import logging
import os
import re
import boto3


# Initialize Boto3 Client
s3 = boto3.client('s3')


def lambda_handler(event, context):
    setup_logging()
    # Load source-object whether in test or prod
    if 'source-ref' in event['dataObject']:
        source_uri = event['dataObject']['source-ref']
    elif 'source' in event['dataObject']:
        source_uri = event['dataObject']['source']
    else:
        log.error("No source data found in input")
        raise ClientError

    # Load custom labeling input object from S3
    custom_labeling_input = json.loads(read_s3_object(source_uri))

    return {
            "taskInput": {
                "sourceRef" : custom_labeling_input
            }
        }


def setup_logging():
    global log
    log = logging.getLogger()
    valid = ['INFO', 'WARNING', 'ERROR']
    desired = os.environ.get('logging_level', 'ERROR').upper()
    if desired not in valid:
        desired = 'ERROR'
    log.setLevel(desired)


def read_s3_object(s3_uri):
	# parse full s3 path to get s3 bucket & s3 key
	s3_regex = 's3://([^/]*)/(.*)'
	s3r = re.search(s3_regex, s3_uri)
	s3_bucket = s3r.group(1)
	s3_key = s3r.group(2)
	textFile = s3.get_object(Bucket = s3_bucket, Key = s3_key)
	filecont = textFile['Body'].read()
	return filecont
