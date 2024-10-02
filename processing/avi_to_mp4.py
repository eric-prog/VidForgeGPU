import subprocess

def convert_avi_to_mp4(avi_file_path, output_name):
    try:
        command = [
            'ffmpeg',
            '-i', avi_file_path,
            '-ac', '2',
            '-b:v', '2000k',
            '-c:a', 'aac',
            '-c:v', 'libx264',
            '-b:a', '160k',
            '-vprofile', 'high',
            '-bf', '0',
            '-strict', 'experimental',
            '-f', 'mp4',
            f'{output_name}.mp4'
        ]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error converting {avi_file_path}: {e}")
        return False