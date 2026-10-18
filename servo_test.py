from pyfirmata2 import Arduino, SERVO
import time

# pin -> rest angle (matches cameraModual.py; thumb joint limited to 95..175)
REST = {8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 175, 3: 90}

board = Arduino('/dev/cu.usbmodem2101')
for p in REST:
    board.digital[p].mode = SERVO
time.sleep(0.5)
for p, a in REST.items():
    board.digital[p].write(a)

print("Servos at rest. Type: <pin> <angle>   e.g. 8 90   (r = all to rest, Ctrl+C = quit)")
try:
    while True:
        s = input("> ").split()
        if s == ['r']:
            for p, a in REST.items():
                board.digital[p].write(a)
            continue
        if len(s) != 2 or not s[0].isdigit() or not s[1].isdigit():
            print("format: <pin> <angle>"); continue
        p, a = int(s[0]), max(0, min(180, int(s[1])))
        if p not in REST:
            print("pin must be one of", list(REST)); continue
        if p == 13:
            a = max(95, min(175, a))
        board.digital[p].write(a)
        print(f"pin {p} -> {a}")
except KeyboardInterrupt:
    pass
finally:
    board.exit()
