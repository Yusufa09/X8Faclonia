import socket
from pynput import keyboard

# CONFIGURATION: Replace with your Raspberry Pi's actual IP address
PI_IP = "192.168.1.XX" 
PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
active_keys = set()

def send_cmd(msg):
    sock.sendto(msg.encode(), (PI_IP, PORT))

def on_press(key):
    try:
        k = key.char.lower()
        if k in ['w', 'a', 's', 'd'] and k not in active_keys:
            active_keys.add(k)
            send_cmd(k)
    except AttributeError:
        pass

def on_release(key):
    try:
        k = key.char.lower()
        if k in active_keys:
            active_keys.remove(k)
            # If no movement keys are currently held, tell the robot to stop
            if not any(x in active_keys for x in ['w', 'a', 's', 'd']):
                send_cmd('stop')
    except AttributeError:
        pass
    if key == keyboard.Key.esc:
        return False # Stop the listener

print(f"Controller Ready. Controlling Pi at {PI_IP}")
print("Use WASD to drive. Press ESC to quit.")

with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
