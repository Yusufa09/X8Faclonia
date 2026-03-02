# ...existing code...
#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO

device_path = "/sys/bus/iio/devices/iio:device0/"
TRIG = 11
ECHO = 12

def ultrasonicSetup():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(TRIG, GPIO.OUT)
    GPIO.setup(ECHO, GPIO.IN)
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.05)

def distance(timeout=0.03):
    # send trigger pulse
    GPIO.output(TRIG, GPIO.LOW)
    time.sleep(0.000002)
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG, GPIO.LOW)

    start_time = time.time()
    # wait for echo high
    while GPIO.input(ECHO) == 0:
        if time.time() - start_time > timeout:
            return None
    pulse_start = time.time()

    # wait for echo low
    while GPIO.input(ECHO) == 1:
        if time.time() - pulse_start > timeout:
            return None
    pulse_end = time.time()

    duration = pulse_end - pulse_start
    distance_cm = (duration * 340.0) / 2.0 * 100.0
    return distance_cm

def read_humiture():
    try:
        with open(device_path + "in_temp_input", "r") as f:
            temp = int(f.read().strip()) / 1000.0
        with open(device_path + "in_humidityrelative_input", "r") as f:
            hum = int(f.read().strip()) / 1000.0
        return temp, hum
    except Exception:
        return None, None

def loop():
    ultrasonicSetup()
    try:
        while True:
            dis = distance()
            if dis is None:
                print("Distance: timeout")
            else:
                print(f"Distance: {dis:.2f} cm")
            temp, hum = read_humiture()
            if temp is None or hum is None:
                print("Humiture: no data")
            else:
                print(f"Temperature: {temp:.2f} °C, Humidity: {hum:.2f} %")
            print("")
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        destroy()

def destroy():
    GPIO.cleanup()

if __name__ == "__main__":
    loop()
