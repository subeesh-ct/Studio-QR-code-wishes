# CT Wishlink Generator 🎁

A Premium Windows Desktop Application to create customized wish links and generate QR codes instantly. 

**Note:** All the required source files (`app.py`, `index.html`, and `CT-Stdio.ico`) are provided in the repository above. You can download and use them directly. (`redirect.html` is not needed for this project, so you can safely ignore it.)

## Features ✨
* **ImgBB API Integration:** Seamless and permanent image uploads.
* **Audio URL Support:** Easy redirection for audio files.
* **Live QR Code Generation:** Instantly creates a downloadable QR code for the generated link.
* **Auto Setup:** Forces initial configuration (API Keys & URLs) on the first run.

---

## Method 1: How to Run Locally 🚀
1. **Python Installation:** Ensure Python is properly installed on your system (make sure to check "Add Python to PATH" during installation).
2. **IDE Setup:** Open the downloaded repository folder in VS Code (or any preferred IDE). **Make sure to select the correct Python Interpreter** in your editor.
3. **Run the Script:** Open your integrated terminal and run the following command:

```bash
python app.py
```

---

## Method 2: How to Build `.exe` File (For Windows) 📦
If you want to convert this script into a standalone Windows application (.exe), open your terminal and run this exact command:

```bash
pyinstaller --noconsole --onefile --icon="CT-Stdio.ico" --add-data "CT-Stdio.ico;." --collect-all customtkinter --name="Ct wishlink generator" app.py
```
