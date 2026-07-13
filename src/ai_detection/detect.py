import cv2
from ultralytics import YOLO

# Load trained model
model = YOLO("weights/best.pt")

# Path to input video
video_path = "test.mp4"   # Change this to your video name

# Open video
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

frame_number = 0

while True:
    ret, frame = cap.read()

    if not ret:
        break

    frame_number += 1

    # Run YOLO on the current frame
    results = model(frame, conf=0.25)

    height, width = frame.shape[:2]

    # Draw coordinate grid every 100 pixels
    for x in range(0, width, 100):
        cv2.line(frame, (x, 0), (x, height), (70, 70, 70), 1)

    for y in range(0, height, 100):
        cv2.line(frame, (0, y), (width, y), (70, 70, 70), 1)

    # Draw axes
    cv2.line(frame, (0, 0), (width, 0), (255, 0, 0), 2)
    cv2.line(frame, (0, 0), (0, height), (255, 0, 0), 2)

    cv2.putText(
        frame,
        "(0,0)",
        (5, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )

    detection_found = False

    # Process detections
    for result in results:
        for box in result.boxes:

            detection_found = True

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            confidence = float(box.conf[0])

            # Center coordinates
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Draw center point
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)

            # Label
            cv2.putText(
                frame,
                f"Drone {confidence:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

            # Coordinates on video
            cv2.putText(
                frame,
                f"({cx}, {cy})",
                (cx + 10, cy + 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2,
            )

            # Print coordinates to PowerShell
            print(
                f"Frame {frame_number} | X = {cx} | Y = {cy} | Confidence = {confidence:.2f}"
            )

    if not detection_found:
        print(f"Frame {frame_number} | No drone detected")

    # Show video
    cv2.imshow("Drone Detection", frame)

    # Press Q to quit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print("Finished processing video.")