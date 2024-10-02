# Get Started

1) First install reqs:

```bash
pip3 install -r requirements.txt
```

2) Download Kinetic-400 train dataset

```bash
python3 src/run_download.py
```

3) Setup Vast API

```bash
vastai set api-key <your_api_key>
```

<img src="/assets/vast.png">

4) ENV VARS

5) Start!

```bash
python3 download_kinetics.py kinetics-dataset/k400_targz/k400_train_path.txt ./kinetics-videos
```