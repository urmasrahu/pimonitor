import datetime
from multi_blinkt import blinky
import os
import time
from threading import Thread
from gpiozero import CPUTemperature


NETWORK_POLLING_INTERVAL_SECONDS = 300
NETWORK_LED_INDEX = 5

CPU_TEMP_POLLING_INTERVAL_SECONDS = 60
CPU_TEMP_LED_INDEX = 6

# LED colors
COLOR_WHILE_CHECKING = (0, 0, 16)
COLOR_OK = (0, 8, 0)
COLOR_ERROR = (255, 0, 0)

# colors for terminal output
COLOR_TERM_ALERT = '\033[91m'
COLOR_TERM_OK = '\033[92m'
COLOR_TERM_BLUE_BACKGR = '\033[44m'
COLOR_TERM_END = '\033[0m'



IP_ADDRESS = "192.168.10.1" # will ping this address to check for connection, e.g. use your home router address


def GetTimeString():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class BaseMonitor(Thread):
    def __init__(self, led, index_led, polling_interval):
        Thread.__init__(self, daemon=True)
        self.led = led
        self.index_led = index_led
        self.polling_interval = polling_interval

    def TurnLedOff(self):
        self.led.Off(self.index_led)


class NetworkMonitor(BaseMonitor):
    def __init__(self, led):
        BaseMonitor.__init__(self, led=led, index_led=NETWORK_LED_INDEX, polling_interval=NETWORK_POLLING_INTERVAL_SECONDS)
        
    def IsNetworkAlive(self):
        ret = os.system(F"ping -c 3 {IP_ADDRESS}")
        return ret == 0
    
    def run(self):
        while True:
            self.led.On(self.index_led, COLOR_WHILE_CHECKING)
            alive = self.IsNetworkAlive()
            print (f"{COLOR_TERM_OK if alive else COLOR_TERM_ALERT}{GetTimeString()} Ping: {'OK' if alive else 'FAILED'}{COLOR_TERM_END}")
            self.led.On(self.index_led, COLOR_OK if alive else COLOR_ERROR)
            time.sleep(self.polling_interval)


class CpuTempMonitor(BaseMonitor):
    def __init__(self, led):
        BaseMonitor.__init__(self, led=led, index_led=CPU_TEMP_LED_INDEX, polling_interval=CPU_TEMP_POLLING_INTERVAL_SECONDS)
        self.FULL_GREEN_LEVEL = 60
        self.FULL_RED_LEVEL = 80
        self.MAX_BRIGHTNESS = 10 # adjust LED brightness with this, max value is 255
        
    def GetColorForCpuTemp(self, temperature):
        level = temperature
        if level < self.FULL_GREEN_LEVEL:
            level = self.FULL_GREEN_LEVEL
        elif level > self.FULL_RED_LEVEL:
            level = self.FULL_RED_LEVEL
            
        # map temperature to the range 0 - MAX_BRIGHTNESS
        level = (level - self.FULL_GREEN_LEVEL) * (self.MAX_BRIGHTNESS / (self.FULL_RED_LEVEL - self.FULL_GREEN_LEVEL))
        
        red = int(level)
        green = int(self.MAX_BRIGHTNESS - level)
        blue = 0
        
        return (red, green, blue)
        
    def run(self):
        while True:
            temperature = CPUTemperature().temperature
            print(f"{COLOR_TERM_BLUE_BACKGR}CPU temperature: {temperature}{COLOR_TERM_END}")
            color = self.GetColorForCpuTemp(temperature)
            self.led.On(self.index_led, color)
            time.sleep(self.polling_interval)
    


class MultiMonitor:
    def __init__(self):
        self.led = blinky.Blinkt()
        self.net_monitor = NetworkMonitor(self.led)
        self.cpu_temp_monitor = CpuTempMonitor(self.led)
        self.monitors = [self.net_monitor, self.cpu_temp_monitor]
        
    def Run(self):
        for monitor in self.monitors:
            monitor.start()
        
        try:
            for monitor in self.monitors:
                monitor.join()
        except KeyboardInterrupt:
            for monitor in self.monitors:
                monitor.TurnLedOff()
            print("Exiting")
    


### =============== MAIN PROGRAM STARTS HERE ===============

monitor = MultiMonitor()
monitor.Run()
