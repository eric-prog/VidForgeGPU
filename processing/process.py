import os
from celery import Celery  # Import Celery
from avi_to_mp4 import convert_avi_to_mp4
from resize import random_crop_video
from vae_feature_extraction import extract_vae_features
from upload_to_s3 import upload_file_to_s3
import logging
from dotenv import load_dotenv
import os

# app = Celery('process', broker='redis://localhost:6379/0')
# Replace 'localhost' with your global Redis server IP.
GLOBAL_REDIS_IP = os.getenv('IP_ADDRESS')
app = Celery('process', broker=f'redis://{GLOBAL_REDIS_IP}:6379/0')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.task 
def process_video(file_path, output_dir, target_width=256, target_height=256, bucket_name="kinetics-400"):
    """Process the video - convert if necessary, resize, crop, then extract VAE features, and upload to S3."""
    
    logger.info(f"Starting processing for video: {file_path}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_ext = os.path.splitext(file_path)[1]
    if file_ext == ".avi":
        converted_file = os.path.join(output_dir, os.path.basename(file_path).replace(".avi", ".mp4"))
        if not convert_avi_to_mp4(file_path, converted_file):
            logger.error(f"Error converting {file_path}")
            return False
        logger.info(f"Converted {file_path} to .mp4")
        os.remove(file_path)
        file_path = converted_file

    resized_file = os.path.join(output_dir, os.path.basename(file_path))
    random_crop_video(file_path, resized_file, crop_width=target_width, crop_height=target_height)
    upload_file_to_s3(resized_file, bucket_name, f"{os.path.basename(resized_file)}")
    logger.info(f"Resized and cropped {file_path} to 256x256")

    vae_features_path = extract_vae_features(resized_file, output_dir, bucket_name=bucket_name)
    logger.info(f"Extracted VAE features for {file_path}")

    if bucket_name and vae_features_path:
        upload_file_to_s3(vae_features_path, bucket_name, f"{os.path.basename(vae_features_path)}")
        logger.info(f"Uploaded VAE features {vae_features_path} to S3")

    if os.path.exists(resized_file):
        os.remove(resized_file)
        logger.info(f"Deleted resized file {resized_file} after processing")

    return True
