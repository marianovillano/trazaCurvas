import time
from tkinter import *
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PyHT6022.LibUsbScope import Oscilloscope
import sys
import os
import serial
from threading import Thread
from modules.functions_trazacurvas import (show_frequency, show_voltage, show_impedance, capture_trace,
                                           creating_pins, open_profile, close_profile, send_command, frequency_dict,
                                           voltage_dict, impedance_dict)

class VITracerGUI:

    def __init__(self, the_root):
        self.fig = None
        self.thread_animation = None
        self.calibration = None
        self.scope = None
        self.decoded_answer = None
        self.thread_uart = None
        self.line = None
        self.ani = None
        self.uart = None
        self.x_signal = []
        self.y_signal = []
        self.buffer_size_x = 3072
        self.buffer_size_y = 3072
        self.the_root = the_root
        self.the_root.option_add('*tearOff', FALSE)
        self.the_root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.the_root.rowconfigure(0, weight=1)
        self.the_root.columnconfigure(0, weight=1)
        self.the_root.title("V-I curve tracer")
        self.icon = PhotoImage(file='scope.gif')
        self.the_root.tk.call('wm', 'iconphoto', self.the_root._w, self.icon)
        self.window_size = 9
        self.frequency = StringVar()
        self.frequency.set("5Hz")
        self.voltage = StringVar()
        self.voltage.set("200mV")
        self.impedance = StringVar()
        self.impedance.set("45R")
        self.serial_monitor = StringVar()
        self.connection_active = False
        self.monitoring_serial = False
        self.scope_is_run = False

        # Creating frames inside main window
        self.tracer = ttk.Frame(root, padding=3)
        self.indicators = ttk.Frame(root, padding=10)  # , style="TEntry")
        self.selectors = ttk.Frame(root, padding=3)
        self.serial_communication = ttk.Frame(root, padding=3)
        self.tracer.grid(column=0, row=0)
        self.indicators.grid(column=1, row=0, sticky=N)
        self.selectors.grid(column=0, row=1, sticky=W)
        self.serial_communication.grid(column=0, row=2, sticky=W)

        self.moved_button = "moved.TRadiobutton"
        self.selected_button = "selected.TRadiobutton"
        self.unselected_button = "unselected.TRadiobutton"
        buttons_style = ttk.Style()
        buttons_style.configure("moved.TRadiobutton", foreground="blue")
        buttons_style.configure("selected.TRadiobutton", foreground="green")
        buttons_style.configure("unselected.TRadiobutton", foreground="black")

        self.create_menu()
        self.create_controls()
        self.create_plotter()
        # self.starting_scope()
        # testing commit
        # self.animate_plot()

    def create_menu(self):
        # Menu structure
        menubar = Menu(root)
        self.the_root['menu'] = menubar
        menu_ic_profile = Menu(menubar)
        menu_device = Menu(menubar)
        menu_edit = Menu(menubar)
        menu_about = Menu(menubar)
        menubar.add_cascade(menu=menu_ic_profile, label='IC Profile')
        menubar.add_cascade(menu=menu_device, label='Device')
        menubar.add_cascade(menu=menu_edit, label='Edit')
        menubar.add_cascade(menu=menu_about, label='About')

        # Menu IC Profile
        menu_ic_profile.add_command(label='New profile', command=lambda: self.new_profile_window())
        menu_ic_profile.add_separator()
        menu_ic_profile.add_command(label='Open profile...', command=open_profile)
        menu_ic_profile.add_command(label='Close profile', command=close_profile)

        # Menu device
        menu_device.add_command(label='Connect...', command=self.connecting_device)
        menu_device.add_command(label='Disconnect', command=self.disconnecting_device)
        menu_device.add_separator()
        menu_device.add_command(label='Setup', command=lambda: self.setup_communication_window())

        # Menu About
        menu_about.add_command(label='About the program', command=lambda: self.about_window())

    def create_controls(self):
        # Selectors framing
        # Frequency selection
        ttk.Label(self.selectors, text="Frequencies: ", style="TLabel").grid(column=0, row=0)
        ttk.Radiobutton(self.selectors, text="5Hz", variable=self.frequency, value="5Hz",
                        command=lambda: show_frequency(self.frequency, self.serial_monitor, self.uart,
                                                       self.scope)).grid(column=1, row=0)
        ttk.Radiobutton(self.selectors, text="20Hz", variable=self.frequency, value="20Hz",
                        command=lambda: show_frequency(self.frequency, self.serial_monitor, self.uart,
                                                       self.scope)).grid(column=2, row=0)
        ttk.Radiobutton(self.selectors, text="50Hz", variable=self.frequency, value="50Hz",
                        command=lambda: show_frequency(self.frequency, self.serial_monitor, self.uart,
                                                       self.scope)).grid(column=3, row=0)
        ttk.Radiobutton(self.selectors, text="60Hz", variable=self.frequency, value="60Hz",
                        command=lambda: show_frequency(self.frequency, self.serial_monitor, self.uart,
                                                       self.scope)).grid(column=4, row=0)
        ttk.Radiobutton(self.selectors, text="200Hz", variable=self.frequency, value="200Hz",
                        command=lambda: show_frequency(self.frequency, self.serial_monitor, self.uart,
                                                       self.scope)).grid(column=5, row=0)
        ttk.Radiobutton(self.selectors, text="500Hz", variable=self.frequency, value="500Hz",
                        command=lambda: show_frequency(self.frequency, self.serial_monitor, self.uart,
                                                       self.scope)).grid(column=6, row=0)
        ttk.Radiobutton(self.selectors, text="2kHz", variable=self.frequency, value="2kHz",
                        command=lambda: show_frequency(self.frequency, self.serial_monitor, self.uart,
                                                       self.scope)).grid(column=7, row=0)
        ttk.Radiobutton(self.selectors, text="5kHz", variable=self.frequency, value="5kHz",
                        command=lambda: show_frequency(self.frequency, self.serial_monitor, self.uart,
                                                       self.scope)).grid(column=8, row=0)

        # Voltage selection
        ttk.Label(self.selectors, text="Voltages: ").grid(column=0, row=1)
        ttk.Radiobutton(self.selectors, text="200mV", variable=self.voltage, value="200mV",
                        command=lambda: show_voltage(self.voltage, self.serial_monitor,
                                                     self.uart, self.scope)).grid(column=1, row=1)
        ttk.Radiobutton(self.selectors, text="3.3V", variable=self.voltage, value="3.3V",
                        command=lambda: show_voltage(self.voltage, self.serial_monitor,
                                                     self.uart, self.scope)).grid(column=2, row=1)
        ttk.Radiobutton(self.selectors, text="5V", variable=self.voltage, value="5V",
                        command=lambda: show_voltage(self.voltage, self.serial_monitor,
                                                     self.uart, self.scope)).grid(column=3, row=1)
        ttk.Radiobutton(self.selectors, text="9V", variable=self.voltage, value="9V",
                        command=lambda: show_voltage(self.voltage, self.serial_monitor,
                                                     self.uart, self.scope)).grid(column=4, row=1)

        # Impedance selection
        ttk.Label(self.selectors, text="Impedance: ").grid(column=0, row=2)
        ttk.Radiobutton(self.selectors, text="45R", variable=self.impedance, value="45R",
                        command=lambda: show_impedance(self.impedance, self.serial_monitor,
                                                       self.uart)).grid(column=1, row=2)
        ttk.Radiobutton(self.selectors, text="415R", variable=self.impedance, value="415R",
                        command=lambda: show_impedance(self.impedance, self.serial_monitor,
                                                       self.uart)).grid(column=2, row=2)
        ttk.Radiobutton(self.selectors, text="726R", variable=self.impedance, value="726R",
                        command=lambda: show_impedance(self.impedance, self.serial_monitor,
                                                       self.uart)).grid(column=3, row=2)
        ttk.Radiobutton(self.selectors, text="1.5kR", variable=self.impedance, value="1.5kR",
                        command=lambda: show_impedance(self.impedance, self.serial_monitor,
                                                       self.uart)).grid(column=4, row=2)

        # Capture button
        bt_capture = (ttk.Button(self.selectors, text="Capture trace",
                   command=lambda: capture_trace(plt)))
        bt_capture.grid(column=10, row=1, padx=1, sticky=E)
        bt_capture.focus_set()

        # Indicators framing
        ttk.Label(self.indicators, text="Frequency:").grid(column=0, row=0, padx=1, sticky=NW)
        ttk.Label(self.indicators, textvariable=self.frequency).grid(column=0, row=1, padx=1, sticky=W)
        ttk.Label(self.indicators, text="Voltage:").grid(column=0, row=2, padx=1, sticky=NW)
        ttk.Label(self.indicators, textvariable=self.voltage).grid(column=0, row=3, padx=1, sticky=W)
        ttk.Label(self.indicators, text="Impedance:").grid(column=0, row=4, padx=1, sticky=NW)
        ttk.Label(self.indicators, textvariable=self.impedance).grid(column=0, row=5, padx=1, sticky=W)
        ttk.Button(self.indicators, text="Show captures",
                   command=lambda: self.open_captures()).grid(column=0, row=6, padx=1, sticky=W)

        # Serial monitoring
        ttk.Label(self.serial_communication,
                  text="Monitoring serial:").grid(column=0, row=0, padx=1, sticky=W)
        ttk.Label(self.serial_communication, width=75, font=("Arial", 10),
                  textvariable=self.serial_monitor, background="white").grid(column=1, row=0, padx=1, sticky=W)

    def new_profile_window(self):
        new_profile = Toplevel(self.the_root)
        new_profile.resizable(False, False)
        new_profile.title("New board profile")
        new_profile.geometry("800x600")
        new_profile.tk.call('wm', 'iconphoto', new_profile._w, self.icon)
        # about.rowconfigure(0, weight=1)
        # about.columnconfigure(0, weight=1)
        equipment = StringVar()
        board = StringVar()
        id_board = StringVar()
        ic_name = StringVar()
        datasheet = StringVar()
        number_pins = IntVar()
        ttk.Label(new_profile, text="Equipment: ").grid(column=0, row=0, pady=2, padx=2, sticky=E)
        ttk.Entry(new_profile, width=30, textvariable=equipment).grid(column=1, row=0, pady=2, padx=2)
        ttk.Label(new_profile, text="Board: ").grid(column=2, row=0, pady=2, padx=2, sticky=W)
        ttk.Entry(new_profile, width=30, textvariable=board).grid(column=3, row=0, pady=2, padx=2)
        ttk.Label(new_profile, text="Integrated circuits: ").grid(column=0, row=1, pady=20, padx=2)

        ttk.Label(new_profile, text="ID in board (U...): ").grid(column=0, row=2, pady=2, padx=2, sticky=W)
        ttk.Entry(new_profile, width=30, textvariable=id_board).grid(column=1, row=2, pady=2, padx=2)
        ttk.Label(new_profile, text="IC part ").grid(column=0, row=3, pady=2, padx=2, sticky=W)
        ttk.Entry(new_profile, width=30, textvariable=ic_name).grid(column=1, row=3, pady=2, padx=2)
        ttk.Label(new_profile, text="Datasheet: ").grid(column=0, row=4, pady=2, padx=2, sticky=W)
        ttk.Entry(new_profile, width=30, textvariable=datasheet).grid(column=1, row=4, pady=2, padx=2)
        ttk.Label(new_profile, text="Number of pins: ").grid(column=0, row=5, pady=2, padx=2, sticky=W)
        ttk.Entry(new_profile, width=10, textvariable=number_pins).grid(column=1, row=5, pady=2, padx=2, sticky=W)
        ttk.Button(new_profile, text="Add...", command=lambda: creating_pins()).grid(column=2, row=5, pady=8,
                                                                                    padx=8, sticky=W)
        ttk.Button(new_profile, text="OK", command=new_profile.destroy).grid(column=3, row=10, pady=8, padx=8, sticky=E)

    def about_window(self):
        about = Toplevel(self.the_root)
        about.resizable(False, False)
        about.title("About this program")
        about.geometry("500x100")
        about.tk.call('wm', 'iconphoto', about._w, self.icon)
        about.rowconfigure(0, weight=1)
        about.columnconfigure(0, weight=1)
        Label(about, text="Mi programita version 0.1", pady=20).grid(column=0, row=0)
        ttk.Button(about, text="OK", command=about.destroy).grid(column=0, row=2, pady=8, padx=8, sticky=E)

    def setup_communication_window(self):
        setup_uart = Toplevel(self.the_root)
        setup_uart.resizable(False, False)
        setup_uart.title("Configure serial communication")
        setup_uart.geometry("500x300")
        setup_uart.tk.call('wm', 'iconphoto', setup_uart._w, self.icon)
        setup_uart.rowconfigure(0, weight=1)
        setup_uart.columnconfigure(0, weight=1)

    def open_captures(self):
        captures_window = Toplevel(self.the_root)
        captures_window.title("V-I traces captured")
        # captures_window.geometry("800x600")
        #captures_window.iconbitmap("scope.ico")
        figs = ttk.Frame(captures_window, padding=3)
        try:
            photo = PhotoImage(file=(os.path.abspath("image.png")), master=captures_window)
            photo2 = PhotoImage(file=(os.path.abspath("image2.png")), master=captures_window)
            image = Label(captures_window, image=photo)
            image.grid(column=0, row=0)
            image2 = Label(captures_window, image=photo2)
            image2.grid(column=1, row=0)
            captures_window.photo = photo
            captures_window.photo2 = photo2
        except Exception as e:
            print(f"Error loading image: {e}")

