"""Basic idea for an X-Y scope with the Hantek HT6022 oscilloscope"""
import sys
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from PyHT6022.LibUsbScope import Oscilloscope
from threading import Thread
from tkinter import *
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

def get_data():
    while isRun:
        global x_signal
        global y_signal
        scope.start_capture()
        adc_signals = scope.read_data(data_size=0xC00, raw=False)
        x_signal = scope.scale_read_data(adc_signals[0])
        y_signal = scope.scale_read_data(adc_signals[1])


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

# Initialize function: plot the background of each frame
def init():
    line.set_data([], [])
    return line,

# Update function: called for each frame
def update(frame):
    global x_signal
    global y_signal
    global data_length
    # Create a rolling window of the data to animate
    window_size = 3072  # Size of the window to show

    # Define the data to plot by taking a slice of the data list
    plot_x_signal = [x_signal[frame] for frame in range(window_size)]
    plot_y_signal = [y_signal[frame] for frame in range(window_size)]

    line.set_data(plot_x_signal, plot_y_signal)  # Update the plot with the new data
    return line,

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
x_signal = []
y_signal = []
data_length = 256

# Create a figure and axis
fig, ax = plt.subplots()
ax.set_xlim(-5, 5)  # x-axis limits (length of data)
ax.set_ylim(-5, 5)
line, = ax.plot([], [], lw=0.5)  # Empty plot to update

thread = Thread(target = get_data)
thread.start()

root = Tk()
root.protocol('WM_DELETE_WINDOW', on_closing)

canvas = FigureCanvasTkAgg(fig, master = root)
canvas._tkcanvas.grid(row = 0, column = 0)

# Create animation
ani = FuncAnimation(fig, update, frames=100, init_func=init, blit=True, interval=0.01)

plt.title('Oscilloscope X-Y?')
plt.xlabel('Index')
plt.ylabel('Value')

# Display the animation
# plt.show()

root.mainloop()

