import os.path
from datetime import datetime
from tkinter import filedialog
from tkinter import messagebox
from tkinter import *
from tkinter import ttk


class Functions:

    def __init__(self):
        self.trace_compared = None
        self.button_new_ic = None
        self.captured_images = None
        self.new_folder_tree = None
        self.new_folder_path = None
        self.already_created = False
        self.new_ic = False
        self.entry_ic_name = None
        self.entry_pin_numbers = None
        self.entry_ic_label = None
        self.entry_board_name = None
        self.captures = None
        self.log = None
        self.pin_numbers = IntVar(value=1)
        self.pin_captured = 1
        self.row_to_show = 0
        self.column_to_show = 0
        self.photo_list = []
        self.label_list = []
        self.show_pin_captured = IntVar(value=0)
        self.ic_name = StringVar()
        self.ic_label = StringVar()
        self.board_name = StringVar()
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

    def make_profile(self):
        if self.trace_compared is not None:
            messagebox.showwarning("Already open", message="The pin comparison is open, please close it first")
        else:
            self.captures = ttk.Frame(self.the_root, padding=3)
            self.captures.configure(width=550, height=90)
            self.captures.grid_propagate(False)
            self.captures.grid(column=2, row=2, padx=5, pady=2, sticky=N, rowspan=2)

            self.captured_images = ttk.Frame(self.the_root, borderwidth=1, relief="solid", padding=3)
            self.captured_images.configure(width=550, height=450)
            self.captured_images.grid_propagate(False)
            self.captured_images.grid(column=2, row=0, padx=5, pady=2, columnspan=4, sticky=N)

            ttk.Label(self.captures, text="Board name: ").grid(column=0, row=0, pady=2, padx=2, sticky=W)
            self.entry_board_name = ttk.Entry(self.captures, width=15, textvariable=self.board_name)
            self.entry_board_name.grid(column=1, row=0, pady=2, padx=2, columnspan=2, sticky=W)
            ttk.Label(self.captures, text="IC label (U...): ").grid(column=3, row=0, pady=2, padx=2, sticky=W)
            self.entry_ic_label = ttk.Entry(self.captures, width=5, textvariable=self.ic_label)
            self.entry_ic_label.grid(column=4, row=0, pady=2, padx=2, sticky=W)
            ttk.Button(self.captures, text="Creating tree", command=lambda: self.create_tree()).grid(column=5, row=0, padx=1, columnspan=2, sticky=W)
            self.entry_board_name.focus()

    def capture_trace(self, plt):
        if self.captures is not None and self.captured_images is not None:
            try:
                self.new_folder_path = os.path.join(self.new_folder_tree, self.ic_label.get())
                os.makedirs(self.new_folder_path, exist_ok=True)
                if self.new_ic:
                    self.pin_captured = 1
                    self.show_pin_captured.set(self.pin_captured - 1)
                    self.new_ic = False

                if self.ic_label.get() == "" or self.ic_name.get() == "" or self.board_name.get() == "":
                    messagebox.showwarning("Missing...", message="Please, fill all the missing fields")
                else:
                    if self.pin_captured > self.pin_numbers.get():
                        messagebox.showwarning("Already done...", message="No more pins for this IC")
                        self.entry_ic_label.focus()
                        self.button_new_ic.config(state="enabled")
                    else:
                        plt.savefig(self.new_folder_path + "/" + self.ic_name.get() + "_" +  self.ic_label.get() + "_"
                                    + "pin" + str(self.pin_captured) + ".png")

                        self.entry_pin_numbers.config(state="disabled")
                        self.entry_ic_name.config(state="disabled")
                        self.show_pin_captured.set(self.pin_captured)
                        self.photo = PhotoImage(file=(self.new_folder_path + "/" + self.ic_name.get() + "_"
                                                      +  self.ic_label.get() + "_" + "pin" + str(self.pin_captured)
                                                      + ".png"), master=self.captures).subsample(3, 3)
                        self.photo_list.append(self.photo)

                        self.image = Label(self.captured_images, image=self.photo)
                        self.image.grid(column=self.column_to_show, row=self.row_to_show)
                        self.column_to_show += 1
                        self.label_list.append(self.image)
                        if self.column_to_show > 2:
                            self.row_to_show += 1
                            self.column_to_show = 0
                        if self.row_to_show > 2:
                            self.row_to_show = 0
                            self.column_to_show = 0
                        self.pin_captured += 1
            except Exception as e:
                self.write_to_log(f"Error: {e}")
        elif self.trace_compared is not None:
            plt.savefig("comparing.png")
            self.photo = PhotoImage(file="comparing.png", master=self.trace_compared)
            self.image = Label(self.trace_compared, image=self.photo)
            self.image.grid(column=0, row=0)
            self.trace_compared.photo = self.photo

    def create_tree(self):
        if self.already_created:
            self.entry_ic_name.config(state="enabled")
            self.entry_pin_numbers.config(state="enabled")

        folder_selected = filedialog.askdirectory(title="Select a place where the profile will be created")

        if folder_selected:
            self.new_folder_tree = os.path.join(folder_selected, self.board_name.get())
            self.new_folder_path = os.path.join(self.new_folder_tree, self.ic_label.get())
            os.makedirs(self.new_folder_path, exist_ok=True)
            self.write_to_log(f"Created folder in {self.new_folder_path}")
            self.already_created = True
            self.new_ic = True
            ttk.Label(self.captures, text="Pin numbers: ").grid(column=0, row=1, pady=2, padx=2)
            self.entry_pin_numbers = ttk.Entry(self.captures, width=5, textvariable=self.pin_numbers)
            self.entry_pin_numbers.grid(column=1, row=1, pady=2, padx=2)
            ttk.Label(self.captures, text="IC name: ").grid(column=2, row=1, pady=2, padx=2)
            self.entry_ic_name = ttk.Entry(self.captures, width=25, textvariable=self.ic_name)
            self.entry_ic_name.grid(column=3, row=1, pady=2, padx=2, columnspan=3)
            self.button_new_ic = ttk.Button(self.captures, text="New IC...", command=lambda: self.add_new_ic())
            self.button_new_ic.grid(column=6, row=1, padx=1, sticky=W)
            self.button_new_ic.config(state="disabled")
            ttk.Label(self.captures, text="Nº of pins captured: ").grid(column=0, row=2, pady=2, padx=2, columnspan=2, sticky=W)
            ttk.Label(self.captures, textvariable=self.show_pin_captured).grid(column=2, row=2, pady=2, padx=2, columnspan=5, sticky=W)
        else:
            self.write_to_log("Folder not selected")

    def add_new_ic(self):
        self.entry_ic_name.config(state="enabled")
        self.entry_pin_numbers.config(state="enabled")
        self.entry_ic_label.focus()
        self.ic_label.set("")
        self.row_to_show = 0
        self.column_to_show = 0
        self.photo_list.clear()
        self.label_list.clear()
        self.pin_numbers.set(1)
        self.ic_name.set("")
        self.new_ic = True
        self.button_new_ic.config(state="disabled")

    def compare_tracing(self):
        if self.captures is not None and self.captured_images is not None:
            messagebox.showwarning("Already open", message="The capture IC traces is open, please close it first")
        else:
            self.trace_compared = ttk.Frame(self.the_root, borderwidth=1, relief="solid", padding=3)
            self.trace_compared.configure(width=550, height=450)
            self.trace_compared.grid_propagate(False)
            self.trace_compared.grid(column=2, row=0, padx=5, pady=10, columnspan=4, sticky=N)
    
    def close_profile(self):
        if self.captures is not None and self.captured_images is not None:
            self.captures.destroy()
            self.captured_images.destroy()
            self.captures = None
            self.captured_images = None
        if self.trace_compared is not None:
            self.trace_compared.destroy()
            self.trace_compared = None