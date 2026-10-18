# Hand-tracking robotic hand: my build

A 3D-printed, tendon-driven robotic hand that mirrors my own hand in real time from a webcam. Built in October 2026 in London.

The code in this repository is mine. The idea of pairing this printed hand with MediaPipe and PyFirmata2 came from [pathofseb/RoboticArm](https://github.com/pathofseb/RoboticArm), which I used while getting the hardware working before writing my own version.

- **Hardware**: [Humanoid Robotic Hand by grossrc](https://www.thingiverse.com/thing:2269115) on Thingiverse (CC BY-NC). Assembly follows the designer's video [How to Assemble the Forearm and Hand of the PROTO1 Robot](https://www.youtube.com/watch?v=L2ddw3MQl9g).

What I changed, what went wrong, and how I fixed it is below.

## How it works

1. The Mac's camera captures video. MediaPipe finds 21 hand landmarks per frame.
2. For each finger the script decides up or down (fingertip above or below its knuckle) and the roll angle of the hand.
3. PyFirmata2 sends servo angles to an Arduino Uno running StandardFirmata.
4. Each finger has a fishing-line tendon on the palm side pulled by a servo in the forearm, and a shock cord on the back that straightens it again when the servo releases. A micro servo in the palm swings the thumb across; a servo in the forearm cup rotates the wrist.

## Parts

Electronics

| Part | Qty | Notes |
|---|---|---|
| Arduino Uno Rev3 | 1 | USB powers the Arduino only |
| Sensor Shield V5.0 | 1 | Servo headers (G, V, S) for all seven servos |
| MG996R standard servo | 5 | Four fingers plus wrist rotation |
| MG90S micro servo | 1 | Thumb rotation, pin 13 |
| 5 V 10 A DC power supply with DC socket adapter | 1 | Feeds the shield's servo rail through the screw terminal |
| Servo extension cables | 7 | The MG90S lead and the block leads do not reach the shield on their own |
| USB-A to USB-B cable | 1 | Mac to Arduino |
| Jumper wires | | Already had them |

Mechanical

| Part | Qty | Notes |
|---|---|---|
| 0.6 mm fishing line | | Tendons, five lengths of about 60 cm |
| 3 mm shock cord | | Finger return springs, one per finger |
| Superglue | | Horns into the thumb piece, knots |
| M3 x 6 mm screws | | Horn centre screws if the servo bags are short |

Printed parts (PLA, 0.2 mm layers, standard infill, supports only where needed)

- Hand5 (palm)
- Fingerdesign_ALL (all finger segments)
- Hand5Thumb3 (thumb base and segments)
- ServoHorn x 4 (printed ring that sits round the servo's round disc horn; the gap in the ring anchors the line)
- Servo_Hold (block that carries four MG996R in the forearm)
- Forearm9-1 (forearm trough)
- Forarm_9-2 / 9-3 (wrist cup that holds the rotation servo)
- E5P1 is in the Thingiverse set but is not needed for the hand on its own; I did not print it.

## Software setup (macOS)

Python 3.12 is needed. The current MediaPipe (1.x) has dropped `mp.solutions`, which the script uses, and the last version that still has it (0.10.21) has no Python 3.13 wheel.

```
# Python 3.12.10 from python.org, then:
python3.12 -m venv roboarm
source roboarm/bin/activate
pip install mediapipe==0.10.21 opencv-python==4.11.0.86 numpy==1.26.4 pyfirmata2==2.5.1
```

Arduino side: Arduino IDE, File > Examples > Firmata > StandardFirmata, upload to the Uno. Close the IDE (or at least the Serial Monitor) before running any Python, otherwise the port is busy.

Find the port with `ls /dev/cu.usbmodem*` and put it in the `PORT` line at the top of both scripts.

## Wiring and power

Pin map (set at the top of `hand_mirror.py`):

| Pin | Servo |
|---|---|
| 8 | Thumb bend |
| 9 | Index |
| 10 | Middle |
| 11 | Ring |
| 12 | Pinky |
| 13 | Thumb rotation (MG90S), limited to 95 to 175 degrees |
| 3 | Wrist rotation |

Servo leads: brown or black to G, red to V, orange or yellow to S.

Power: the SEL jumper cap on the Sensor Shield is removed, so the servo rail is fed only from the external 5 V supply on the shield's screw terminal (GND and VCC). The USB cable powers the Arduino and nothing else. Seven servos on USB power would brown out the board.

Switch-on order: power supply first, then USB. Switch-off: Ctrl+C in the script, USB out, then the power supply. Put the servos at rest before switching off so nothing is holding tension unpowered.

## Assembly notes and changes from the original

Conventions I settled on, which matter for everything below:

- Finger servos: 0 degrees is open (finger straight), 180 is closed. The printed ring horn goes on with its gap pointing towards the hand end at 0 degrees.
- Wrist: 0 degrees has the open side of the cup facing forward, 180 faces back.
- Thumb rotation: 175 is out to the side, 95 is across the palm.

Changes and fixes, in the order I met them:

1. **Wrist horn position.** The designer screws the star horn to the outside face of the trough floor. The black horn screw in my MG996R bag was too short to reach the shaft through the floor, and there was a gap between horn and shaft. I put the star on the inside of the floor with its hub through the hole. The screw now reaches and the servo is held in the cup.
2. **Thumb limits.** With the thumb base fitted, the MG90S growled and warmed up when held at 180 or 90. It is quiet at 175 and 95, so those are the limits in both scripts (`THUMB_OUT` and `THUMB_IN`). The thumb base also rubbed the palm; a little trimming of the palm cutout helps.
3. **Lead order.** First run with the camera, the wrong fingers moved. The four block leads were in mirrored order on the shield. Test each with `servo_test.py`, then plug the lead that moves the index into 9, middle 10, ring 11, pinky 12.
4. **Tendon tension.** Two lines were tied too long: the horn turned but the finger did not. Right tension is: finger straight at 0 with no droop, fingertip touching the palm at 180, no growling at either end. Tie with the servo at 0, line pulled taut and let back about 2 mm, one wrap round the horn groove, through the gap, knot, superglue.
5. **Horn screws.** The black M3 screw in each MG996R bag is the horn centre screw. Fit them with the servos at 0 before the lines go under tension.
6. **Port busy.** `Resource busy: /dev/cu.usbmodem2101` every time means the Arduino IDE Serial Monitor is still open. `lsof | grep usbmodem` shows what has it.
7. **Camera permission.** macOS asks once; Terminal needs restarting after you allow it or the camera stays "not authorized".
8. **Jitter.** MediaPipe flickers between open and closed on a finger that is half bent, which makes the servo chatter. `hand_mirror.py` only moves a finger once the camera has agreed on its state for three frames in a row (`STABLE_FRAMES`), and the wrist angle is smoothed.

## Scripts

`hand_mirror.py` is the main program. It opens the camera, finds one hand with MediaPipe, classes each finger as open or closed (tip above or below its middle joint; for the thumb, tip further from the pinky knuckle than its middle joint is), measures the hand's roll from the line across the knuckles, and writes the servo angles over Firmata. Everything that depends on the build (port, camera, pins, open and closed angles, thumb limits, wrist mirroring) is in the settings block at the top. On quit it returns every servo to rest before closing the port.

`servo_test.py` puts every servo at rest, then lets you type `<pin> <angle>` to move one at a time. `r` returns everything to rest, Ctrl+C quits. Used for fitting horns, calibrating the wrist and thumb, finding the lead order and setting tendon tension.

```
source roboarm/bin/activate
python servo_test.py
> 9 180
> 9 0
> r
```

## Running

```
source roboarm/bin/activate
python hand_mirror.py
```

Hold your right hand about 50 cm from the camera, palm facing it, in good light. The window shows the finger states (O open, _ closed) and the wrist angle. Press `q` in the video window to stop. Each finger is either fully open or fully closed; MediaPipe's joint angles are too unsteady to drive the servos proportionally without a lot more filtering.

## Still to do

- Decide whether the wrist direction needs mirroring (`WRIST_MIRROR = True` if it turns the wrong way).
- Thicker wires from the power supply to the screw terminal.
- A stand using the four holes in the base of the wrist cup.
- Try a USB webcam (`cv2.VideoCapture(1)`) for a better angle than the laptop camera.
