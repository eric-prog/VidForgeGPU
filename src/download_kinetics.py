import sys
import subprocess
import time
from vast_celery_setup import launch_vast_ai_instances, setup_celery_worker_on_vast
from celery import Celery
import math
from dotenv import load_dotenv
import os

def start_redis():
    """Start Redis server in the background."""
    print("Starting Redis server...")
    redis_process = subprocess.Popen(['redis-server'])
    time.sleep(2)  # Give Redis a couple of seconds to start up
    return redis_process

def start_vast_celery_workers(num_instances):
    """Launch GPU instances on Vast.ai and setup Celery workers on them."""
    instance_ids = launch_vast_ai_instances(num_instances)
    for instance_id in instance_ids:
        setup_celery_worker_on_vast(instance_id)
    return instance_ids

def check_celery_tasks(celery_app):
    """Check the status of Celery tasks to see if all tasks are finished."""
    inspector = celery_app.control.inspect()
    while True:
        active_tasks = inspector.active() or {}
        reserved_tasks = inspector.reserved() or {}

        if not active_tasks and not reserved_tasks:
            print("All Celery tasks are finished.")
            break

        print("Waiting for Celery tasks to finish...")
        time.sleep(10)  # Check every 10 seconds

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 download_kinetics.py <url_list> <output_dir>")
        sys.exit(1)

    url_list = sys.argv[1]
    output_dir = sys.argv[2]

    # Start Redis server
    redis_process = start_redis()

    # Launch Vast.ai instances and set up Celery workers
    num_vast_instances = 2 
    vast_instance_ids = start_vast_celery_workers(num_vast_instances)

    # init Celery app
    # app = Celery('vidforge', broker='redis://localhost:6379/0')
    # Update Celery to connect to the global Redis server
    # app = Celery('process', broker='redis://localhost:6379/0')

    # Replace 'localhost' with your global Redis server IP.
    GLOBAL_REDIS_IP = os.getenv('IP_ADDRESS')
    app = Celery('vidforge', broker=f'redis://{GLOBAL_REDIS_IP}:6379/0')

    try:
        # Read URLs from the .txt file and submit them as tasks
        print(f"Starting distributed download: URL List = {url_list}, Output Directory = {output_dir}")

        with open(url_list, 'r') as f:
            urls = f.read().splitlines()
        
        # Split URLs into chunks for each worker
        chunk_size = math.ceil(len(urls) / num_vast_instances)
        url_chunks = [urls[i:i + chunk_size] for i in range(0, len(urls), chunk_size)]

        # # Submit the download tasks to the Celery worker
        # for chunk in url_chunks:
        #     app.send_task('process.download_tar_file', args=[chunk, output_dir])  # Assuming you want to handle tar.gz files
        #     # For other file types, you can create another task if necessary

        # Submit the download tasks to the Celery worker (tasks will be sent to global Redis)
        for chunk in url_chunks:
            app.send_task('process.process_video', args=[chunk, output_dir])  # Correct task name

        # Wait for tasks to finish
        check_celery_tasks(app)

    finally:
        # Cleanup: Stop Redis and terminate all Vast.ai instances
        print("Stopping Redis...")
        redis_process.terminate()

        for instance_id in vast_instance_ids:
            print(f"Terminating instance {instance_id}...")
            subprocess.run(['vastai', 'destroy', 'instance', str(instance_id)])
        print("Vast.ai instances terminated.")