# --------------------------------------------------------------------------------------------------------------------

    def starting_scope(self):
        self.scope_is_run = True
        self.scope = Oscilloscope()
        self.scope.setup()
        if not self.scope.open_handle():
            print("oscilloscope not detected")
            sys.exit(-1)

        # upload correct firmware into device's RAM
        if not self.scope.is_device_firmware_present:
            self.scope.flash_firmware()

        # read calibration values from EEPROM
        self.calibration = self.scope.get_calibration_values()

        # set interface: 0 = BULK, >0 = ISO, 1=3072,2=2048,3=1024 bytes per 125 us
        self.scope.set_interface(0)  # use BULK unless you have specific need for ISO xfer
        self.scope.set_num_channels(2)
        self.scope.set_sample_rate(102)

        # set the gain for CH1 and CH2
        self.scope.set_ch1_voltage_range(10)
        self.scope.set_ch2_voltage_range(10)
        scope_thread = Thread(target=self.get_data)
        scope_thread.daemon = True
        scope_thread.start()

    def get_data(self):
        while self.scope_is_run:
            self.scope.start_capture()
            adc_signals = self.scope.read_data(data_size=0xC00, raw=False)
            self.buffer_size_x = len(adc_signals[0])
            self.buffer_size_y = len(adc_signals[1])
            self.x_signal = self.scope.scale_read_data(adc_signals[0])
            self.y_signal = self.scope.scale_read_data(adc_signals[1])

    def init(self):
        self.line.set_data([], [])
        return self.line,

    # Update function: called for each frame
    def update(self, frame):
        # Define the data to plot by taking a slice of the data list
        plot_x_signal = [self.x_signal[frame] for frame in range(self.buffer_size_x)]
        plot_y_signal = [self.y_signal[frame] for frame in range(self.buffer_size_y)]

        self.line.set_data(plot_x_signal, plot_y_signal)  # Update the plot with the new data
        return self.line,

    def create_plotter(self):
        # Create a figure and axis
        self.fig, ax = plt.subplots()
        ax.set_xlim(-5, 5)
        ax.set_ylim(-5, 5)
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        self.line, = ax.plot([], [], lw=1)  # Empty plot to update
        # The signal
        canvas = FigureCanvasTkAgg(self.fig, master=self.tracer)
        canvas.get_tk_widget().pack()

    def animate_plot(self):
        # Create animation
        self.ani = FuncAnimation(self.fig, self.update, frames=100, init_func=self.init, blit=True, interval=0.01)
        plt.title('V-I Trace')
        plt.grid()
        plt.yticks([n for n in range(-5, 5)])
        plt.xticks([n for n in range(-5, 5)])

    def connecting_device(self):
        try:
            self.uart = serial.Serial('/dev/ttyUSB0', timeout=0.1, write_timeout=0.1)
            self.connection_active = True
            self.thread_uart = Thread(target=self.read_from_port)
            self.thread_uart.daemon = True
            self.thread_uart.start()
            self.monitoring_serial = True
            send_command("hello", self.serial_monitor, self.uart)
            self.starting_scope()
            self.thread_animation = Thread(target=self.animate_plot())
            self.thread_animation.daemon = True
            self.thread_animation.start()
        except Exception as e:
            self.serial_monitor.set(repr(e))

    def disconnecting_device(self):
        self.scope_is_run = False
        self.scope.stop_capture()
        time.sleep(0.5)
        self.scope.close_handle()
        if self.uart is not None:
            send_command("bye", self.serial_monitor, self.uart)
            time.sleep(0.1)
            self.connection_active = False
            self.uart.close()
            time.sleep(0.1)

    def read_from_port(self):
        while self.connection_active:  # Check the flag in the reading loop
            try:
                if self.uart.inWaiting()>0:
                    answer = self.uart.read_until()
                    self.decoded_answer = answer.decode("utf-8").replace("\r\n", "")
                    if self.decoded_answer[0] == "F":
                        self.frequency.set(frequency_dict[self.decoded_answer])
                    elif self.decoded_answer[0] == "V":
                        self.voltage.set(voltage_dict[self.decoded_answer])
                    elif self.decoded_answer[0] == "R":
                        self.impedance.set(impedance_dict[self.decoded_answer])
                    self.serial_monitor.set(self.decoded_answer)
            except Exception as e:
                self.serial_monitor.set(repr(e))
                break

    def on_closing(self):
        if self.uart is not None:
            send_command("bye", self.serial_monitor, self.uart)
            time.sleep(0.1)
            self.connection_active = False
            self.uart.close()
            time.sleep(0.1)
        if self.scope_is_run is True:
            self.scope_is_run = False
            time.sleep(0.1)
            self.scope.stop_capture()
            time.sleep(0.5)
            self.scope.close_handle()
        self.the_root.quit()
        self.the_root.destroy()
        sys.exit()


if __name__ == "__main__":
    # Creating main window
    root = Tk()
    app = VITracerGUI(root)
    # style = ttk.Style()
    # style.configure("TEntry", background="#7AC5CD")
    root.mainloop()
