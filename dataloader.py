import os
import cv2
import torch
from torch.utils.data import Dataset, DataLoader

class VideoDataset(Dataset):
    def __init__(self, video_dir):
        self.video_files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith('.mp4')]
        
    def __len__(self):
        return len(self.video_files)

    def __getitem__(self, idx):
        video_path = self.video_files[idx]
        cap = cv2.VideoCapture(video_path)
        frames = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = torch.tensor(frame).permute(2, 0, 1)  # Convert to (C, H, W) format
            frames.append(frame)
        
        cap.release()
        frames = torch.stack(frames)
        return frames

def train_dummy_model(data_loader):
    """
    Dummy model training loop that just iterates through the video frames.
    Replace this with your actual model training logic later.
    """
    for i, video_batch in enumerate(data_loader):
        print(f"Processing batch {i + 1} of {len(data_loader)}")
        # Dummy "training" step
        torch.cuda.empty_cache()

if __name__ == "__main__":
    video_dir = "./processed_videos"
    dataset = VideoDataset(video_dir)
    loader = DataLoader(dataset, batch_size=1, shuffle=True)
    
    train_dummy_model(loader)
