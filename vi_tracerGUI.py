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

    def __init__(self, the_root):
        Functions.__init__(self)
        self.check = None
        self.canvas = None
        self.connect_button = None
        self.baud_combobox = None
        self.port_combox = None
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
        self.window_size = 9
        self.frequency = StringVar()
        self.frequency.set("5Hz")
        self.voltage = StringVar()
        self.voltage.set("200mV")
        self.impedance = StringVar()
        self.impedance.set("45R")
        self.connection_active = False
        self.monitoring_serial = False
        self.scope_is_run = False
        self.received_command = False

        # Creating frames inside main window
        self.tracer = ttk.Frame(self.the_root, padding=3)
        self.indicators = ttk.Frame(self.the_root, padding=3)
        self.selectors = ttk.Frame(self.the_root, padding=3)
        self.serial_communication = ttk.Frame(self.the_root, padding=3)
        self.tracer.grid(column=0, row=0, rowspan=2, sticky=W)
        self.indicators.grid(column=1, row=0, sticky=N, rowspan=2)
        self.selectors.grid(column=0, row=2, sticky=W)
        self.serial_communication.grid(column=0, row=3, sticky=W)

        self.populate_menu()
        self.populate_controls()
        self.populate_indicators()
        self.populate_plotter()

    def populate_menu(self):
        # Menu structure
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
        # Selectors framing
        # Frequency selection
        ttk.Label(self.selectors, text="Frequencies: ", style="TLabel").grid(column=0, row=0)
        ttk.Radiobutton(self.selectors, text="5Hz", variable=self.frequency, value="5Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart,
                                                       self.scope)).grid(column=1, row=0)
        ttk.Radiobutton(self.selectors, text="20Hz", variable=self.frequency, value="20Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart,
                                                       self.scope)).grid(column=2, row=0)
        ttk.Radiobutton(self.selectors, text="50Hz", variable=self.frequency, value="50Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart,
                                                       self.scope)).grid(column=3, row=0)
        ttk.Radiobutton(self.selectors, text="60Hz", variable=self.frequency, value="60Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart,
                                                       self.scope)).grid(column=4, row=0)
        ttk.Radiobutton(self.selectors, text="200Hz", variable=self.frequency, value="200Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart,
                                                       self.scope)).grid(column=5, row=0)
        ttk.Radiobutton(self.selectors, text="500Hz", variable=self.frequency, value="500Hz",
                        command=lambda: self.show_frequency(self.frequency, self.uart,
                                                       self.scope)).grid(column=6, row=0)
        ttk.Radiobutton(self.selectors, text="2kHz", variable=self.frequency, value="2kHz",
                        command=lambda: self.show_frequency(self.frequency, self.uart,
                                                       self.scope)).grid(column=7, row=0)
        ttk.Radiobutton(self.selectors, text="5kHz", variable=self.frequency, value="5kHz",
                        command=lambda: self.show_frequency(self.frequency, self.uart,
                                                       self.scope)).grid(column=8, row=0)

        # Voltage selection
        ttk.Label(self.selectors, text="Voltages: ").grid(column=0, row=1)
        ttk.Radiobutton(self.selectors, text="200mV", variable=self.voltage, value="200mV",
                        command=lambda: self.show_voltage(self.voltage, self.uart, self.scope)).grid(column=1, row=1)
        ttk.Radiobutton(self.selectors, text="3.3V", variable=self.voltage, value="3.3V",
                        command=lambda: self.show_voltage(self.voltage, self.uart, self.scope)).grid(column=2, row=1)
        ttk.Radiobutton(self.selectors, text="5V", variable=self.voltage, value="5V",
                        command=lambda: self.show_voltage(self.voltage, self.uart, self.scope)).grid(column=3, row=1)
        ttk.Radiobutton(self.selectors, text="9V", variable=self.voltage, value="9V",
                        command=lambda: self.show_voltage(self.voltage, self.uart, self.scope)).grid(column=4, row=1)

        # Impedance selection
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
        # Indicators framing
        font_size = 20
        ttk.Label(self.indicators, text="Frequency").grid(column=0, row=0, padx=1)
        ttk.Label(self.indicators, textvariable=self.frequency, font=("", font_size),
                  foreground="green").grid(column=0, row=1, padx=1)
        ttk.Label(self.indicators, text="Voltage").grid(column=0, row=2, padx=1)
        ttk.Label(self.indicators, textvariable=self.voltage, font=("", font_size),
                  foreground="blue").grid(column=0, row=3, padx=1)
        ttk.Label(self.indicators, text="Impedance").grid(column=0, row=4, padx=1)
        ttk.Label(self.indicators, textvariable=self.impedance, font=("", font_size),
                  foreground="red").grid(column=0, row=5, padx=1)

        # Capturing button
        ttk.Button(self.indicators, text="Capture trace",
                   command=lambda: self.capture_trace(plt)).grid(column=0, row=6, padx=1, sticky=W)

        # Event monitoring
        ttk.Label(self.serial_communication, text="Events monitor:").grid(column=0, row=0, padx=1, sticky=W)
        self.log = Text(self.serial_communication, state="disabled", width=70, height=5, wrap="word", bg="light gray")
        self.log.grid(column=0, row=1, padx=5, pady=5, sticky=W)

    def about_window(self):
        about = Toplevel(self.the_root)
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
        self.scope = Oscilloscope()
        self.scope.setup()
        if self.scope.open_handle():
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
            self.scope_is_run = True
            self.scope_thread = Thread(target=self.get_data)
            self.scope_thread.start()
        else:
            self.write_to_log("Oscilloscope not detected")

    def get_data(self):
        while self.scope_is_run:
            self.scope.start_capture()
            adc_signals = self.scope.read_data(data_size=0xC00, raw=False)
            self.buffer_size_x = len(adc_signals[0])
            self.buffer_size_y = len(adc_signals[1])
            self.x_signal = self.scope.scale_read_data(adc_signals[0])
            self.y_signal = self.scope.scale_read_data(adc_signals[1])
            if len(self.x_signal) == 3072:
                self.x_signal_past = self.x_signal
            if len(self.y_signal) == 3072:
                self.y_signal_past = self.y_signal

    def init(self):
        self.line.set_data([], [])
        return self.line,

    def update(self, frame):
        # Update function: called for each frame
        plot_x_signal = []
        plot_y_signal = []
        try:
            plot_x_signal = [self.x_signal[frame] for frame in range(self.buffer_size_x)]
            plot_y_signal = [self.y_signal[frame] for frame in range(self.buffer_size_y)]

            self.line.set_data(plot_x_signal, plot_y_signal)  # Update the plot with the new data
            return self.line,
        except IndexError as e:
            self.write_to_log(repr(e))
            if len(self.x_signal_past) == 3072:
                plot_x_signal = [self.x_signal_past[frame] for frame in range(self.buffer_size_x)]
            if len(self.y_signal_past) == 3072:
                plot_y_signal = [self.y_signal_past[frame] for frame in range(self.buffer_size_y)]

            self.line.set_data(plot_x_signal, plot_y_signal)  # Update the plot with the new data
            return self.line,

    def populate_plotter(self):
        # Create a figure and axis
        self.fig, ax = plt.subplots(figsize=(5, 4))
        ax.set_xlim(-5, 5)
        ax.set_ylim(-5, 5)
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        self.line, = ax.plot([], [], lw=1)  # Empty plot to update
        self.fig.tight_layout(pad=0)
        ax.set_position((0.05, 0.05, 0.92, 0.92))
        # The signal
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tracer)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

    def animate_plot(self):
        # Create animation
        self.ani = FuncAnimation(self.fig, self.update, frames=100, init_func=self.init, blit=True, interval=0.01)
        plt.grid()
        plt.yticks([n for n in range(-5, 5)])
        plt.xticks([n for n in range(-5, 5)])

    def connecting_window(self):
        self.setup_uart = Toplevel()
        self.setup_uart.resizable(False, False)
        self.setup_uart.title("Configure serial communication")
        self.icon = PhotoImage(file='scope.gif')
        self.setup_uart.tk.call('wm', 'iconphoto', self.setup_uart._w, self.icon)
        ttk.Label(self.setup_uart, text="Select Port:").grid(row=0, column=0, padx=40, pady=30, sticky=W)
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if len(ports) == 0:
            ports = "______NO_PORTS______"
        self.port_combox = ttk.Combobox(self.setup_uart, values=ports, state="readonly")
        self.port_combox.bind("<Button-1>", self.callback)
        self.port_combox.grid(row=0, column=1, padx=5, pady=30)
        self.port_combox.set(ports)

        ttk.Label(self.setup_uart, text="Select Baud Rate:").grid(row=1, column=0, padx=40, pady=3, sticky=W)
        self.baud_combobox = ttk.Combobox(self.setup_uart, values=["2400", "4800", "9600", "14400", "19200",
                                                                   "57600", "115200"], state="readonly")
        self.baud_combobox.set("9600")
        self.baud_combobox.grid(row=1, column=1, padx=5, pady=3)

        self.use_scope.set(True)
        self.check = ttk.Checkbutton(self.setup_uart, text="Connect Scope", variable=self.use_scope,
                                     offvalue=False, onvalue=True)
        self.check.grid(row=2, column=1, padx=5, pady=5)

        self.connect_button = ttk.Button(self.setup_uart, text="Connect", command= lambda: self.connecting_device())
        if ports == "______NO_PORTS______":
            self.connect_button.config(state=tkinter.DISABLED)
        self.connect_button.grid(row=4, column=1, padx=90, pady=30)

    def callback(self, event):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        if len(ports) > 0:
            self.port_combox.set(ports)
            self.port_combox["values"] = ports
            self.connect_button.config(state=tkinter.NORMAL)

    def connecting_device(self):
        port = self.port_combox.get()
        baud = int(self.baud_combobox.get())
        try:
            self.uart = serial.Serial(port, baudrate=baud, timeout=0.1, write_timeout=0.1)
            self.connection_active = True
            self.thread_uart = Thread(target=self.read_from_port)
            self.thread_uart.daemon = True
            self.thread_uart.start()
            self.monitoring_serial = True
            self.send_command("hello", self.uart)
            self.populate_plotter()
        except Exception as e:
            self.write_to_log(repr(e))
        time.sleep(1)
        if self.use_scope.get() is True:
            self.starting_scope()
            if self.scope_is_run:
                self.populate_plotter()
                self.thread_animation = Thread(target=self.animate_plot())
                self.thread_animation.start()
        time.sleep(0.5)
        self.setup_uart.destroy()

    def disconnecting_device(self):
        if self.uart is not None:
            self.send_command("bye", self.uart)
            time.sleep(0.1)
            self.connection_active = False
            self.uart.close()
            time.sleep(0.1)
        else:
            self.write_to_log("Nothing to disconnect")
        if self.scope is not None:
            self.scope_is_run = False
            if self.use_scope.get() is True:
                self.scope.stop_capture()
                time.sleep(0.5)
                self.scope.close_handle()
            self.thread_animation.join()

    def read_from_port(self):
        while self.connection_active:  # Check the flag in the reading loop
            try:
                if self.uart.inWaiting() > 0:
                    answer = self.uart.read_until()
                    self.decoded_answer = answer.decode("utf-8").replace("\r\n", "")
                    self.received_command = True
                    if self.decoded_answer[0] == "F":
                        self.frequency.set(self.frequency_dict[self.decoded_answer])
                        if self.use_scope.get() is True:
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
                        if self.use_scope.get() is True:
                            if self.voltage.get() == "200mV":
                                self.scope.set_ch1_voltage_range(10)
                                self.scope.set_ch2_voltage_range(10)
                            else:
                                self.scope.set_ch1_voltage_range(1)
                                self.scope.set_ch2_voltage_range(1)
                    elif self.decoded_answer[0] == "R":
                        self.impedance.set(self.impedance_dict[self.decoded_answer])
                    elif self.decoded_answer[0] == "c":
                        self.capture_trace(plt)
                    self.write_to_log("Receiving: " + self.decoded_answer)
                    self.received_command = False
            except Exception as e:
                self.write_to_log(repr(e))
                break

    def on_closing(self):
        if self.uart is not None:
            self.send_command("bye", self.uart)
            time.sleep(0.1)
            self.connection_active = False
            self.uart.close()
            time.sleep(0.1)
        if self.use_scope.get() is True:
            if self.scope_is_run is True:
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
