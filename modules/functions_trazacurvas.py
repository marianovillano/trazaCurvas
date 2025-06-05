import os.path
from datetime import datetime
from tkinter import filedialog
from tkinter import messagebox
from tkinter import *
from tkinter import ttk
import xml.etree.ElementTree as Et
from warnings import showwarning


class Functions:

    def __init__(self):
        self.captures = None
        self.log = None
        self.pin_numbers = IntVar(value=1)
        self.ic_name = StringVar()
        self.ic_label = StringVar()
        self.board_name = StringVar()
        self.pin_captured = 1
        self.dir_captures = "image_captures"
        self.frequencies = {"5Hz": "1", "20Hz": "2", "50Hz": "3", "60Hz": "4", "200Hz": "5", "500Hz": "6", "2kHz": "7",
                            "5kHz": "8"}
        self.voltages = {"200mV": "9", "3.3V": "10", "5V": "11", "9V": "12"}
        self.d_impedance = {"45R": "13", "415R": "14", "726R": "15", "1.5kR": "16"}
        self.frequency_dict = {"F1": "5Hz", "F2": "20Hz", "F3": "50Hz", "F4": "60Hz", "F5": "200Hz", "F6": "500Hz",
                               "F7": "2kHz", "F8": "5kHz"}
        self.voltage_dict = {"V9": "200mV", "V10": "3.3V", "V11": "5V", "V12": "9V"}
        self.impedance_dict = {"R13": "45R", "R14": "415R", "R15": "726R", "R16": "1.5kR"}

    def send_command(self, message, uart):
        try:
            if uart is not None:
                message_encoded = message.encode("utf-8")
                uart.write(message_encoded)
                self.write_to_log("Sending: " + message)
            else:
                self.write_to_log("UART connection object isn't initiated yet")
        except Exception as e:
            self.write_to_log(repr(e))

    def show_frequency(self, frequency, uart, obj_scope):
        if uart is not None:
            frequency.set(frequency.get())
            self.send_command(self.frequencies[frequency.get()], uart)
            if self.use_scope.get() is True:
                if frequency.get() == "5Hz":
                    obj_scope.set_sample_rate(102)
                elif frequency.get() == "20Hz":
                    obj_scope.set_sample_rate(106)
                elif frequency.get() == "50Hz" or frequency.get() == "60Hz":
                    obj_scope.set_sample_rate(110)
                elif frequency.get() == "200Hz":
                    obj_scope.set_sample_rate(150)
                else:
                    obj_scope.set_sample_rate(1)
        else:
            self.write_to_log("UART connection object isn't initiated yet")

    def show_voltage(self, voltage, uart, obj_scope):
        if uart is not None:
            voltage.set(voltage.get())
            self.send_command(self.voltages[voltage.get()], uart)
            if self.use_scope.get() is True:
                if voltage.get() == "200mV":
                    obj_scope.set_ch1_voltage_range(10)
                    obj_scope.set_ch2_voltage_range(10)
                else:
                    obj_scope.set_ch1_voltage_range(1)
                    obj_scope.set_ch2_voltage_range(1)
        else:
            self.write_to_log("UART connection object isn't initiated yet")

    def show_impedance(self, impedance, uart):
        impedance.set(impedance.get())
        self.send_command(self.d_impedance[impedance.get()], uart)

    def write_to_log(self, msg):
        number_of_lines = int(self.log.index('end - 1 line').split('.')[0])
        self.log['state'] = 'normal'
        if number_of_lines == 5:
            self.log.delete(1.0, 2.0)
        if self.log.index('end-1c') != '1.0':
            self.log.insert('end', '\n')
        now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        self.log.insert('end', str(now) + " - " + msg)
        self.log.see("5.0")
        self.log['state'] = 'disabled'

    def open_profile(self):
        s = ttk.Style()
        s.configure('captures.TFrame', background='white')
        self.captures = ttk.Frame(self.the_root, padding=3, style='captures.TFrame')
        self.captures.configure(width=550, height=500)
        self.captures.grid_propagate(False)
        self.captures.grid(column=2, row=0, padx=20, pady=20, sticky=N)
        ttk.Label(self.captures, text="Board name: ").grid(column=0, row=0, pady=2, padx=2)
        self.entry_board_name = (ttk.Entry(self.captures, width=35, textvariable=self.board_name))
        self.entry_board_name.grid(column=1, row=0, pady=2, padx=2, columnspan=3)
        ttk.Label(self.captures, text="Pin numbers: ").grid(column=0, row=1, pady=2, padx=2)
        self.entry_pin_numbers = (ttk.Entry(self.captures, width=5, textvariable=self.pin_numbers))
        self.entry_pin_numbers.grid(column=1, row=1, pady=2, padx=2)
        ttk.Label(self.captures, text="IC name: ").grid(column=2, row=1, pady=2, padx=2)
        self.entry_ic_name = (ttk.Entry(self.captures, width=25, textvariable=self.ic_name))
        self.entry_ic_name.grid(column=3, row=1, pady=2, padx=2)
        ttk.Label(self.captures, text="IC label (U...): ").grid(column=4, row=1, pady=2, padx=2)
        self.entry_ic_label = (ttk.Entry(self.captures, width=5, textvariable=self.ic_label))
        self.entry_ic_label.grid(column=5, row=1, pady=2, padx=2)
        ttk.Button(self.captures, text="Save captures", command=lambda: self.saving()).grid(column=6, row=1, padx=1, sticky=W)

    def capture_trace(self, plt):
        if not os.path.exists(self.dir_captures):
            os.mkdir(self.dir_captures)
        if self.ic_label.get() == "" or self.ic_name.get() == "" or self.board_name.get() == "":
            messagebox.showwarning("Missing...", message="Please, fill all the missing fields")
        else:
            if self.pin_captured > self.pin_numbers.get():
                self.write_to_log("No more pins for this IC")
            else:
                plt.savefig(self.dir_captures + "/" + self.ic_name.get() + "_" +  self.ic_label.get() + "_"
                            + "pin" + str(self.pin_captured) + ".png")
                self.entry_pin_numbers.config(state="disabled")
                self.pin_captured += 1

    def saving(self):
        folder_selected = filedialog.askdirectory(title="Select a place where the profile will be created")

        if folder_selected:
            new_folder_path = os.path.join(folder_selected, self.board_name.get())
            os.makedirs(new_folder_path, exist_ok=True)
            print(f"Pasta criada em: {new_folder_path}")
        else:
            print("Nenhuma pasta selecionada.")

    def close_profile(self):
        pass