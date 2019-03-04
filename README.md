Easily perform Bulk Label Quality Assurance using Amazon SageMaker Ground Truth
================

With the code in this repo, and accompanying [AWS blog post](TO DO ADD LINK), we’re going to walk you through an example situation where you’ve just built a machine learning system that labels your data at volume and you want to perform manual quality assurance (QA) on some of the labels. How can you do so without overwhelming your limited resources?  We’ll show you how, by using an [Amazon SageMaker Ground Truth](https://aws.amazon.com/sagemaker/groundtruth/) [custom labeling workflow](https://docs.aws.amazon.com/sagemaker/latest/dg/sms-custom-templates.html).

Rather than asking your workers to validate items one at a time, you’ll accomplish this by presenting a batch of already-labeled items that have been assigned the same label. You’ll ask the worker to mark any that aren’t correct. In this way, a workforce is able to quickly assess a much larger quantity of data than what they could label from scratch in the same time. 
Use cases that may require quality assurance include:
* Require subject matter expert review and approval of labels before using them for sensitive use cases.
* Review the labels to test the quality of the label-producing model. 
* Identify and count mislabeled items, correct them, and feed them back into the training set. 
* Analyze label correctness versus confidence levels assigned by the model. 
* Understand whether a single threshold can be applied to all label classes, or whether using different thresholds for different classes is more appropriate. 
* Explore using a simpler model to label some initial data, then improve the model by using QA to validate the results and retrain.

This example uses a subset of the [CalTech 101 dataset](http://www.vision.caltech.edu/Image_Datasets/Caltech101/) from [AWS Open Datasets for image classification](https://registry.opendata.aws/fast-ai-imageclas/). We've provided three prelabeled subsets for you:
* smallsample.csv
* sample.csv
* shellfish.csv  

# To Deploy
Follow the instructions in this [AWS Blog post](https: < TO DO - UPDATE >) to set up a private labeling workforce, and to see the code in action.

To deploy manually (i.e., without using the blog "Launch template" bucket):
* Clone this repo
* Copy the files into an S3 bucket, into a directory with the name "bulkqa"
* Follow the instructions in the blog. 
* Instead of using the blog's "Launch" button: From the AWS CloudFormation console, execute the template s3://<your_bucket>/bulkqa/bulkqa-template.yaml
* Adjust the S3 bucket name to point to your S3 bucket
* Follow the remainder of the instructions in the blog.


## License Summary

This sample code is made available under a modified MIT license. See the LICENSE file.

