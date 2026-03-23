"""
Photo Migration Tool
Author: Mohan Kumar
Email: mohankumar454522@gmail.com
"""

import os
import shutil
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

# --- FIX BLURRY AND PIXELATED TEXT ON WINDOWS ---
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass
# ------------------------------------------------

import sys
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES

# Set modern appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

IMG_EXT = (".jpg", ".jpeg", ".png")

# Wrapper to marry TkinterDnD with CustomTkinter
class TkinterDnD_CTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

class PhotoToolApp(TkinterDnD_CTk):
    def __init__(self):
        super().__init__()
        self.title("Photo Migration Tool v3 (Progress & DnD)")
        self.geometry("850x800")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.cancel_flag = False

        self.setup_variables()
        self.setup_ui()

    # ---------- Helpers ----------
    def clean(self, s): 
        return s.strip()

    def copy_text(self, widget):
        self.clipboard_clear()
        self.clipboard_append(widget.get("1.0", tk.END))
        messagebox.showinfo("Copied", "Text copied to clipboard.")

    def save_txt(self, data):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(data)
                messagebox.showinfo("Success", "File saved successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save:\n{e}")

    def save_excel(self, data):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if path:
            try:
                import pandas as pd
                pd.DataFrame(data.split(",")).to_excel(path, index=False, header=False)
                messagebox.showinfo("Success", "Excel file saved successfully.")
            except ImportError:
                messagebox.showerror("Dependency Error", "Pandas missing.\nPlease run: pip install pandas openpyxl")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save Excel file:\n{e}")

    def load_names(self, file_path, textbox_data, silent=False):
        names = set()
        if file_path and os.path.exists(file_path):
            if file_path.endswith(".txt"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().replace('\n', ',')
                        for part in content.split(','):
                            if part.strip():
                                names.add(self.clean(part))
                except Exception as e:
                    if not silent: messagebox.showerror("Error", f"Could not read TXT:\n{e}")
            elif file_path.endswith(".xlsx"):
                try:
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    for x in df.iloc[:, 0]:
                        val = str(x).strip()
                        if val and val.lower() != 'nan':
                            names.add(self.clean(val))
                except Exception as e:
                    if not silent: print(f"Excel error: {e}")

        if textbox_data:
            content = textbox_data.replace('\n', ',')
            for part in content.split(","):
                if part.strip(): 
                    names.add(self.clean(part))

        self.input_count.set(f"Loaded: {len(names)} names")
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

    def drop_inside(self, event, string_var):
        # Depending on OS, event.data may be curly-braced around the path
        path = event.data.strip('{}')
        string_var.set(path)

    def abort_migration(self):
        self.cancel_flag = True
        self.status.set("Cancelling... waiting for current file to finish.")
        self.cancel_btn.configure(state="disabled")

    # ---------- Export ----------
    def export_names(self):
        src = filedialog.askdirectory()
        if not src: return

        self.status.set("Exporting...")
        self.update_idletasks()

        names = []
        for root_dir, _, files in os.walk(src):
            for f in files:
                if f.lower().endswith(IMG_EXT):
                    names.append(f)

        self.export_box.delete("1.0", tk.END)
        self.export_box.insert(tk.END, ",".join(names))
        self.export_count.set(f"Exported: {len(names)} files")
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

        # Prepare UI for migration
        self.cancel_flag = False
        self.run_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.status.set("Phase 1/2: Scanning folders for matches...")

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

    def _transfer_file(self, src_path, dst_path, mode):
        try:
            if mode == "copy":
                shutil.copy(src_path, dst_path)
            else:
                shutil.move(src_path, dst_path)
        except Exception as e:
            print(f"Failed to move/copy {src_path}: {e}")

    def _process_files_thread(self, src, dst, names, case, partial, mode, dup, structure):
        found, missing = set(), set(names)
        preview = []
        to_transfer = []

        # PHASE 1: SCANNING
        for root_dir, _, files in os.walk(src):
            if self.cancel_flag: break
            for f in files:
                if self.cancel_flag: break
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
                    
                    to_transfer.append((src_path, dst_path, f))

        if self.cancel_flag:
            self.after(0, self._process_cancelled)
            return

        total_files = len(to_transfer)
        if total_files == 0:
            self.after(0, self._process_complete, preview, sorted(list(missing)), found)
            return

        self.after(0, lambda: self.status.set(f"Phase 2/2: Transferring {total_files} files..."))

        # PHASE 2: TRANSFERRING
        for i, (src_path, dst_path, f) in enumerate(to_transfer):
            if self.cancel_flag:
                self.after(0, self._process_cancelled)
                return

            os.makedirs(os.path.dirname(dst_path), exist_ok=True)

            if os.path.exists(dst_path):
                if dup == "skip": 
                    pass
                elif dup == "rename":
                    base, ext = os.path.splitext(f)
                    idx = 1
                    while os.path.exists(dst_path):
                        dst_path = os.path.join(os.path.dirname(dst_path), f"{base}({idx}){ext}")
                        idx += 1
                    self._transfer_file(src_path, dst_path, mode)
                elif dup == "replace":
                    self._transfer_file(src_path, dst_path, mode)
            else:
                self._transfer_file(src_path, dst_path, mode)

            # Update progress bar
            prog = (i + 1) / total_files
            self.after(0, self._update_progress, prog, i + 1, total_files)

        self.after(0, self._process_complete, preview, sorted(list(missing)), found)

    def _update_progress(self, prog, current, total):
        self.progress_bar.set(prog)
        self.status.set(f"Transferring: {current} / {total}")

    def _process_cancelled(self):
        self.status.set("Migration Cancelled.")
        self.run_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        messagebox.showwarning("Cancelled", "The file migration was aborted.")

    def _process_complete(self, preview, missing_list, found_set):
        self.preview_box.delete("1.0", tk.END)
        self.preview_box.insert(tk.END, "\n".join(preview))

        self.missing_box.delete("1.0", tk.END)
        self.missing_box.insert(tk.END, ",".join(missing_list))

        self.status.set(f"Results: Found {len(found_set)} | Missing {len(missing_list)}")
        self.progress_bar.set(1.0)
        self.run_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
        messagebox.showinfo("Complete", f"Operation Finished!\nFound: {len(found_set)}\nMissing: {len(missing_list)}")

    # ---------- GUI Setup ----------
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
        self.export_count = tk.StringVar(value="Exported: 0")
        self.input_count = tk.StringVar(value="Loaded: 0 names")

    def setup_ui(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Main Title
        title = ctk.CTkLabel(self.scroll_frame, text="Photo Migration Tool", font=ctk.CTkFont(size=26, weight="bold"))
        title.pack(pady=(10, 20))

        # --- EXPORT SECTION ---
        frame1 = ctk.CTkFrame(self.scroll_frame)
        frame1.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(frame1, text="1. Export Existing Names", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,5))
        ctk.CTkButton(frame1, text="Select Folder to Export", command=self.export_names, width=200).pack(pady=5)
        
        self.export_box = ctk.CTkTextbox(frame1, height=80)
        self.export_box.pack(fill="x", padx=10, pady=5)
        
        info_frame1 = ctk.CTkFrame(frame1, fg_color="transparent")
        info_frame1.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(info_frame1, textvariable=self.export_count).pack(side="left")
        ctk.CTkButton(info_frame1, text="Copy", command=lambda: self.copy_text(self.export_box), width=80).pack(side="right", padx=5)
        ctk.CTkButton(info_frame1, text="Save Excel", command=lambda: self.save_excel(self.export_box.get("1.0", tk.END)), width=80).pack(side="right", padx=5)
        ctk.CTkButton(info_frame1, text="Save TXT", command=lambda: self.save_txt(self.export_box.get("1.0", tk.END)), width=80).pack(side="right", padx=5)

        # --- INPUT SECTION ---
        frame2 = ctk.CTkFrame(self.scroll_frame)
        frame2.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(frame2, text="2. Configure Migration", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,5))

        # Folder selection grid
        input_grid = ctk.CTkFrame(frame2, fg_color="transparent")
        input_grid.pack(fill="x", padx=10, pady=5)
        input_grid.grid_columnconfigure(1, weight=1)

        # Drag and drop wiring
        self.src_entry = ctk.CTkEntry(input_grid, textvariable=self.src_var, placeholder_text="Path or drag and drop a folder here...")
        ctk.CTkButton(input_grid, text="Source Folder", width=140, command=lambda: self.pick_dir(self.src_var)).grid(row=0, column=0, pady=5, padx=(0,10))
        self.src_entry.grid(row=0, column=1, sticky="ew", pady=5)
        self.src_entry.drop_target_register(DND_FILES)
        self.src_entry.dnd_bind('<<Drop>>', lambda e: self.drop_inside(e, self.src_var))

        self.dst_entry = ctk.CTkEntry(input_grid, textvariable=self.dst_var, placeholder_text="Path or drag and drop a folder here...")
        ctk.CTkButton(input_grid, text="Destination Folder", width=140, command=lambda: self.pick_dir(self.dst_var)).grid(row=1, column=0, pady=5, padx=(0,10))
        self.dst_entry.grid(row=1, column=1, sticky="ew", pady=5)
        self.dst_entry.drop_target_register(DND_FILES)
        self.dst_entry.dnd_bind('<<Drop>>', lambda e: self.drop_inside(e, self.dst_var))

        self.file_entry = ctk.CTkEntry(input_grid, textvariable=self.file_var, placeholder_text="Path to names list... you can drag and drop here too.")
        ctk.CTkButton(input_grid, text="Load TXT/Excel", width=140, command=lambda: self.pick_file(self.file_var)).grid(row=2, column=0, pady=5, padx=(0,10))
        self.file_entry.grid(row=2, column=1, sticky="ew", pady=5)
        self.file_entry.drop_target_register(DND_FILES)
        self.file_entry.dnd_bind('<<Drop>>', lambda e: self.drop_inside(e, self.file_var))

        ctk.CTkLabel(frame2, text="Or paste names manually (comma separated):").pack(anchor="w", padx=10)
        self.input_box = ctk.CTkTextbox(frame2, height=60)
        self.input_box.pack(fill="x", padx=10, pady=5)
        
        # Automatic bindings
        self.input_box.bind("<KeyRelease>", lambda e: self.load_names(self.file_var.get(), self.input_box.get("1.0", tk.END), silent=True))
        self.file_var.trace_add("write", lambda *args: self.load_names(self.file_var.get(), self.input_box.get("1.0", tk.END), silent=True))

        ctk.CTkLabel(frame2, textvariable=self.input_count).pack(anchor="e", padx=10, pady=(0, 10))

        # --- OPTIONS SECTION ---
        frame3 = ctk.CTkFrame(self.scroll_frame)
        frame3.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame3, text="3. Options", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,5))

        check_frame = ctk.CTkFrame(frame3, fg_color="transparent")
        check_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkCheckBox(check_frame, text="Case Sensitive", variable=self.case_var).pack(side="left", padx=(0, 20))
        ctk.CTkCheckBox(check_frame, text="Partial Match", variable=self.partial_var).pack(side="left", padx=(0, 20))
        ctk.CTkCheckBox(check_frame, text="Keep Folder Structure", variable=self.struct_var).pack(side="left")

        radio_frame = ctk.CTkFrame(frame3, fg_color="transparent")
        radio_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(radio_frame, text="Mode:").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(radio_frame, text="Copy", variable=self.mode_var, value="copy").pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(radio_frame, text="Move", variable=self.mode_var, value="move").pack(side="left", padx=(0, 30))

        ctk.CTkLabel(radio_frame, text="Duplicates:").pack(side="left", padx=(0, 10))
        ctk.CTkRadioButton(radio_frame, text="Skip", variable=self.dup_var, value="skip").pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(radio_frame, text="Rename", variable=self.dup_var, value="rename").pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(radio_frame, text="Replace", variable=self.dup_var, value="replace").pack(side="left")


        # --- RUN / CANCEL / PROGRESS ACTION AREA ---
        action_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=20)
        
        self.run_btn = ctk.CTkButton(action_frame, text="Start Migration", font=ctk.CTkFont(size=16, weight="bold"), height=40, fg_color="#2EA043", hover_color="#238636", command=self.run)
        self.run_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.cancel_btn = ctk.CTkButton(action_frame, text="Cancel", font=ctk.CTkFont(size=16, weight="bold"), height=40, fg_color="#F85149", hover_color="#DA3633", state="disabled", width=120, command=self.abort_migration)
        self.cancel_btn.pack(side="left")

        # Status Label and Progress Bar under buttons
        ctk.CTkLabel(self.scroll_frame, textvariable=self.status, font=ctk.CTkFont(slant="italic")).pack()
        self.progress_bar = ctk.CTkProgressBar(self.scroll_frame)
        self.progress_bar.pack(fill="x", padx=40, pady=(5, 10))
        self.progress_bar.set(0)


        # --- RESULTS ---
        frame4 = ctk.CTkFrame(self.scroll_frame)
        frame4.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(frame4, text="4. Results (Found files)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,0))
        self.preview_box = ctk.CTkTextbox(frame4, height=100)
        self.preview_box.pack(fill="x", padx=10, pady=10)

        frame5 = ctk.CTkFrame(self.scroll_frame)
        frame5.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(frame5, text="5. Missing Files", text_color="#F85149", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,0))
        self.missing_box = ctk.CTkTextbox(frame5, height=100, text_color="#F85149")
        self.missing_box.pack(fill="x", padx=10, pady=10)
        
        info_frame5 = ctk.CTkFrame(frame5, fg_color="transparent")
        info_frame5.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(info_frame5, text="Copy Missing", command=lambda: self.copy_text(self.missing_box), width=100).pack(side="right", padx=5)
        ctk.CTkButton(info_frame5, text="Save TXT", command=lambda: self.save_txt(self.missing_box.get("1.0", tk.END)), width=100).pack(side="right", padx=5)

        # --- CREDITS FOOTER ---
        credits_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        credits_frame.pack(fill="x", pady=(20, 10))
        ctk.CTkLabel(credits_frame, text="Created by Mohan Kumar", font=ctk.CTkFont(size=13, weight="bold"), text_color="#1F6AA5").pack()
        ctk.CTkLabel(credits_frame, text="mohankumar454522@gmail.com", font=ctk.CTkFont(size=11, slant="italic"), text_color="gray").pack()


if __name__ == "__main__":
    app = PhotoToolApp()
    app.mainloop()