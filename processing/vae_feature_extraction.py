import torch
from diffusers import AutoencoderKL
from torchvision import transforms
import cv2
import os
from upload_to_s3 import upload_file_to_s3

vae_model = AutoencoderKL.from_pretrained("stabilityai/sd-vae-ft-mse")
vae_model.eval()

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Resize((256, 256)),
])

def extract_vae_features(video_file, output_dir, bucket_name=None):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    video_name = os.path.splitext(os.path.basename(video_file))[0]
    cap = cv2.VideoCapture(video_file)
    
    vae_features = []
    segment_frame_count = 0
    frames_per_segment = 20  # 4 FPS for 5 seconds = 20 frames
    batch_index = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if segment_frame_count < frames_per_segment:
            frame_tensor = transform(frame).unsqueeze(0)
            with torch.no_grad():
                latents = vae_model.encode(frame_tensor)
            vae_features.append(latents.squeeze(0))

            segment_frame_count += 1

        if segment_frame_count >= frames_per_segment:
            feature_path = os.path.join(output_dir, f"{video_name}_vae_features_batch_{batch_index}.pt")
            torch.save(torch.stack(vae_features), feature_path) 
            print(f"Saved batch of VAE features: {feature_path}")
            if bucket_name:
                upload_file_to_s3(feature_path, bucket_name, f"vae_features/{os.path.basename(feature_path)}")
            vae_features.clear()
            segment_frame_count = 0 
            batch_index += 1 

    cap.release()

    if vae_features:
        feature_path = os.path.join(output_dir, f"{video_name}_vae_features_batch_{batch_index}.pt")
        torch.save(torch.stack(vae_features), feature_path)
        print(f"Saved final VAE features: {feature_path}")
        if bucket_name:
            upload_file_to_s3(feature_path, bucket_name, f"vae_features/{os.path.basename(feature_path)}")

    return feature_path
