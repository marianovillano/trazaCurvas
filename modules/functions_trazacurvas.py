import os.path
from datetime import datetime

class Functions:

    def __init__(self):
        self.log = None
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

    def capture_trace(self, plt):
        if not os.path.exists(self.dir_captures):
            os.mkdir(self.dir_captures)
        plt.savefig(self.dir_captures + "/" + "image.png")

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
        pass

    def close_profile(self):
        pass