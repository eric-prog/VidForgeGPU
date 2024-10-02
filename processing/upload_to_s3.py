import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
import os

def upload_file_to_s3(file_name, bucket, object_name=None):
    """
    Upload a file to an S3 bucket using stored AWS credentials.
    
    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified, file_name is used.
    """
    if object_name is None:
        object_name = file_name

    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )

    try:
        s3_client.upload_file(file_name, bucket, object_name)
        print(f"File uploaded to {bucket}/{object_name}")
    except NoCredentialsError:
        print("Credentials not available or incorrect.")
    except Exception as e:
        print(f"Failed to upload {file_name} to S3: {str(e)}")
