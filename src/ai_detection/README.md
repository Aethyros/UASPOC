# Camera Detection Module

This module performs visual drone detection using a trained YOLOv8 model.

## Contents

- `best.pt` - Trained YOLOv8 model weights.
- `detect.py` - Inference script to run drone detection on images/videos/live streams.

## Requirements

- Python 3.10+
- ultralytics
- opencv-python
- torch
- torchvision

Install the required packages:

```bash
pip install ultralytics opencv-python torch torchvision
```

## Usage

Place the `best.pt` file in the same directory as `detect.py` (or update the model path in the code).

Run:

```bash
python detect.py
```

Modify the `source` parameter inside `detect.py` according to the input source.

Examples:

```python
source = "image.jpg"      # Image
source = "video.mp4"      # Video
source = 0                # Webcam
source = "rtsp://..."     # IP Camera / CCTV Stream
```

## Output

The model detects drones in the input stream and provides:

- Bounding box around the detected drone
- Confidence score
- Drone coordinates (if enabled in the script)

The output video/images are saved automatically if `save=True` is used.

## Notes

- This module is intended for integration into the UAV Detection System.
- The detected coordinates can be passed to other modules such as RF signature matching, tracking, or the GUI.
- Only the trained model (`best.pt`) and inference script are required to run detection. The training dataset and training files are not needed.

## Author

Sugapriyan S