import os, shutil, tkinter as tk
from tkinter import filedialog, messagebox

IMG_EXT = (".jpg",".jpeg",".png")

# ---------- helpers ----------
def clean(s): return s.strip()

def copy_text(widget):
    root.clipboard_clear()
    root.clipboard_append(widget.get("1.0", tk.END))

def save_txt(data):
    path = filedialog.asksaveasfilename(defaultextension=".txt")
    if path:
        with open(path,"w") as f: f.write(data)

def save_excel(data):
    path = filedialog.asksaveasfilename(defaultextension=".xlsx")
    if path:
        import pandas as pd
        pd.DataFrame(data.split(",")).to_excel(path,index=False,header=False)

def load_names(file_path, textbox_data):
    names = set()
    if file_path:
        if file_path.endswith(".txt"):
            with open(file_path) as f:
                names.update(clean(x) for x in f if x.strip())
        elif file_path.endswith(".xlsx"):
            import pandas as pd
            df = pd.read_excel(file_path)
            names.update(clean(str(x)) for x in df.iloc[:,0])

    if textbox_data:
        for x in textbox_data.split(","):
            if x.strip(): names.add(clean(x))

    input_count.set(f"Input Count: {len(names)}")
    return names

def match(file, names, case, partial):
    f = file if case else file.lower()
    for n in names:
        n2 = n if case else n.lower()
        if partial:
            if n2 in f: return True
        else:
            if f == n2: return True
    return False

# ---------- Export ----------
def export_names():
    src = filedialog.askdirectory()
    if not src: return

    names = []
    for root,_,files in os.walk(src):
        for f in files:
            if f.lower().endswith(IMG_EXT):
                names.append(f)

    export_box.delete("1.0", tk.END)
    export_box.insert(tk.END, ",".join(names))
    export_count.set(f"Export Count: {len(names)}")

# ---------- Process ----------
def run():
    src = src_var.get()
    dst = dst_var.get()
    names = load_names(file_var.get(), input_box.get("1.0",tk.END))

    if not src or not dst:
        messagebox.showerror("Error","Select folders")
        return

    case = case_var.get()
    partial = partial_var.get()
    mode = mode_var.get()
    dup = dup_var.get()
    structure = struct_var.get()

    found, missing = set(), set(names)

    preview = []

    for root,_,files in os.walk(src):
        for f in files:
            if not f.lower().endswith(IMG_EXT): continue
            if match(f, names, case, partial):
                found.add(f)
                missing.discard(f)
                preview.append(f)

                src_path = os.path.join(root,f)
                dst_path = os.path.join(dst,f)

                if structure:
                    rel = os.path.relpath(root, src)
                    dst_path = os.path.join(dst, rel, f)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                if os.path.exists(dst_path):
                    if dup == "skip": continue
                    elif dup == "rename":
                        base,ext = os.path.splitext(f)
                        i=1
                        while os.path.exists(dst_path):
                            dst_path = os.path.join(dst,f"{base}({i}){ext}")
                            i+=1

                if mode=="copy":
                    shutil.copy(src_path,dst_path)
                else:
                    shutil.move(src_path,dst_path)

    preview_box.delete("1.0",tk.END)
    preview_box.insert(tk.END,"\n".join(preview))

    missing_box.delete("1.0",tk.END)
    missing_box.insert(tk.END, ",".join(sorted(missing)))

    status.set(f"Found: {len(found)} | Missing: {len(missing)}")

# ---------- GUI ----------
root = tk.Tk()
root.title("Photo Tool")
root.geometry("650x700")

src_var=tk.StringVar()
dst_var=tk.StringVar()
file_var=tk.StringVar()

case_var=tk.BooleanVar(value=False)
partial_var=tk.BooleanVar(value=False)
mode_var=tk.StringVar(value="copy")
dup_var=tk.StringVar(value="skip")
struct_var=tk.BooleanVar(value=False)

status=tk.StringVar()
export_count=tk.StringVar()
input_count=tk.StringVar()

def pick_dir(v): v.set(filedialog.askdirectory())
def pick_file(v): v.set(filedialog.askopenfilename())

# ---------- Export Frame ----------
frame1 = tk.LabelFrame(root, text="Export Names")
frame1.pack(fill="both", padx=10, pady=5)

tk.Button(frame1,text="Export",command=export_names).pack()
export_box=tk.Text(frame1,height=4)
export_box.pack()

tk.Label(frame1,textvariable=export_count).pack()

tk.Button(frame1,text="Copy",
          command=lambda:copy_text(export_box)).pack(side="left",padx=5)
tk.Button(frame1,text="Save TXT",
          command=lambda:save_txt(export_box.get("1.0",tk.END))).pack(side="left",padx=5)
tk.Button(frame1,text="Save Excel",
          command=lambda:save_excel(export_box.get("1.0",tk.END))).pack(side="left",padx=5)

# ---------- Input Frame ----------
frame2 = tk.LabelFrame(root, text="Selection Input")
frame2.pack(fill="both", padx=10, pady=5)

tk.Entry(frame2,textvariable=src_var,width=60).pack()
tk.Button(frame2,text="Source",command=lambda:pick_dir(src_var)).pack()

tk.Entry(frame2,textvariable=dst_var,width=60).pack()
tk.Button(frame2,text="Destination",command=lambda:pick_dir(dst_var)).pack()

tk.Entry(frame2,textvariable=file_var,width=60).pack()
tk.Button(frame2,text="Load File",command=lambda:pick_file(file_var)).pack()

tk.Label(frame2,text="Paste names (comma)").pack()
input_box=tk.Text(frame2,height=3)
input_box.pack()

tk.Label(frame2,textvariable=input_count).pack()

# ---------- Options ----------
frame3 = tk.LabelFrame(root, text="Options")
frame3.pack(fill="both", padx=10, pady=5)

tk.Checkbutton(frame3,text="Case Sensitive",variable=case_var).pack()
tk.Checkbutton(frame3,text="Partial Match",variable=partial_var).pack()
tk.Checkbutton(frame3,text="Keep Folder Structure",variable=struct_var).pack()

tk.Radiobutton(frame3,text="Copy",variable=mode_var,value="copy").pack()
tk.Radiobutton(frame3,text="Move",variable=mode_var,value="move").pack()

tk.Radiobutton(frame3,text="Skip Duplicate",variable=dup_var,value="skip").pack()
tk.Radiobutton(frame3,text="Rename Duplicate",variable=dup_var,value="rename").pack()
tk.Radiobutton(frame3,text="Replace Duplicate",variable=dup_var,value="replace").pack()

# ---------- Run ----------
tk.Button(root,text="Start",bg="green",fg="white",command=run).pack(pady=10)

# ---------- Preview ----------
frame4 = tk.LabelFrame(root, text="Preview (Found)")
frame4.pack(fill="both", padx=10, pady=5)

preview_box=tk.Text(frame4,height=5)
preview_box.pack()

tk.Button(frame4,text="Copy Preview",
          command=lambda:copy_text(preview_box)).pack()

# ---------- Missing ----------
frame5 = tk.LabelFrame(root, text="Missing")
frame5.pack(fill="both", padx=10, pady=5)

missing_box=tk.Text(frame5,height=3)
missing_box.pack()

tk.Button(frame5,text="Copy Missing",
          command=lambda:copy_text(missing_box)).pack(side="left",padx=5)

tk.Button(frame5,text="Save TXT",
          command=lambda:save_txt(missing_box.get("1.0",tk.END))).pack(side="left",padx=5)

# ---------- Status ----------
tk.Label(root,textvariable=status).pack()

root.mainloop()