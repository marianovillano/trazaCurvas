import time
import tkinter
from tkinter import *
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PyHT6022.LibUsbScope import Oscilloscope
import sys
import os
import serial
import serial.tools.list_ports
from threading import Thread

from modules.functions_trazacurvas import Functions

class VITracerGUI(Functions):
    """Main class to construct all the application, the input parameter is the tkinter root object previously
    created. The class calls the methods automatically and is not intended to run methods separately"""
    def __init__(self, the_root):
        Functions.__init__(self)
        self.check = None
        self.canvas = None
        self.connect_button = None
        self.baud_combobox = None
        self.port_combobox = None
        self.setup_uart = None
        self.fig = None
        self.thread_animation = None
        self.calibration = None
        self.scope = None
        self.decoded_answer = None
        self.thread_uart = None
        self.line = None
        self.ani = None
        self.uart = None
        self.use_scope = BooleanVar(value=False)
        self.y_signal_past = []
        self.x_signal_past = []
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
        # self.window_size = 9 # TODO: check that it could be an old attribute not used anymore
        self.frequency = StringVar()
        self.frequency.set("5Hz")
        self.voltage = StringVar()
        self.voltage.set("200mV")
        self.impedance = StringVar()
        self.impedance.set("45R")
        self.connection_active = False
        self.monitoring_serial = False
        self.received_command = None
        self.scope_is_run = False
        self.scope_thread = None

        # Creating frames inside main window
        self.tracer = ttk.Frame(self.the_root, padding=3)
        self.indicators = ttk.Frame(self.the_root, padding=3)
        self.selectors = ttk.Frame(self.the_root, padding=3)
        self.serial_communication = ttk.Frame(self.the_root, padding=3)
        self.tracer.grid(column=0, row=0, rowspan=2, sticky=W)
        self.indicators.grid(column=1, row=0, sticky=N, rowspan=2)
        self.selectors.grid(column=0, row=2, sticky=W)
        self.serial_communication.grid(column=0, row=3, sticky=W)

        # Calling the methods that creates the needed widgets that conforms the app
        self.populate_menu()
        self.populate_controls()
        self.populate_indicators()
        self.populate_plotter()

    def populate_menu(self):
        # Menu structure of the app
        menubar = Menu(root)
        self.the_root['menu'] = menubar
        menu_ic_profile = Menu(menubar)
        menu_device = Menu(menubar)
        menu_about = Menu(menubar)
        menubar.add_cascade(menu=menu_ic_profile, label='IC Profile')
        menubar.add_cascade(menu=menu_device, label='Device')
        menubar.add_cascade(menu=menu_about, label='About')

        # Menu IC Profile
        menu_ic_profile.add_command(label='Capture IC traces', command=self.make_profile)
        menu_ic_profile.add_command(label='Open pin comparisons', command=self.compare_tracing)
        menu_ic_profile.add_separator()
        menu_ic_profile.add_command(label='Close IC traces/comparisons', command=self.close_profile)

        # Menu device
        menu_device.add_command(label='Connect...', command=self.connecting_window)
        menu_device.add_command(label='Disconnect', command=self.disconnecting_device)

        # Menu About
        menu_about.add_command(label='About the program', command=lambda: self.about_window())

    def populate_controls(self):
        # Frequency buttons selection
        ttk.Label(self.selectors, text="Frequencies: ", style="TLabel").grid(column=0, row=0)
        ttk.Radiobutton(self.selectors, text="5Hz", variable=self.frequency, value="5Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart, self.scope)).grid(column=1, row=0)
        ttk.Radiobutton(self.selectors, text="20Hz", variable=self.frequency, value="20Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart, self.scope)).grid(column=2, row=0)
        ttk.Radiobutton(self.selectors, text="50Hz", variable=self.frequency, value="50Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart, self.scope)).grid(column=3, row=0)
        ttk.Radiobutton(self.selectors, text="60Hz", variable=self.frequency, value="60Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart, self.scope)).grid(column=4, row=0)
        ttk.Radiobutton(self.selectors, text="200Hz", variable=self.frequency, value="200Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart, self.scope)).grid(column=5, row=0)
        ttk.Radiobutton(self.selectors, text="500Hz", variable=self.frequency, value="500Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart, self.scope)).grid(column=6, row=0)
        ttk.Radiobutton(self.selectors, text="2kHz", variable=self.frequency, value="2kHz",
                        command=lambda: self.show_frequency(self.frequency, self.uart, self.scope)).grid(column=7, row=0)
        ttk.Radiobutton(self.selectors, text="5kHz", variable=self.frequency, value="5kHz",
                        command=lambda: self.show_frequency(self.frequency, self.uart, self.scope)).grid(column=8, row=0)

        # Voltage buttons selection
        ttk.Label(self.selectors, text="Voltages: ").grid(column=0, row=1)
        ttk.Radiobutton(self.selectors, text="200mV", variable=self.voltage, value="200mV",
                        command=lambda: self.show_voltage(self.voltage, self.uart, self.scope)).grid(column=1, row=1)
        ttk.Radiobutton(self.selectors, text="3.3V", variable=self.voltage, value="3.3V",
                        command=lambda: self.show_voltage(self.voltage, self.uart, self.scope)).grid(column=2, row=1)
        ttk.Radiobutton(self.selectors, text="5V", variable=self.voltage, value="5V",
                        command=lambda: self.show_voltage(self.voltage, self.uart, self.scope)).grid(column=3, row=1)
        ttk.Radiobutton(self.selectors, text="9V", variable=self.voltage, value="9V",
                        command=lambda: self.show_voltage(self.voltage, self.uart, self.scope)).grid(column=4, row=1)

        # Impedance buttons selection
        ttk.Label(self.selectors, text="Impedance: ").grid(column=0, row=2)
        ttk.Radiobutton(self.selectors, text="45R", variable=self.impedance, value="45R",
                        command=lambda: self.show_impedance(self.impedance, self.uart)).grid(column=1, row=2)
        ttk.Radiobutton(self.selectors, text="415R", variable=self.impedance, value="415R",
                        command=lambda: self.show_impedance(self.impedance, self.uart)).grid(column=2, row=2)
        ttk.Radiobutton(self.selectors, text="726R", variable=self.impedance, value="726R",
                        command=lambda: self.show_impedance(self.impedance, self.uart)).grid(column=3, row=2)
        ttk.Radiobutton(self.selectors, text="1.5kR", variable=self.impedance, value="1.5kR",
                        command=lambda: self.show_impedance(self.impedance, self.uart)).grid(column=4, row=2)

    def populate_indicators(self):
        # Creating the indicator elements to show the selected frequency, voltage and impedance
        font_size = 20
        ttk.Label(self.indicators, text="Frequency").grid(column=0, row=0, padx=1)
        ttk.Label(self.indicators, textvariable=self.frequency, font=("", font_size), foreground="green").grid(column=0, row=1, padx=1)
        ttk.Label(self.indicators, text="Voltage").grid(column=0, row=2, padx=1)
        ttk.Label(self.indicators, textvariable=self.voltage, font=("", font_size), foreground="blue").grid(column=0, row=3, padx=1)
        ttk.Label(self.indicators, text="Impedance").grid(column=0, row=4, padx=1)
        ttk.Label(self.indicators, textvariable=self.impedance, font=("", font_size), foreground="red").grid(column=0, row=5, padx=1)

        # Creating the capture button
        ttk.Button(self.indicators, text="Capture trace",
                   command=lambda: self.capture_trace(plt)).grid(column=0, row=6, padx=1, sticky=W)

        # Creating the event monitoring
        ttk.Label(self.serial_communication, text="Events monitor:").grid(column=0, row=0, padx=1, sticky=W)
        self.log = Text(self.serial_communication, state="disabled", width=70, height=5, wrap="word", bg="light gray")
        self.log.grid(column=0, row=1, padx=5, pady=5, sticky=W)

    def about_window(self):
        """The typical about window..."""
        about = Toplevel(self.the_root)
        about.transient(self.the_root)
        about.grab_set()
        about.focus_set()
        about.resizable(False, False)
        about.title("About...")
        about.geometry("200x100")
        about.tk.call('wm', 'iconphoto', about._w, self.icon)
        about.rowconfigure(0, weight=1)
        about.columnconfigure(0, weight=1)
        Label(about, text="Mi programita version 0.9", pady=20).grid(column=0, row=0)
        ttk.Button(about, text="OK", command=about.destroy).grid(column=0, row=2, pady=8, padx=8, sticky=E)

# --------------------------------------------------------------------------------------------------------------------

    def starting_scope(self):
        """Method that configures and starts a thread to handle the data capture of the Hantek oscilloscope"""
        self.scope = Oscilloscope()
        self.scope.setup()
        if self.scope.open_handle():
            # Upload the firmware into device's RAM
            if not self.scope.is_device_firmware_present:
                self.scope.flash_firmware()

            # Read calibration values from EEPROM. TODO: Make a calibration process
            self.calibration = self.scope.get_calibration_values()

            # Set the scope interface: 0 = BULK, >0 = ISO, 1=3072,2=2048,3=1024 bytes per 125 us
            self.scope.set_interface(0)  # Use BULK unless you have specific need for ISO xfer
            self.scope.set_num_channels(2)
            self.scope.set_sample_rate(102)

            # Set the gain for CH1 and CH2: the value is a divisor of the default 5V voltage
            self.scope.set_ch1_voltage_range(10)    # V channel
            self.scope.set_ch2_voltage_range(10)    # I channel

            # Initializing the thread to measure data
            self.scope_is_run = True
            self.scope_thread = Thread(target=self.get_data)
            self.scope_thread.start()
        else:
            self.write_to_log("Oscilloscope not detected")

    def get_data(self):
        """Method that captures and sends two lists representing the two channels of the Hantek oscilloscope"""
        while self.scope_is_run:
            self.scope.start_capture()     # API method to start the data capture
            adc_signals = self.scope.read_data(data_size=0xC00, raw=False) # The scope returns a list of two lists (V/I)
            # Separating the lists in two buffers, V and I, and determinate its sizes
            self.buffer_size_x = len(adc_signals[0])
            self.buffer_size_y = len(adc_signals[1])
            # transforming the collected data in float values
            self.x_signal = self.scope.scale_read_data(adc_signals[0])
            self.y_signal = self.scope.scale_read_data(adc_signals[1])
            # Recovery buffers to allow the program still capturing when a USB communication problem is happened, due
            # to capturing data smaller than the data size 0xC00 (3072)
            if len(self.x_signal) == 3072:
                self.x_signal_past = self.x_signal
            if len(self.y_signal) == 3072:
                self.y_signal_past = self.y_signal

    def init(self):
        """Initialization  of the animated plot function"""
        self.line.set_data([], [])
        return self.line,

    def update(self, frame):
        """Method called to show a frame in the animated plot"""
        plot_x_signal = []
        plot_y_signal = []
        try:
            # Assigning in the axis graphics the data to show: x represents voltage and y represents current
            plot_x_signal = [self.x_signal[frame] for frame in range(self.buffer_size_x)]
            plot_y_signal = [self.y_signal[frame] for frame in range(self.buffer_size_y)]

            self.line.set_data(plot_x_signal, plot_y_signal)  # Update the plot with the new data
            return self.line,
        # Sometimes, the buffer couldn't be captured with the correct size, then the IndexError exception is captured
        except IndexError as e:
            self.write_to_log(repr(e))
            # Plotting the recovery buffers to allow the program still running
            if len(self.x_signal_past) == 3072:
                plot_x_signal = [self.x_signal_past[frame] for frame in range(self.buffer_size_x)]
            if len(self.y_signal_past) == 3072:
                plot_y_signal = [self.y_signal_past[frame] for frame in range(self.buffer_size_y)]

            self.line.set_data(plot_x_signal, plot_y_signal)  # Update the plot with the new data
            return self.line,

    def populate_plotter(self):
        """Method to populate the frame representing the animated plotter"""
        # Create a figure and the axis
        self.fig, ax = plt.subplots(figsize=(5, 4))
        ax.set_xlim(-5, 5)
        ax.set_ylim(-5, 5)
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        self.line, = ax.plot([], [], lw=1)  # Empty plot to update
        self.fig.tight_layout(pad=0)
        ax.set_position((0.05, 0.05, 0.92, 0.92))
        # The signal to plot
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tracer)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def animate_plot(self):
        # Create animation
        self.ani = FuncAnimation(self.fig, self.update, frames=100, init_func=self.init, blit=True, interval=0.01)
        plt.grid()
        # Creating lines representing the maximum and minimum captured voltages that represents V and I +/- 5V
        plt.yticks([n for n in range(-5, 5)])
        plt.xticks([n for n in range(-5, 5)])

    def connecting_window(self):
        """Method called from the menu to open a window with the data needed to start the uart communication with the
        curve tracer and USB communication with the oscilloscope"""
        self.setup_uart = Toplevel(self.the_root)
        self.setup_uart.resizable(False, False)
        self.setup_uart.transient(self.the_root)
        self.setup_uart.grab_set()
        self.setup_uart.focus_set()
        self.setup_uart.title("Configure serial communication")
        self.icon = PhotoImage(file='scope.gif')
        self.setup_uart.tk.call('wm', 'iconphoto', self.setup_uart._w, self.icon)
        ttk.Label(self.setup_uart, text="Select Port:").grid(row=0, column=0, padx=40, pady=30, sticky=W)
        # Look for the connected uart ports in the system and creating a widget list of them
        # TODO: Can be filtered by serial number of the USB/UART conversor and show only the curve tracer port
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if len(ports) == 0:
            ports = "______NO_PORTS______"
        self.port_combobox = ttk.Combobox(self.setup_uart, values=ports, state="readonly")
        self.port_combobox.bind("<Button-1>", self.callback)
        self.port_combobox.grid(row=0, column=1, padx=5, pady=30)
        self.port_combobox.set(ports)
        # Widget list of port speed options
        ttk.Label(self.setup_uart, text="Select Baud Rate:").grid(row=1, column=0, padx=40, pady=3, sticky=W)
        self.baud_combobox = ttk.Combobox(self.setup_uart, values=["2400", "4800", "9600", "14400", "19200",
                                                                   "57600", "115200"], state="readonly")
        # Set the default speed
        self.baud_combobox.set("9600")
        self.baud_combobox.grid(row=1, column=1, padx=5, pady=3)

        # Option to connect and capture oscilloscope data, activated by default
        self.use_scope.set(True)
        self.check = ttk.Checkbutton(self.setup_uart, text="Connect Scope", variable=self.use_scope,
                                     offvalue=False, onvalue=True)
        self.check.grid(row=2, column=1, padx=5, pady=5)

        # Widget button to call the curve tracer connection method, disabled if there's no detected comports
        self.connect_button = ttk.Button(self.setup_uart, text="Connect", command= lambda: self.connecting_device())
        if ports == "______NO_PORTS______":
            self.connect_button.config(state=tkinter.DISABLED)
        self.connect_button.grid(row=4, column=1, padx=90, pady=30)

    def callback(self, event):
        """Internal method to repopulate the comport list if any is connected after the connection window is opened,
        also enables the connection widget button"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if len(ports) > 0:
            self.port_combobox.set(ports)
            self.port_combobox["values"] = ports
            self.connect_button.config(state=tkinter.NORMAL)

    def connecting_device(self):
        """Method to establish the connection with the curve tracer, gets port and speed data from the connection
        window and starts the connection, and the capturing signals from the oscilloscope if configured (default yes)
        """
        port = self.port_combobox.get()
        baud = int(self.baud_combobox.get())
        try:
            self.uart = serial.Serial(port, baudrate=baud, timeout=0.1, write_timeout=0.1)
            self.connection_active = True
            # The uart rx is received in a method opened in a different thread
            self.thread_uart = Thread(target=self.read_from_port)
            self.thread_uart.daemon = True
            self.thread_uart.start()
            self.monitoring_serial = True
            self.send_command("hello", self.uart) # The command to start the connection in the remote
            self.populate_plotter()
        except Exception as e:
            self.write_to_log(repr(e))
        time.sleep(1)
        # If the oscilloscope is wanted to be activated, starts the capture
        if self.use_scope.get():
            self.starting_scope()
            if self.scope_is_run:
                # Once the oscilloscope capturing process is running, the plotting is initialized in a new thread
                self.populate_plotter()
                self.thread_animation = Thread(target=self.animate_plot())
                self.thread_animation.start()
        time.sleep(0.5)
        # Closes the communication window
        self.setup_uart.destroy()

    def disconnecting_device(self):
        """Method called in the menu to disconnect the remote and stop the capturing data and signal plotting"""
        if self.uart is not None:
            self.send_command("bye", self.uart)     # Command to disconnect the remote
            time.sleep(0.1)
            self.connection_active = False
            self.uart.close()
            time.sleep(0.1)
        else:
            self.write_to_log("Nothing to disconnect")
        # Process to stopping the oscilloscope capture and the plotting process
        if self.scope is not None:
            self.scope_is_run = False
            if self.use_scope.get():
                self.scope.stop_capture()
                time.sleep(0.5)
                self.scope.close_handle()
            self.thread_animation.join()

    def read_from_port(self):
        """Method to monitor the receiving data in the uart connection, is run constantly in an independent thread
        Here, it will receive the confirmation commands of the remote to change the parameter in the oscilloscope"""
        while self.connection_active:  # Check the flag in the reading loop
            try:
                if self.uart.inWaiting() > 0:
                    answer = self.uart.read_until()
                    self.decoded_answer = answer.decode("utf-8").replace("\r\n", "")
                    self.received_command = True
                    # Depending on the first letter of the confirmation command received, it will determine the process
                    if self.decoded_answer[0] == "F":
                        self.frequency.set(self.frequency_dict[self.decoded_answer])
                        if self.use_scope.get():
                            # Changing the convenient sampling data in the oscilloscope
                            if self.frequency.get() == "5Hz":
                                self.scope.set_sample_rate(102)
                            elif self.frequency.get() == "20Hz":
                                self.scope.set_sample_rate(106)
                            elif self.frequency.get() == "50Hz" or self.frequency.get() == "60Hz":
                                self.scope.set_sample_rate(110)
                            elif self.frequency.get() == "200Hz":
                                self.scope.set_sample_rate(150)
                            else:
                                self.scope.set_sample_rate(1)
                    elif self.decoded_answer[0] == "V":
                        self.voltage.set(self.voltage_dict[self.decoded_answer])
                        # Changing the convenient vertical range (voltage) data in the oscilloscope
                        if self.use_scope.get():
                            if self.voltage.get() == "200mV":
                                self.scope.set_ch1_voltage_range(10)
                                self.scope.set_ch2_voltage_range(10)
                            else:
                                self.scope.set_ch1_voltage_range(1)
                                self.scope.set_ch2_voltage_range(1)
                    elif self.decoded_answer[0] == "R":
                        # Receiving confirmation impedance command of the remote
                        self.impedance.set(self.impedance_dict[self.decoded_answer])
                    elif self.decoded_answer[0] == "c":
                        # Receiving confirmation capture button pressed command in the remote
                        self.capture_trace(plt)
                    self.write_to_log("Receiving: " + self.decoded_answer)
                    self.received_command = False
            except Exception as e:
                self.write_to_log(repr(e))
                break

    def on_closing(self):
        """Method called if the close [X] icon in the main window is pressed, it sends the disconnecting command to the
        remote and stops all the capturing and plotting processes if they are opened"""
        if self.uart is not None:
            self.send_command("bye", self.uart)
            time.sleep(0.1)
            self.connection_active = False
            self.uart.close()
            time.sleep(0.1)
        if self.use_scope.get():
            if self.scope_is_run:
                self.scope_is_run = False
                time.sleep(0.1)
                self.scope.stop_capture()
                time.sleep(0.5)
                self.scope.close_handle()
                self.thread_animation.join()
                self.scope_thread.join()
        self.the_root.quit()
        self.the_root.destroy()
        sys.exit()


if __name__ == "__main__":
    # Creating main window
    if sys.platform == "linux":
        os.system("clear")
    elif sys.platform == "windows":
        os.system("cls")
    print("Starting program...")
    root = Tk()
    app = VITracerGUI(root)

    root.mainloop()
