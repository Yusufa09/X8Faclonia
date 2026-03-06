import socket
import board
from adafruit_motorkit import MotorKit

# Initialize the MotorKit
kit = MotorKit(i2c=board.I2C())

# Networking Setup
UDP_IP = "0.0.0.0" # Listen on all network interfaces
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

def drive(m1_speed, m2_speed):
    kit.motor1.throttle = m1_speed
    kit.motor2.throttle = m2_speed

print("Robot Server Active. Waiting for Sam's commands...")

while True:
    data, addr = sock.recvfrom(1024)
    cmd = data.decode().strip()

    if cmd == 'w':   # Forward
        drive(0.6, 0.6)
    elif cmd == 's': # Backward
        drive(-0.6, -0.6)
    elif cmd == 'a': # Sharp Left Turn
        drive(-0.5, 0.5)
    elif cmd == 'd': # Sharp Right Turn
        drive(0.5, -0.5)
    elif cmd == 'stop': # All motors off
        drive(0, 0)
