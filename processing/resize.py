import os
import subprocess
import ffmpeg
import random

def get_video_dimensions(file_path):
    """Get the dimensions of the video using ffprobe."""
    try:
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        width, height = map(int, result.stdout.decode().strip().split('\n'))
        return width, height
    except subprocess.CalledProcessError as e:
        print(f"Error getting video dimensions: {e.stderr.decode()}")
        return None, None


def resize_video(input_file, output_file, target_width, target_height):
    """Resize the video to the target dimensions."""
    try:
        original_width, original_height = get_video_dimensions(input_file)
        if original_width is None or original_height is None:
            return
        
        aspect_ratio = original_width / original_height
        if target_width / aspect_ratio <= target_height:
            new_width = target_width
            new_height = int(target_width / aspect_ratio)
        else:
            new_width = int(target_height * aspect_ratio)
            new_height = target_height

        new_width -= new_width % 2
        new_height -= new_height % 2
        
        ffmpeg.input(input_file).filter('scale', new_width, new_height).output(output_file).run()
        os.remove(input_file)
        print(f"Resized video saved to: {output_file}")
    except Exception as e:
        print(f"Error resizing video: {e}")


def random_crop_video(input_file, output_file, crop_width=256, crop_height=256):
    """Apply random cropping to a video, but skip cropping if video dimensions are already 256x256."""
    try:
        # Get the dimensions of the video
        original_width, original_height = get_video_dimensions(input_file)
        if original_width is None or original_height is None:
            return

        # If the video is already 256x256, no cropping is needed
        if original_width == crop_width and original_height == crop_height:
            print(f"Video {input_file} is already {crop_width}x{crop_height}, skipping cropping.")
            os.rename(input_file, output_file)  # Simply rename/move the file
            return

        # Ensure the crop size is less than the original dimensions
        if crop_width > original_width or crop_height > original_height:
            print("Crop dimensions exceed original video dimensions. Resizing instead.")
            resize_video(input_file, output_file, crop_width, crop_height)
            return

        # Calculate random crop starting point
        x_offset = random.randint(0, original_width - crop_width)
        y_offset = random.randint(0, original_height - crop_height)

        print(f"Cropping video at x: {x_offset}, y: {y_offset}, width: {crop_width}, height: {crop_height}")

        # Apply the crop using ffmpeg
        ffmpeg.input(input_file).crop(crop_width, crop_height, x_offset, y_offset).output(output_file).run()

        # Remove the original file after cropping
        os.remove(input_file)
        print(f"Cropped video saved to: {output_file}")
    except Exception as e:
        print(f"Error cropping video: {e}")
