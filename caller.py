from tkinter import *
from tkinter import ttk
from PIL import ImageTk, Image
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PyHT6022.LibUsbScope import Oscilloscope
from threading import Thread
import sys
import os
import time

from modules.main_gui import create_main_window

def get_data():
    while isRun:
        global x_signal
        global y_signal
        global buffer_size_x
        global buffer_size_y
        scope.start_capture()
        adc_signals = scope.read_data(data_size=0xC00, raw=False)
        buffer_size_x = len(adc_signals[0])
        buffer_size_y = len(adc_signals[1])
        x_signal = scope.scale_read_data(adc_signals[0])
        y_signal = scope.scale_read_data(adc_signals[1])

def init():
    line.set_data([], [])
    return line,

# Update function: called for each frame
def update(frame):
    global x_signal
    global y_signal
    global buffer_size_x
    global buffer_size_y

    # Define the data to plot by taking a slice of the data list
    plot_x_signal = [x_signal[frame] for frame in range(buffer_size_x)]
    plot_y_signal = [y_signal[frame] for frame in range(buffer_size_y)]

    line.set_data(plot_x_signal, plot_y_signal)  # Update the plot with the new data
    return line,

def on_closing():
    global isRun
    isRun = False
    scope.stop_capture()
    time.sleep(0.5)
    scope.close_handle()
    thread.join()
    root.quit()
    root.destroy()
    sys.exit()

isRun = True
scope = Oscilloscope()
scope.setup()
if not scope.open_handle():
    print("oscilloscope not detected")
    sys.exit(-1)

# upload correct firmware into device's RAM
if not scope.is_device_firmware_present:
    scope.flash_firmware()

# read calibration values from EEPROM
calibration = scope.get_calibration_values()

# set interface: 0 = BULK, >0 = ISO, 1=3072,2=2048,3=1024 bytes per 125 us
scope.set_interface(0) # use BULK unless you have specific need for ISO xfer

scope.set_num_channels(2)
scope.set_sample_rate(102)

# set the gain for CH1 and CH2
scope.set_ch1_voltage_range(1)
scope.set_ch2_voltage_range(1)

# Data list
buffer_size_x = 3072
buffer_size_y = 3072
x_signal = []
y_signal = []

thread = Thread(target = get_data)
thread.start()

# Creating main window
root = Tk()
root.protocol('WM_DELETE_WINDOW', on_closing)
frequency = StringVar()
voltage = StringVar()
impedance = StringVar()

# Create a figure and axis
fig, ax = plt.subplots()
ax.set_xlim(-5, 5)
ax.set_ylim(-5, 5)
ax.set_xticklabels([])
ax.set_yticklabels([])
line, = ax.plot([], [], lw=1)  # Empty plot to update

# The signal
canvas = FigureCanvasTkAgg(fig, master=create_main_window(root, scope, frequency, voltage, impedance))
canvas.get_tk_widget().pack()

ani = FuncAnimation(fig, update, frames=100, init_func=init, blit=True, interval=0.01)
plt.title('V-I Trace')
plt.grid()
plt.yticks([n for n in range(-5, 5)])
plt.xticks([n for n in range(-5, 5)])

root.mainloop()
