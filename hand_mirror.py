"""
hand_mirror.py

Mirrors a hand seen by the webcam onto a 3D-printed, tendon-driven robotic hand.
MediaPipe finds the hand landmarks, each finger is classed as open or closed,
the hand's roll angle is measured, and the angles are sent to servos on an
Arduino Uno running StandardFirmata.

Servo conventions for this build:
  finger servos      0 = open (straight), 180 = closed (tip in the palm)
  thumb rotation     THUMB_OUT = out to the side, THUMB_IN = across the palm
  wrist rotation     0 = open side of the cup facing forward, 180 = facing back

Controls: show your right hand to the camera, palm facing it. Press q to quit.
"""

import math
import sys
import time

import cv2
import mediapipe as mp
from pyfirmata2 import Arduino, SERVO

# ---------------------------------------------------------------- settings --

PORT = '/dev/cu.usbmodem2101'   # ls /dev/cu.usbmodem*
CAMERA = 0                       # 0 = built-in camera, 1 = USB webcam

PIN_THUMB = 8                    # thumb bend
PIN_FINGERS = [9, 10, 11, 12]    # index, middle, ring, pinky
PIN_THUMB_ROT = 13               # MG90S in the palm
PIN_WRIST = 3

OPEN, CLOSED = 0, 180
THUMB_OUT, THUMB_IN = 175, 95    # measured limits, the servo strains beyond these
WRIST_MIRROR = False             # set True if the wrist turns the wrong way

STABLE_FRAMES = 3                # frames a finger must agree before the servo moves
WRIST_SMOOTHING = 0.3            # 0 = frozen, 1 = no smoothing

# ------------------------------------------------------------------- servos --

class Hand:
    def __init__(self, port):
        self.board = Arduino(port)
        self.pins = {}
        for p in [PIN_THUMB, *PIN_FINGERS, PIN_THUMB_ROT, PIN_WRIST]:
            self.board.digital[p].mode = SERVO
            self.pins[p] = self.board.digital[p]
        time.sleep(0.5)
        self.last = {}
        self.rest()

    def write(self, pin, angle):
        angle = int(max(0, min(180, angle)))
        if pin == PIN_THUMB_ROT:
            angle = max(THUMB_IN, min(THUMB_OUT, angle))
        if self.last.get(pin) != angle:
            self.pins[pin].write(angle)
            self.last[pin] = angle

    def rest(self):
        for p in [PIN_THUMB, *PIN_FINGERS]:
            self.write(p, OPEN)
        self.write(PIN_THUMB_ROT, THUMB_OUT)
        self.write(PIN_WRIST, 90)

    def close(self):
        self.rest()
        time.sleep(0.5)
        self.board.exit()

# ----------------------------------------------------------------- tracking --

# MediaPipe landmark ids
WRIST = 0
THUMB_IP, THUMB_TIP = 3, 4
INDEX_MCP, PINKY_MCP = 5, 17
FINGER_PIP = [6, 10, 14, 18]
FINGER_TIP = [8, 12, 16, 20]

def fingers_open(lm):
    """Return [thumb, index, middle, ring, pinky] as True (open) / False (closed).
    lm is the list of 21 normalised landmarks."""
    out = []
    # Thumb: open when its tip is further from the pinky knuckle than its middle joint is.
    tip_d = math.dist((lm[THUMB_TIP].x, lm[THUMB_TIP].y), (lm[PINKY_MCP].x, lm[PINKY_MCP].y))
    ip_d = math.dist((lm[THUMB_IP].x, lm[THUMB_IP].y), (lm[PINKY_MCP].x, lm[PINKY_MCP].y))
    out.append(tip_d > ip_d)
    # Other fingers: open when the tip is above the middle joint (image y grows downwards).
    for pip, tip in zip(FINGER_PIP, FINGER_TIP):
        out.append(lm[tip].y < lm[pip].y)
    return out

def hand_roll(lm):
    """Roll of the hand in degrees, 0..180, from the line across the knuckles."""
    dx = lm[PINKY_MCP].x - lm[INDEX_MCP].x
    dy = lm[PINKY_MCP].y - lm[INDEX_MCP].y
    roll = math.degrees(math.atan2(dy, dx))
    if roll < 0:
        roll += 360
    if roll > 180:
        roll = 360 - roll
    return roll

# --------------------------------------------------------------------- main --

def main():
    print('Connecting to Arduino on', PORT)
    hand = Hand(PORT)

    cap = cv2.VideoCapture(CAMERA)
    if not cap.isOpened():
        print('Camera', CAMERA, 'not available')
        hand.close()
        sys.exit(1)

    hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.7,
                                     min_tracking_confidence=0.6)
    draw = mp.solutions.drawing_utils

    state = [True] * 5          # what the servos are doing now (True = open)
    pending = [True] * 5        # what the camera currently sees
    agree = [0] * 5             # how many frames in a row the camera has agreed
    wrist = 90.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb)

            if result.multi_hand_landmarks:
                lm = result.multi_hand_landmarks[0].landmark
                draw.draw_landmarks(frame, result.multi_hand_landmarks[0],
                                    mp.solutions.hands.HAND_CONNECTIONS)

                seen = fingers_open(lm)
                for i, s in enumerate(seen):
                    if s == pending[i]:
                        agree[i] += 1
                    else:
                        pending[i] = s
                        agree[i] = 1
                    if agree[i] >= STABLE_FRAMES and state[i] != pending[i]:
                        state[i] = pending[i]

                # Fingers
                hand.write(PIN_THUMB, OPEN if state[0] else CLOSED)
                for pin, is_open in zip(PIN_FINGERS, state[1:]):
                    hand.write(pin, OPEN if is_open else CLOSED)
                # Thumb swings across the palm when it is folded
                hand.write(PIN_THUMB_ROT, THUMB_OUT if state[0] else THUMB_IN)

                # Wrist, smoothed
                target = hand_roll(lm)
                if WRIST_MIRROR:
                    target = 180 - target
                wrist += (target - wrist) * WRIST_SMOOTHING
                hand.write(PIN_WRIST, wrist)

                label = ''.join('O' if s else '_' for s in state)
                cv2.putText(frame, f'{label}  wrist {int(wrist)}', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            cv2.imshow('Hand mirror', frame)
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        hand.close()
        print('Servos at rest, closed.')

if __name__ == '__main__':
    main()
