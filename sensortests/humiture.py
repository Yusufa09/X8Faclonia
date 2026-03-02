import time

device_path = "/sys/bus/iio/devices/iio:device0/"

def read_sensor():
    try:
        with open(device_path + "in_temp_input", "r") as f:
            temp = int(f.read()) / 1000
        with open(device_path + "in_humidityrelative_input", "r") as f:
            hum = int(f.read()) / 1000
        
        print(temp, hum)
    
    except Exception as e:
        print("dsauihdhas")
while True:
    read_sensor()
    time.sleep(2)