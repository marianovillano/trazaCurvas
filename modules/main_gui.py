from tkinter import *
from tkinter import ttk
import matplotlib.pyplot as plt

from modules.gui_commands import show_frequency, show_voltage, show_impedance, open_captures, capture_trace

def create_main_window(obj_root, obj_scope, frequency, voltage, impedance):
    # Creating main window
    obj_root = Tk()
    # root.geometry("800x600")
    obj_root.rowconfigure(0, weight=1)
    obj_root.columnconfigure(0, weight=1)
    obj_root.title("V-I curve tracer")
    # root.wm_iconphoto(True, ImageTk.PhotoImage(Image.open("scope.png")))

    # Creating frames inside main window
    tracer = ttk.Frame(obj_root, padding=3)
    indicators = ttk.Frame(obj_root, padding=10)  # , style="TEntry")
    selectors = ttk.Frame(obj_root, padding=3)
    tracer.grid(column=0, row=0)
    indicators.grid(column=1, row=0, sticky=N)
    selectors.grid(column=0, row=1, sticky=W)

    # Selectors framing
    # Frequency selection
    ttk.Label(selectors, text="Frequencies: ").grid(column=0, row=0)
    ttk.Radiobutton(selectors, text="5Hz", variable=frequency, value="5Hz",
                    command=lambda: show_frequency(frequency)).grid(column=1, row=0)
    ttk.Radiobutton(selectors, text="20Hz", variable=frequency, value="20Hz",
                    command=lambda: show_frequency(frequency)).grid(column=2, row=0)
    ttk.Radiobutton(selectors, text="50Hz", variable=frequency, value="50Hz",
                    command=lambda: show_frequency(frequency)).grid(column=3, row=0)
    ttk.Radiobutton(selectors, text="60Hz", variable=frequency, value="60Hz",
                    command=lambda: show_frequency(frequency)).grid(column=4, row=0)
    ttk.Radiobutton(selectors, text="200Hz", variable=frequency, value="200Hz",
                    command=lambda: show_frequency(frequency)).grid(column=5, row=0)
    ttk.Radiobutton(selectors, text="500Hz", variable=frequency, value="500Hz",
                    command=lambda: show_frequency(frequency)).grid(column=6, row=0)
    ttk.Radiobutton(selectors, text="2kHz", variable=frequency, value="2kHz",
                    command=lambda: show_frequency(frequency)).grid(column=7, row=0)
    ttk.Radiobutton(selectors, text="5kHz", variable=frequency, value="5kHz",
                    command=lambda: show_frequency(frequency)).grid(column=8, row=0)

    # Voltage selection
    ttk.Label(selectors, text="Voltages: ").grid(column=0, row=1)
    ttk.Radiobutton(selectors, text="200mV", variable=voltage, value="200mV",
                    command=lambda: show_voltage(voltage, obj_scope)).grid(column=1, row=1)
    ttk.Radiobutton(selectors, text="3.3V", variable=voltage, value="3.3V",
                    command=lambda: show_voltage(voltage, obj_scope)).grid(column=2, row=1)
    ttk.Radiobutton(selectors, text="5V", variable=voltage, value="5V",
                    command=lambda: show_voltage(voltage, obj_scope)).grid(column=3, row=1)
    ttk.Radiobutton(selectors, text="12V", variable=voltage, value="12V",
                    command=lambda: show_voltage(voltage, obj_scope)).grid(column=4, row=1)

    # Impedance selection
    ttk.Label(selectors, text="Impedance: ").grid(column=0, row=2)
    ttk.Radiobutton(selectors, text="45R", variable=impedance, value="45R",
                    command=lambda: show_impedance).grid(column=1, row=2)
    ttk.Radiobutton(selectors, text="415R", variable=impedance, value="415R",
                    command=lambda: show_impedance).grid(column=2, row=2)
    ttk.Radiobutton(selectors, text="726R", variable=impedance, value="726R",
                    command=lambda: show_impedance).grid(column=3, row=2)
    ttk.Radiobutton(selectors, text="1.5kR", variable=impedance, value="1.5kR",
                    command=lambda: show_impedance).grid(column=4, row=2)

    # Capture button
    ttk.Button(selectors, text="Capture trace",
               command=lambda: capture_trace(plt)).grid(column=10, row=1, padx=1, sticky=E)

    # Indicators framing
    ttk.Label(indicators, text="Frequency:").grid(column=0, row=0, padx=1, sticky=NW)
    ttk.Label(indicators, textvariable=frequency).grid(column=0, row=1, padx=1, sticky=W)
    ttk.Label(indicators, text="Voltage:").grid(column=0, row=2, padx=1, sticky=NW)
    ttk.Label(indicators, textvariable=voltage).grid(column=0, row=3, padx=1, sticky=W)
    ttk.Label(indicators, text="Impedance:").grid(column=0, row=4, padx=1, sticky=NW)
    ttk.Label(indicators, textvariable=impedance).grid(column=0, row=5, padx=1, sticky=W)
    ttk.Button(indicators, text="Show captures",
               command=lambda: open_captures(obj_root)).grid(column=0, row=6, padx=1, sticky=W)

    return tracer
