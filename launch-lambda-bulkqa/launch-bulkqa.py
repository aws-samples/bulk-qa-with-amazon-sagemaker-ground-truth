"""
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Information Block.

This code receives an event from CloudFormation with a Bucket and DynamoDB table name.
    It then populates the S3 bucket with a subset of images from the Caltech 101 dataset
    and the DynamoDB table with labels for each image. On Stack Deletion, the code will empty the S3 bucket.
API Triggers: CloudFormation Custom Resource
Services: S3, DynamoDB
Python 3.7 - AWS Lambda - Last Modified 2/1/2019
"""

import csv
import json
import logging
import os
import tarfile
import urllib.request
import cfnresponse
import boto3
import botocore


# Initialize Boto3 Clients and Resources
s3 = boto3.client('s3')
dynamodb_client = boto3.client('dynamodb')
s3_resource = boto3.resource('s3')


def lambda_handler(event, context):
    setup_logging()
    log.info('Received event!')
    log.info(event)

    s3_bucket = event['ResourceProperties']['S3Bucket']
    dynamodb_table = event['ResourceProperties']['DynamoDBTable']
    launch_bucket = event['ResourceProperties']['LaunchBucket']
    label_corpus_key = event['ResourceProperties']['LabelCorpusKey']
    caltech101_dataset_url = event['ResourceProperties']['CALTECH101URL']
    qa_batch_size = int(event['ResourceProperties']['QABatchSize'])
    responseData = {}
    try:
        if event['RequestType'] == 'Create':
            deploy_bulkqa_lab(dynamodb_table, s3_bucket, launch_bucket, label_corpus_key, caltech101_dataset_url, qa_batch_size)
        elif event['RequestType'] == 'Delete':
            teardown_bulkqa_lab(s3_bucket)
        else:
            log.info('Event received is not a "Delete" Event. Code is taking no action.')
        cfnresponse.send(event, context, cfnresponse.SUCCESS, responseData)
    except:
        cfnresponse.send(event, context, cfnresponse.FAILED, responseData)
        raise


def deploy_bulkqa_lab(dynamodb_table, s3_bucket, launch_bucket, label_corpus_key, caltech101_dataset_url, qa_batch_size):
    # Download Label Corpus
    log.info("Downloading Label Corpus from " + launch_bucket + "/"  + label_corpus_key)
    try:
        s3_resource.Bucket(launch_bucket).download_file(label_corpus_key, '/tmp/corpus.csv')
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            log.error("The Label Corpus does not exist at s3://" + launch_bucket + "/" + label_corpus_key)
            log.error(e)
            raise e
        else:
            log.error(e)
            raise e

    # Download and untar CALTECH101 Dataset
    log.info("Downloading CALTECH101 Dataset from " + caltech101_dataset_url)

    urllib.request.urlretrieve(caltech101_dataset_url, '/tmp/101_ObjectCategories.tgz')

    tar = tarfile.open('/tmp/101_ObjectCategories.tgz')
    tar.extractall(path='/tmp')
    tar.close()

    # Upload Images relevant to the job to S3
    log.info("Uploading CALTECH101 test images to " + s3_bucket)

    caltech101_image_dir = '/tmp/101_ObjectCategories/'

    manifest_dict = {}

    with open('/tmp/corpus.csv', mode='rt') as deployment_file:
        deployment_reader = csv.DictReader(deployment_file, delimiter=',', quotechar='"')
        for row in deployment_reader:
            image_url = 's3://' + s3_bucket + '/' + row['image_local_path']
            #Load to S3
            log.info("Uploading image to:\t" + image_url )
            s3.upload_file(caltech101_image_dir + row['image_local_path'], s3_bucket, row['image_local_path'])
            # Load to DynamoDB
            log.info(row)
            log.info("PutItem " + image_url + " into DynamoDB" )
            dynamodb_item = {
                    "s3_image_url": {
                        "S": image_url
                    },
                    "label": {
                        "S": row["label"]
                    },
                    "confidence": {
                        "N": str(row["confidence"])
                    },
            }
            dynamodb_client.put_item(TableName=dynamodb_table, Item=dynamodb_item)

            # Add item to manifest

            manifest_item = {
                "s3_image_url": image_url,
                "label": row["label"],
                "confidence":  str(row["confidence"]),
            }
            if manifest_dict.get(row['label']) is None:
                manifest_dict[row['label']] = [manifest_item]
            else:
                manifest_dict[row['label']].append(manifest_item)

    # Build list of custom label inputs
    custom_labeling_input_list = []
    for label in manifest_dict:
        labeled_images = manifest_dict[label]
        chunks_of_labeled_images = [labeled_images[i:i + qa_batch_size] for i in range(0, len(labeled_images), qa_batch_size)]
        for chunk_of_labeled_images in chunks_of_labeled_images:
            custom_labeling_input_list.append(chunk_of_labeled_images)

    manifest_filename = "manifest.json"
    manifest_local = '/tmp/' + manifest_filename
    s3_manifest_path = s3_bucket + manifest_filename
    custom_labeling_input_parent_dir = "custom-labeling-inputs/"
    s3_custom_labeling_input_parent_dir = 's3://' + s3_bucket + '/' + custom_labeling_input_parent_dir
    count = 0

    with open(manifest_local, mode='w') as manifest_out:
        for batch in custom_labeling_input_list:

            custom_labeling_input_path = custom_labeling_input_parent_dir + str(count) + '.json'
            s3_custom_labeling_input_path = 's3://' + s3_bucket + '/' + custom_labeling_input_path
            manifest_line = {'source-ref': s3_custom_labeling_input_path }

            if count == 0:
                manifest_out.write(json.dumps(manifest_line))
            else:
                manifest_out.write('\n' + json.dumps(manifest_line))

            with open('/tmp/' + str(count) + '.json', mode='w') as custom_labeling_input_out:
                json.dump(batch, custom_labeling_input_out)

            log.info("Uploading custom labeling input to:\t" + s3_custom_labeling_input_path )
            s3.upload_file('/tmp/' + str(count) + '.json', s3_bucket, custom_labeling_input_path)
            count = count + 1

    s3.upload_file(manifest_local, s3_bucket, manifest_filename)
    log.info("Uploading manifest to:\t" + manifest_filename)


def teardown_bulkqa_lab(s3_bucket):
    bucket = s3_resource.Bucket(s3_bucket)
    # Empty S3 bucket
    bucket.objects.all().delete()
    log.info("Emptied bucket " + s3_bucket)


def setup_logging():
    global log
    log = logging.getLogger()
    valid = ['INFO', 'WARNING', 'ERROR']
    desired = os.environ.get('logging_level', 'ERROR').upper()
    if desired not in valid:
        desired = 'ERROR'
    log.setLevel(desired)

