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

def show_frequency():
    frequency.set(frequency.get())

def show_voltage():
    voltage.set(voltage.get())
    if voltage.get() == "200mV":
        scope.set_ch1_voltage_range(10)
        scope.set_ch2_voltage_range(10)
    else:
        scope.set_ch1_voltage_range(1)
        scope.set_ch2_voltage_range(1)

def show_impedance():
    impedance.set(impedance.get())

def capture_trace():
    plt.savefig("image.png")

def init():
    line.set_data([], [])
    return line,

def open_captures():
    captures_window = Toplevel(root)
    captures_window.title("V-I traces captured")
    captures_window.geometry("800x600")
    figs = ttk.Frame(captures_window, padding=3)
    try:
        image = Image.open(os.path.abspath("image2.png"))
        # Print image size to verify it loaded correctly
        print(f"Image size: {image.size}")
        photo = ImageTk.PhotoImage(image)

        # Create canvas and add image
        canvas_figs = Canvas(figs, width=640, height=480)
        canvas_figs.pack()
        canvas_figs.create_image(0, 0, anchor=NW, image=photo)
        # Store reference in root to prevent garbage collection
        canvas.image = photo
        canvas_figs.photo = photo  # This is important!
    except Exception as e:
        print(f"Error loading image: {e}")

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
x_lim_min = -0.5
x_lim_max = 0.5
y_lim_min = -0.5
y_lim_max = 0.5

thread = Thread(target = get_data)
thread.start()

# Creating main window
root = Tk()
#root.geometry("800x600")
root.protocol('WM_DELETE_WINDOW', on_closing)
root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)
root.title("V-I curve tracer")
#root.wm_iconphoto(True, ImageTk.PhotoImage(Image.open("scope.png")))

# style = ttk.Style()
# style.configure("TEntry", background="#7AC5CD")

# Creating frames inside main window
tracer = ttk.Frame(root, padding=3)
indicators = ttk.Frame(root, padding=10) #, style="TEntry")
selectors = ttk.Frame(root, padding=3)
tracer.grid(column=0, row=0)
indicators.grid(column=1, row=0, sticky=N)
selectors.grid(column=0, row=1, sticky=W)

# Create a figure and axis
fig, ax = plt.subplots()
ax.set_xlim(-5, 5)
ax.set_ylim(-5, 5)
# ax.set_xlim(x_lim_min, x_lim_max)
# ax.set_ylim(y_lim_min, y_lim_max)
ax.set_xticklabels([])
ax.set_yticklabels([])
line, = ax.plot([], [], lw=1)  # Empty plot to update

# The signal
canvas = FigureCanvasTkAgg(fig, master=tracer)
canvas.get_tk_widget().pack()

ani = FuncAnimation(fig, update, frames=100, init_func=init, blit=True, interval=0.01)
plt.title('V-I Trace')
plt.grid()
plt.yticks([n for n in range(-5, 5)])
plt.xticks([n for n in range(-5, 5)])

frequency = StringVar()
voltage = StringVar()
impedance = StringVar()

# Selectors framing
# Frequency selection
ttk.Label(selectors, text="Frequencies: ").grid(column=0, row=0)
ttk.Radiobutton(selectors, text="5Hz", variable=frequency, value="5Hz", command=show_frequency).grid(column=1, row=0)
ttk.Radiobutton(selectors, text="20Hz", variable=frequency, value="20Hz", command=show_frequency).grid(column=2, row=0)
ttk.Radiobutton(selectors, text="50Hz", variable=frequency, value="50Hz", command=show_frequency).grid(column=3, row=0)
ttk.Radiobutton(selectors, text="60Hz", variable=frequency, value="60Hz", command=show_frequency).grid(column=4, row=0)
ttk.Radiobutton(selectors, text="200Hz", variable=frequency, value="200Hz", command=show_frequency).grid(column=5, row=0)
ttk.Radiobutton(selectors, text="500Hz", variable=frequency, value="500Hz", command=show_frequency).grid(column=6, row=0)
ttk.Radiobutton(selectors, text="2kHz", variable=frequency, value="2kHz", command=show_frequency).grid(column=7, row=0)
ttk.Radiobutton(selectors, text="5kHz", variable=frequency, value="5kHz", command=show_frequency).grid(column=8, row=0)

# Voltage selection
ttk.Label(selectors, text="Voltages: ").grid(column=0, row=1)
ttk.Radiobutton(selectors, text="200mV", variable=voltage, value="200mV", command=show_voltage).grid(column=1, row=1)
ttk.Radiobutton(selectors, text="3.3V", variable=voltage, value="3.3V", command=show_voltage).grid(column=2, row=1)
ttk.Radiobutton(selectors, text="5V", variable=voltage, value="5V", command=show_voltage).grid(column=3, row=1)
ttk.Radiobutton(selectors, text="12V", variable=voltage, value="12V", command=show_voltage).grid(column=4, row=1)

# Impedance selection
ttk.Label(selectors, text="Impedance: ").grid(column=0, row=2)
ttk.Radiobutton(selectors, text="45R", variable=impedance, value="45R", command=show_impedance).grid(column=1, row=2)
ttk.Radiobutton(selectors, text="415R", variable=impedance, value="415R", command=show_impedance).grid(column=2, row=2)
ttk.Radiobutton(selectors, text="726R", variable=impedance, value="726R", command=show_impedance).grid(column=3, row=2)
ttk.Radiobutton(selectors, text="1.5kR", variable=impedance, value="1.5kR", command=show_impedance).grid(column=4, row=2)

# Capture button
ttk.Button(selectors, text="Capture trace", command=capture_trace).grid(column=10, row=1, padx=1, sticky=E)

# Indicators framing
ttk.Label(indicators, text="Frequency:").grid(column=0, row=0, padx=1, sticky=NW)
ttk.Label(indicators, textvariable=frequency).grid(column=0, row=1, padx=1, sticky=W)
ttk.Label(indicators, text="Voltage:").grid(column=0, row=2, padx=1, sticky=NW)
ttk.Label(indicators, textvariable=voltage).grid(column=0, row=3, padx=1, sticky=W)
ttk.Label(indicators, text="Impedance:").grid(column=0, row=4, padx=1, sticky=NW)
ttk.Label(indicators, textvariable=impedance).grid(column=0, row=5, padx=1, sticky=W)
ttk.Button(indicators, text="Show captures", command=open_captures).grid(column=0, row=6, padx=1, sticky=W)
root.mainloop()
