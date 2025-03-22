from tkinter import *
from tkinter import ttk
import os

def show_frequency(var_frequency):
    var_frequency.set(var_frequency.get())

def show_voltage(var_voltage, obj_scope):
    var_voltage.set(var_voltage.get())
    if var_voltage.get() == "200mV":
        obj_scope.set_ch1_voltage_range(10)
        obj_scope.set_ch2_voltage_range(10)
    else:
        obj_scope.set_ch1_voltage_range(1)
        obj_scope.set_ch2_voltage_range(1)

def show_impedance(var_impedance):
    var_impedance.set(var_impedance.get())

def capture_trace(obj_plt):
    obj_plt.savefig("image2.png")

def open_captures(obj_root):
    captures_window = Toplevel(obj_root)
    captures_window.title("V-I traces captured")
    captures_window.geometry("800x600")
    figs = ttk.Frame(captures_window, padding=3)
    try:

        photo = PhotoImage(file=os.path.abspath("image2.png"))
        # Create canvas and add image
        canvas_figs = Canvas(captures_window, width=640, height=480)
        canvas_figs.pack()
        canvas_figs.create_image(0, 0, anchor=NW, image=photo)
        # Store reference in root to prevent garbage collection
        canvas_figs.photo = photo  # This is important!
        captures_window.photo = photo
    except Exception as e:
        print(f"Error loading image: {e}")