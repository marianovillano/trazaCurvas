frequencies = {"5Hz": "1", "20Hz": "2", "50Hz": "3", "60Hz": "4", "200Hz": "5", "500Hz": "6", "2kHz": "7", "5kHz": "8"}
voltages = {"200mV": "9", "3.3V": "10", "5V": "11", "9V": "12"}
d_impedance = {"45R": "13", "415R": "14", "726R": "15", "1.5kR": "16"}

frequency_dict = {"F1": "5Hz", "F2": "20Hz", "F3": "50Hz", "F4": "60Hz", "F5": "200Hz", "F6": "500Hz", "F7": "2kHz",
                  "F8": "5kHz"}
voltage_dict = {"V9": "200mV", "V10": "3.3V", "V11": "5V", "V12": "9V"}
impedance_dict = {"R13": "45R", "R14": "415R", "R15": "726R", "R16": "1.5kR"}


def send_command(message, serial_monitor, uart):
    try:
        message_encoded = message.encode("utf-8")
        uart.write(message_encoded)
    except Exception as e:
        serial_monitor.set(repr(e))


def show_frequency(frequency, serial_monitor, uart, obj_scope):
    if uart is not None:
        frequency.set(frequency.get())
        send_command(frequencies[frequency.get()], serial_monitor, uart)
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


def show_voltage(voltage, serial_monitor, uart, obj_scope):
    if uart is not None:
        voltage.set(voltage.get())
        send_command(voltages[voltage.get()], serial_monitor, uart)
        if voltage.get() == "200mV":
            obj_scope.set_ch1_voltage_range(10)
            obj_scope.set_ch2_voltage_range(10)
        else:
            obj_scope.set_ch1_voltage_range(1)
            obj_scope.set_ch2_voltage_range(1)


def show_impedance(impedance, serial_monitor, uart):
    impedance.set(impedance.get())
    send_command(d_impedance[impedance.get()], serial_monitor, uart)


def capture_trace(plt):
    plt.savefig("image.png")


def open_profile():
    pass


def close_profile():
    pass
