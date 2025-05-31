from tkinter import *
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
import xml.etree.ElementTree as Et


class NewProfileWindow:

    def __init__(self, root_profile):
        self.pin_numbers = {}
        self.cache_ic = []
        self.temporal_db = {}
        self.pin_names = None
        self.ic_datasheet_xml = None
        self.ic_part_xml = None
        self.pins_xml = None
        self.tree = None
        self.ic_id_xml = None
        self.equipment_xml = None
        self.board_xml = None
        self.root_xml = None
        self.root_profile = root_profile
        self.new_profile = Toplevel(self.root_profile)
        self.new_profile.resizable(False, False)
        self.new_profile.title("New board profile")
        self.icon = PhotoImage(file='scope.gif')
        self.new_profile.tk.call('wm', 'iconphoto', self.new_profile._w, self.icon)
        self.new_profile.geometry("700x300")
        self.equipment = StringVar()
        self.board = StringVar()
        self.id_in_board = StringVar()
        self.ic_part = StringVar()
        self.datasheet = StringVar()
        self.number_pins = IntVar()
        self.number_pins.set(1)

        self.upper = ttk.Frame(self.new_profile, padding=3)
        self.left = ttk.Frame(self.new_profile, padding=3)
        self.right = ttk.Frame(self.new_profile, padding=3)
        self.bottom = ttk.Frame(self.new_profile, padding=3)
        self.upper.grid(column=0, row=0, sticky=N)
        self.left.grid(column=0, row=1, sticky=W)
        self.right.grid(column=1, row=1, sticky=E)
        # self.right.grid_columnconfigure(0, weight=1)
        # self.right.grid_rowconfigure(0, weight=1)
        self.bottom.grid(column=0, row=2, sticky=S)

        ttk.Label(self.upper, text="Equipment: ").grid(column=0, row=0, pady=2, padx=2, sticky=E)
        ttk.Entry(self.upper, width=30, textvariable=self.equipment).grid(column=1, row=0, pady=2, padx=2)
        ttk.Label(self.upper, text="Board: ").grid(column=0, row=1, pady=2, padx=2, sticky=E)
        ttk.Entry(self.upper, width=30, textvariable=self.board).grid(column=1, row=1, pady=2, padx=2)

        ttk.Label(self.left, text="Integrated circuits: ").grid(column=0, row=0, pady=10, padx=2, sticky=W)
        ttk.Label(self.left, text="ID in board (U...): ").grid(column=0, row=1, pady=2, padx=2, sticky=W)
        ttk.Entry(self.left, width=30, textvariable=self.id_in_board).grid(column=1, row=1, pady=2, padx=2)
        ttk.Label(self.left, text="IC part: ").grid(column=0, row=2, pady=2, padx=2, sticky=W)
        ttk.Entry(self.left, width=30, textvariable=self.ic_part).grid(column=1, row=2, pady=2, padx=2)
        ttk.Label(self.left, text="Datasheet: ").grid(column=0, row=3, pady=2, padx=2, sticky=W)
        ttk.Entry(self.left, width=30, textvariable=self.datasheet).grid(column=1, row=3, pady=2, padx=2)
        ttk.Label(self.left, text="Number of pins: ").grid(column=0, row=4, pady=2, padx=2, sticky=W)
        ttk.Spinbox(self.left, from_=1.0, to=100.0, textvariable=self.number_pins,
                    state="readonly", width=5).grid(column=1, row=4, pady=2, padx=2, sticky=W)
        ttk.Button(self.left, text="Add IC",
                   command=lambda: self.adding_ic()).grid(column=1, row=5, pady=8, padx=8, sticky=W)

        ttk.Button(self.bottom, text="Create...",
                   command=lambda: self.creating_profile()).grid(column=0, row=0, pady=8, padx=8, sticky=E)
        ttk.Button(self.bottom, text="Close", command=self.new_profile.destroy).grid(column=1, row=0, pady=8,
                                                                                           padx=8, sticky=W)

        # Previous DB to insert to xml
        ttk.Label(self.right, text="ICs:").grid(column=0, row=0, padx=1, sticky=W)
        self.db = ttk.Treeview(self.right, columns=("id_in_board", "info"), show="headings", height=5)
        self.db.heading("id_in_board", text="ID in Board")
        self.db.heading("info", text="Info")
        self.db.column("id_in_board", width=80, anchor="center", stretch=False)
        self.db.column("info", width=150, anchor="center", stretch=False)
        self.db.grid(column=0, row=1, padx=5, pady=5, sticky=W)
        btn_delete = tk.Button(self.right, text="Delete IC", command=self.delete_selected_item)
        btn_delete.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")

    def creating_pins(self):
        pins = ttk.Frame(self.new_profile, padding=3)
        pins.grid(column=0, row=10)
        row = 1
        column = 0
        ttk.Label(pins, text="name").grid(column=0, row=0, pady=2, padx=2, sticky=E)
        ttk.Label(pins, text="number").grid(column=1, row=0, pady=2, padx=2, sticky=E)
        ran = self.number_pins.get()
        self.pin_numbers = {}
        for n in range(ran):
            self.pin_numbers["number{0}".format(n)] = StringVar()
        self.pin_names = {}
        for n in range(ran):
            self.pin_names["name{0}".format(n)] = StringVar()
        for n in self.pin_numbers:
            number = 1
            ttk.Entry(pins, width=5, textvariable=self.pin_numbers[n]).grid(column=column + 1, row=row)
            row += 1
            number += 1
            if row > 20:
                row = 1
                column += 2
                ttk.Label(pins, text="name").grid(column=column, row=0, pady=2, padx=2, sticky=E)
                ttk.Label(pins, text="number").grid(column=column + 1, row=0, pady=2, padx=2, sticky=E)
        row = 1
        column = 0
        for name in self.pin_names:
            ttk.Entry(pins, width=5, textvariable=self.pin_names[name]).grid(column=column, row=row, sticky=E)
            row += 1
            if row > 20:
                row = 1
                column += 2

    def adding_ic(self):
        self.cache_ic.append(self.id_in_board.get())
        self.cache_ic.append(self.ic_part.get())
        self.cache_ic.append(self.datasheet.get())
        self.cache_ic.append(self.number_pins.get())
        if self.id_in_board.get() != "":
            self.temporal_db[self.id_in_board.get()] = self.cache_ic
        self.cache_ic = []
        self.id_in_board.set("")
        self.ic_part.set("")
        self.datasheet.set("")
        self.number_pins.set(1)
        #print(self.temporal_db)
        for item in self.db.get_children():
            self.db.delete(item)
        for id_in_board, info in self.temporal_db.items():
            self.db.insert("", tk.END, values=(id_in_board, ", ".join(map(str, info))))

    def delete_selected_item(self):
        """Remove o item selecionado do Treeview e do dicionário."""
        selected_items = self.db.selection()
        if not selected_items:
            messagebox.showwarning("Warning!", "Select a item to exclude!")
            return
        for item in selected_items:
            id_in_board = self.db.item(item, 'values')[0]
            if id_in_board in self.temporal_db:
                del self.temporal_db[id_in_board]
            self.db.delete(item)

    def creating_profile(self):
        self.adding_ic()
        self.root_xml = Et.Element("root")
        self.equipment_xml = Et.SubElement(self.root_xml, "equipment")
        self.board_xml = Et.SubElement(self.equipment_xml, "board")
        self.equipment_xml.text = self.equipment.get()
        self.board_xml.text = self.board.get()

        for ic in self.temporal_db:
            lista = self.temporal_db[ic]
            self.ic_id_xml = Et.SubElement(self.board_xml, "ID_in_board")
            self.ic_part_xml = Et.SubElement(self.ic_id_xml, "IC_part")
            self.ic_datasheet_xml = Et.SubElement(self.ic_id_xml, "IC_datasheet")
            self.pins_xml = Et.SubElement(self.ic_id_xml, "Pin_numbers")
            self.ic_id_xml.text = lista[0]
            self.ic_part_xml.text = lista[1]
            self.ic_datasheet_xml.text = lista[2]
            ran = lista[3] + 1
            for n in range(1, ran):
                self.pin_numbers["number{0}".format(n)] = Et.SubElement(self.pins_xml, "pin{0}".format(n))

        self.tree = Et.ElementTree(self.root_xml)
        Et.indent(self.tree, space='  ', level=0)
        filename = filedialog.asksaveasfilename(filetypes=[("XML Files", "*.xml"), ("All files", "*.*")],
                                                defaultextension=".xml", confirmoverwrite=True,
                                                initialfile=self.equipment.get())
        if filename:
            self.tree.write(filename)

if __name__ == "__main__":
    root = Tk()
    app = NewProfileWindow(root)
    root.mainloop()
