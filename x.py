import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

IMG_EXT = (".jpg", ".jpeg", ".png")

class PhotoToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Photo Tool")
        self.root.geometry("700x600")

        self.setup_scrollable_window()
        self.setup_variables()
        self.setup_ui()

    # ---------- Helpers ----------
    def clean(self, s): 
        return s.strip()

    def copy_text(self, widget):
        self.root.clipboard_clear()
        self.root.clipboard_append(widget.get("1.0", tk.END))
        messagebox.showinfo("Copied", "Text copied to clipboard.")

    def save_txt(self, data):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
                messagebox.showinfo("Success", "File saved successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{e}")

    def save_excel(self, data):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if path:
            try:
                import pandas as pd
                pd.DataFrame(data.split(",")).to_excel(path, index=False, header=False)
                messagebox.showinfo("Success", "Excel file saved successfully.")
            except ImportError:
                messagebox.showerror("Dependency Error", "Pandas or openpyxl missing.\nPlease run: pip install pandas openpyxl")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save Excel file:\n{e}")

    def load_names(self, file_path, textbox_data):
        names = set()
        if file_path:
            if file_path.endswith(".txt"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        names.update(self.clean(x) for x in f if x.strip())
                except Exception as e:
                    messagebox.showerror("Error", f"Could not read TXT:\n{e}")
            elif file_path.endswith(".xlsx"):
                try:
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    names.update(self.clean(str(x)) for x in df.iloc[:, 0])
                except ImportError:
                    messagebox.showerror("Dependency Error", "Pandas or openpyxl missing.\nPlease run: pip install pandas openpyxl")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not read Excel:\n{e}")

        if textbox_data:
            for x in textbox_data.split(","):
                if x.strip(): 
                    names.add(self.clean(x))

        self.input_count.set(f"Input Count: {len(names)}")
        return names

    def match(self, file, names, case, partial):
        f = file if case else file.lower()
        for n in names:
            n2 = n if case else n.lower()
            if partial:
                if n2 in f: return True
            else:
                if f == n2: return True
        return False

    def pick_dir(self, v): 
        d = filedialog.askdirectory()
        if d: v.set(d)
        
    def pick_file(self, v): 
        f = filedialog.askopenfilename()
        if f: v.set(f)

    # ---------- Export ----------
    def export_names(self):
        src = filedialog.askdirectory()
        if not src: return

        self.status.set("Exporting...")
        self.root.update_idletasks()

        names = []
        for root_dir, _, files in os.walk(src):
            for f in files:
                if f.lower().endswith(IMG_EXT):
                    names.append(f)

        self.export_box.delete("1.0", tk.END)
        self.export_box.insert(tk.END, ",".join(names))
        self.export_count.set(f"Export Count: {len(names)}")
        self.status.set("Export Complete")

    # ---------- Process ----------
    def run(self):
        src = self.src_var.get()
        dst = self.dst_var.get()

        if not src or not dst:
            messagebox.showerror("Error", "Select both Source and Destination folders.")
            return

        names = self.load_names(self.file_var.get(), self.input_box.get("1.0", tk.END))
        if not names:
            messagebox.showwarning("Warning", "No names loaded to search for.")
            return

        # Disable button and update status
        self.run_btn.config(state="disabled", text="Processing...")
        self.status.set("Processing... Please wait.")

        # Gather variables for the thread
        case = self.case_var.get()
        partial = self.partial_var.get()
        mode = self.mode_var.get()
        dup = self.dup_var.get()
        structure = self.struct_var.get()

        threading.Thread(
            target=self._process_files_thread,
            args=(src, dst, names, case, partial, mode, dup, structure),
            daemon=True
        ).start()

    def _process_files_thread(self, src, dst, names, case, partial, mode, dup, structure):
        found, missing = set(), set(names)
        preview = []

        for root_dir, _, files in os.walk(src):
            for f in files:
                if not f.lower().endswith(IMG_EXT): continue
                if self.match(f, names, case, partial):
                    found.add(f)
                    missing.discard(f)
                    preview.append(f)

                    src_path = os.path.join(root_dir, f)
                    
                    if structure:
                        rel = os.path.relpath(root_dir, src)
                        dst_path = os.path.join(dst, rel, f)
                    else:
                        dst_path = os.path.join(dst, f)
                        
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                    if os.path.exists(dst_path):
                        if dup == "skip": continue
                        elif dup == "rename":
                            base, ext = os.path.splitext(f)
                            i = 1
                            while os.path.exists(dst_path):
                                dst_path = os.path.join(os.path.dirname(dst_path), f"{base}({i}){ext}")
                                i += 1

                    try:
                        if mode == "copy":
                            shutil.copy(src_path, dst_path)
                        else:
                            shutil.move(src_path, dst_path)
                    except Exception as e:
                        print(f"Failed to move/copy {src_path}: {e}")

        # Update GUI from main thread
        self.root.after(0, self._process_complete, preview, sorted(list(missing)), found)

    def _process_complete(self, preview, missing_list, found_set):
        self.preview_box.delete("1.0", tk.END)
        self.preview_box.insert(tk.END, "\n".join(preview))

        self.missing_box.delete("1.0", tk.END)
        self.missing_box.insert(tk.END, ",".join(missing_list))

        self.status.set(f"Found: {len(found_set)} | Missing: {len(missing_list)}")
        self.run_btn.config(state="normal", text="Start")
        messagebox.showinfo("Complete", f"Operation Finished!\nFound: {len(found_set)}\nMissing: {len(missing_list)}")

    # ---------- Setup Methods ----------
    def setup_scrollable_window(self):
        self.canvas = tk.Canvas(self.root)
        self.scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        # Bindings
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_linux_scroll)
        self.canvas.bind_all("<Button-5>", self._on_linux_scroll)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_linux_scroll(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    def setup_variables(self):
        self.src_var = tk.StringVar()
        self.dst_var = tk.StringVar()
        self.file_var = tk.StringVar()

        self.case_var = tk.BooleanVar(value=False)
        self.partial_var = tk.BooleanVar(value=False)
        self.mode_var = tk.StringVar(value="copy")
        self.dup_var = tk.StringVar(value="skip")
        self.struct_var = tk.BooleanVar(value=False)

        self.status = tk.StringVar(value="Ready.")
        self.export_count = tk.StringVar(value="Export Count: 0")
        self.input_count = tk.StringVar(value="Input Count: 0")

    def setup_ui(self):
        # ---------- Export ----------
        frame1 = tk.LabelFrame(self.scrollable_frame, text="Export Names")
        frame1.pack(fill="both", padx=10, pady=5)

        tk.Button(frame1, text="Export", command=self.export_names).pack(pady=(5,0))

        exp_frame = tk.Frame(frame1)
        exp_frame.pack(pady=5)

        self.export_box = tk.Text(exp_frame, height=5, width=70)
        self.export_box.pack(side="left")

        tk.Scrollbar(exp_frame, command=self.export_box.yview).pack(side="right", fill="y")
        self.export_box.config(yscrollcommand=lambda *args: None)

        tk.Label(frame1, textvariable=self.export_count).pack()

        btm_frame1 = tk.Frame(frame1)
        btm_frame1.pack(pady=5)
        tk.Button(btm_frame1, text="Copy", command=lambda: self.copy_text(self.export_box)).pack(side="left", padx=5)
        tk.Button(btm_frame1, text="Save TXT", command=lambda: self.save_txt(self.export_box.get("1.0", tk.END))).pack(side="left", padx=5)
        tk.Button(btm_frame1, text="Save Excel", command=lambda: self.save_excel(self.export_box.get("1.0", tk.END))).pack(side="left", padx=5)

        # ---------- Input ----------
        frame2 = tk.LabelFrame(self.scrollable_frame, text="Selection Input")
        frame2.pack(fill="both", padx=10, pady=5)

        tk.Entry(frame2, textvariable=self.src_var, width=60).pack(pady=(5,0))
        tk.Button(frame2, text="Source Folder", command=lambda: self.pick_dir(self.src_var)).pack()

        tk.Entry(frame2, textvariable=self.dst_var, width=60).pack(pady=(5,0))
        tk.Button(frame2, text="Destination Folder", command=lambda: self.pick_dir(self.dst_var)).pack()

        tk.Entry(frame2, textvariable=self.file_var, width=60).pack(pady=(5,0))
        tk.Button(frame2, text="Load TXT/Excel File", command=lambda: self.pick_file(self.file_var)).pack()

        tk.Label(frame2, text="Paste names (comma separated)").pack(pady=(5,0))
        self.input_box = tk.Text(frame2, height=4, width=70)
        self.input_box.pack(padx=10)

        tk.Label(frame2, textvariable=self.input_count).pack(pady=5)

        # ---------- Options ----------
        frame3 = tk.LabelFrame(self.scrollable_frame, text="Options")
        frame3.pack(fill="both", padx=10, pady=5)

        tk.Checkbutton(frame3, text="Case Sensitive", variable=self.case_var).pack()
        tk.Checkbutton(frame3, text="Partial Match", variable=self.partial_var).pack()
        tk.Checkbutton(frame3, text="Keep Folder Structure", variable=self.struct_var).pack()

        opts_frame = tk.Frame(frame3)
        opts_frame.pack(pady=5)
        tk.Radiobutton(opts_frame, text="Copy", variable=self.mode_var, value="copy").pack(side="left", padx=10)
        tk.Radiobutton(opts_frame, text="Move", variable=self.mode_var, value="move").pack(side="left", padx=10)

        dup_frame = tk.Frame(frame3)
        dup_frame.pack(pady=5)
        tk.Radiobutton(dup_frame, text="Skip Duplicate", variable=self.dup_var, value="skip").pack(side="left", padx=5)
        tk.Radiobutton(dup_frame, text="Rename Duplicate", variable=self.dup_var, value="rename").pack(side="left", padx=5)
        tk.Radiobutton(dup_frame, text="Replace Duplicate", variable=self.dup_var, value="replace").pack(side="left", padx=5)

        self.run_btn = tk.Button(self.scrollable_frame, text="Start", bg="green", fg="white", font=("Arial", 10, "bold"), command=self.run)
        self.run_btn.pack(pady=10)

        # ---------- Preview ----------
        frame4 = tk.LabelFrame(self.scrollable_frame, text="Preview")
        frame4.pack(fill="both", padx=10, pady=5)

        prev_frame = tk.Frame(frame4)
        prev_frame.pack(pady=5)

        self.preview_box = tk.Text(prev_frame, height=6, width=70)
        self.preview_box.pack(side="left")

        tk.Scrollbar(prev_frame, command=self.preview_box.yview).pack(side="right", fill="y")
        self.preview_box.config(yscrollcommand=lambda *args: None)

        # ---------- Missing ----------
        frame5 = tk.LabelFrame(self.scrollable_frame, text="❌ Missing Files", fg="red")
        frame5.pack(fill="both", padx=10, pady=10)

        miss_frame = tk.Frame(frame5)
        miss_frame.pack(pady=5)

        self.missing_box = tk.Text(miss_frame, height=6, width=70, bg="#ffe6e6")
        self.missing_box.pack(side="left")

        tk.Scrollbar(miss_frame, command=self.missing_box.yview).pack(side="right", fill="y")
        self.missing_box.config(yscrollcommand=lambda *args: None)

        btm_frame_miss = tk.Frame(frame5)
        btm_frame_miss.pack(pady=5)
        tk.Button(btm_frame_miss, text="Copy Missing", command=lambda: self.copy_text(self.missing_box)).pack(side="left", padx=5)
        tk.Button(btm_frame_miss, text="Save TXT", command=lambda: self.save_txt(self.missing_box.get("1.0", tk.END))).pack(side="left", padx=5)

        # ---------- Status ----------
        tk.Label(self.scrollable_frame, textvariable=self.status, font=("Arial", 10, "italic")).pack(pady=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoToolApp(root)
    root.mainloop()