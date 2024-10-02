import subprocess
import time
import json
from celery import Celery
from dotenv import load_dotenv
import os

load_dotenv()

app = Celery('process', broker='redis://localhost:6379/0')

SSH_KEY_PATH = os.getenv('SSH_KEY_PATH')
LOCAL_PROCESSING_PATH = os.getenv('LOCAL_PROCESSING_PATH')
NUM_INSTANCES = 2

def search_vast_ai_offers(max_dph=0.5):
    """Search for suitable GPU offers on Vast.ai and extract offer IDs."""
    print(f"Searching for GPU offers with max $/hr <= {max_dph}...")
    
    result = subprocess.run(
        ['vastai', 'search', 'offers', f'dph_total<={max_dph}', '--raw'],  # Filters for cheaper GPUs
        capture_output=True,
        text=True
    )

    # Debugging: Print the raw output from the CLI command
    print("Raw output from Vast.ai search:", result.stdout)
    
    if result.stdout:
        try:
            offers = json.loads(result.stdout)
            offer_ids = [offer['id'] for offer in offers]  # Iterate over the list directly
            
            if offer_ids:
                print(f"Found {len(offer_ids)} offers.")
                return offer_ids  # Return all available offer IDs for further processing
            else:
                print("No suitable offers found.")
                return None
        except json.JSONDecodeError:
            print("Failed to decode JSON.")
            return None
    else:
        print("No offers found or failed to get offers.")
        return None

def launch_vast_ai_instances(num_instances=10):
    """Launch GPU instances on Vast.ai and return their IDs."""
    instance_ids = []

    for _ in range(num_instances):
        offer_ids = search_vast_ai_offers()
        if not offer_ids:
            print("No suitable offers found. Exiting.")
            break

        offer_id = offer_ids[0]  # Just picking the first offer for simplicity
        print(f"Launching instance with offer ID: {offer_id}")
        result = subprocess.run(
            ['vastai', 'create', 'instance', str(offer_id), '--image', 'pytorch/pytorch', '--disk', '32', '--raw'],
            capture_output=True,
            text=True
        )

        # Parse the result to extract the new contract (instance ID)
        try:
            instance_info = json.loads(result.stdout)
            instance_id = instance_info['new_contract']
            print(f"Instance launched: {instance_id}")
            instance_ids.append(instance_id)
        except json.JSONDecodeError:
            print(f"Failed to launch instance: {result.stderr}")
            continue

        time.sleep(2)  # To prevent overloading the API

    return instance_ids

def setup_celery_worker_on_vast(instance_id, max_retries=5, retry_delay=20):
    """SSH into the instance, upload local files, install Celery, Redis, and Python dependencies, then start the Celery worker."""
    
    # Wait for the instance to be ready
    time.sleep(60)  # Increased wait time to ensure the instance is fully ready

    # Fetch the SSH URL from Vast.ai CLI
    ssh_url_cmd = f"vastai ssh-url {instance_id}"
    try:
        ssh_url = subprocess.check_output(ssh_url_cmd, shell=True).decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        print(f"Failed to fetch SSH URL: {e}")
        return

    # Extract the address and port from the ssh_url
    if ssh_url.startswith('ssh://'):
        ssh_url = ssh_url.replace('ssh://', '')

    # Split the ssh_url into user, host, and port
    user_host, port = ssh_url.rsplit(':', 1)

    # Upload the local processing folder to the remote instance using scp
    scp_command = f"scp -i {SSH_KEY_PATH} -P {port} -r {LOCAL_PROCESSING_PATH} {user_host}:/root/"
    print(f"Uploading processing folder: {scp_command}")
    
    for attempt in range(max_retries):
        try:
            subprocess.run(scp_command, shell=True, check=True)
            print(f"Successfully uploaded processing folder to {user_host}")
            break
        except subprocess.CalledProcessError as e:
            print(f"SCP command failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Exiting.")
                return

    # Start Redis server in the background
    # start_redis_command = (
    #     "apt-get update && apt-get install -y redis-server && "
    #     "redis-server --daemonize yes"  # Start Redis in daemon mode
    # )

    # Start Redis server in the background
    start_redis_command = (
        "apt-get update && apt-get install -y redis-server && "
        "redis-server --daemonize yes"  # Start Redis in daemon mode
    )
    print(f"Starting Redis server: {start_redis_command}")
    try:
        subprocess.run(f"ssh -i {SSH_KEY_PATH} -p {port} {user_host} '{start_redis_command}'", shell=True, check=True)
        print("Redis server installed and started.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install or start Redis server: {e}")
        return

    # Optionally, check if Redis is running
    check_redis_command = "redis-cli ping"
    try:
        result = subprocess.check_output(f"ssh -i {SSH_KEY_PATH} -p {port} {user_host} '{check_redis_command}'", shell=True).decode('utf-8').strip()
        if result == "PONG":
            print("Redis is running.")
        else:
            print("Redis is not running. Exiting.")
            return
    except subprocess.CalledProcessError as e:
        print(f"Failed to check Redis status: {e}")
        return

    # Install the necessary dependencies
    install_dependencies_command = (
        f"ssh -i {SSH_KEY_PATH} -p {port} {user_host} "
        f"'curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3 get-pip.py && "
        f"python3 -m pip install celery redis python-dotenv accelerate safetensors[torch] boto3 ffmpeg-python torch torchvision opencv-python diffusers && "
        f"apt-get update && apt-get install -y libgl1-mesa-glx'"
    )

    print(f"Installing Celery and Redis, along with required Python packages: {install_dependencies_command}")
    for attempt in range(max_retries):
        try:
            subprocess.run(install_dependencies_command, shell=True, check=True)
            print(f"Celery, Redis, and required libraries installed on instance {instance_id}")
            break
        except subprocess.CalledProcessError as e:
            print(f"Dependency installation failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Exiting.")
                return

    # # Start the Celery worker after installation
    # start_celery_command = (
    #     f"ssh -i {SSH_KEY_PATH} -p {port} {user_host} "
    #     f"'cd /root/processing && "
    #     f"export CELERY_BROKER_URL=redis://localhost:6379/0 && "
    #     f"python3 -m celery -A process worker --loglevel=info --concurrency=2 &'"
    # )

    # app = Celery('process', broker='redis://localhost:6379/0')
    # Replace 'localhost' with your global Redis server IP.
    GLOBAL_REDIS_IP = os.getenv('IP_ADDRESS')
    # Replace localhost with the global Redis IP
    start_celery_command = (
        f"ssh -i {SSH_KEY_PATH} -p {port} {user_host} "
        f"'cd /root/processing && "
        f"export CELERY_BROKER_URL=redis://{GLOBAL_REDIS_IP}:6379/0 && "
        f"python3 -m celery -A process worker --loglevel=info --concurrency=2 &'"
    )

    print(f"Starting Celery worker: {start_celery_command}")
    for attempt in range(max_retries):
        try:
            subprocess.run(start_celery_command, shell=True, check=True)
            print(f"Celery worker started on instance {instance_id}")
            break
        except subprocess.CalledProcessError as e:
            print(f"Failed to start Celery worker on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Exiting.")
                return

if __name__ == "__main__":
    instance_ids = launch_vast_ai_instances(NUM_INSTANCES)

    if instance_ids:
        for instance_id in instance_ids:
            setup_celery_worker_on_vast(instance_id)
    
    print(f"All {NUM_INSTANCES} instances have been set up and are running Celery workers.")
