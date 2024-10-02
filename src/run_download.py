import subprocess
import os

def clone_repo():
    """Clone the Kinetics dataset GitHub repository if it doesn't already exist."""
    if not os.path.exists('kinetics-dataset'):
        print("Cloning the kinetics-dataset repository...")
        try:
            subprocess.run(['git', 'clone', 'https://github.com/cvdfoundation/kinetics-dataset.git'], check=True)
            print("Repository cloned successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error cloning the repository: {e}")
            exit(1)
    else:
        print("Repository already cloned. Skipping clone.")

def download_kinetics_metadata(split):
    """Download the URL metadata file."""
    metadata_file = f'kinetics-dataset/k400_targz/{split}.txt'
    if not os.path.exists(metadata_file):
        print(f"Downloading {split} metadata file...")
        url = f"https://s3.amazonaws.com/kinetics/400/{split}/k400_{split}_path.txt"
        subprocess.run(['wget', '-P', 'kinetics-dataset/k400_targz/', url])
    return metadata_file

if __name__ == "__main__":
    # First, clone the repo to ensure it's present
    clone_repo()

    # Download the metadata for the train/validation/test split
    split = 'train'  # modify this to 'val' or 'test'
    download_kinetics_metadata(split)
