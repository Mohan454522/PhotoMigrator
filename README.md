# PhotoMigrator 📸

A powerful, modern Desktop Application built in Python to seamlessly migrate, organize, and filter massive amounts of photos and files based on Excel sheets, text lists, or manually pasted criteria.

## ✨ Features
- **Modern Dark UI**: A beautiful, premium interface powered by `CustomTkinter`.
- **Drag & Drop**: Easily select source and destination folders by dropping them straight onto the app window.
- **Flexible Inputs**: Search for specific filenames using `.txt` files (new-line or comma-separated) or `.xlsx` files.
- **Live Progress Tracking**: See exactly how many files are parsing in real-time with a fast, non-blocking background thread.
- **Duplicate Handling**: Built-in rules to optionally Skip, Auto-Rename (`file(1).jpg`), or Replace duplicate files natively.
- **Intelligent Tracking**: Keep exact replicate folder structures during migration or dump them all into a single repository.
- **Reporting**: Easily export missing files or found matches into Text or Excel documents right from the dashboard.

## ⚙️ Requirements & Running from Source
If running directly from the Python source code, you will need the following dependencies:
```bash
pip install customtkinter tkinterdnd2 pandas openpyxl pillow
```
Then simply execute:
```bash
python convt2.py
```

## 📦 Running as a Windows Executable (.exe)
You can compile this project into a standalone, portable Windows executable so that Python is not required on the host computer.
A batch script (`build_exe.bat`) is included to automatically handle `PyInstaller` static collection rules and missing `tkinterdnd2` `.dll` data hooks.
```bash
.\build_exe.bat
```
This takes about 3-5 minutes, and your compiled application will be safely generated inside the `dist/PhotoMigrator` folder!

## 👨‍💻 Author
**Mohan Kumar**  
📧 Email: mohankumar454522@gmail.com
