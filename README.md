# CT Wishlink Generator 🎁

A Premium Windows Desktop Application to create customized wish links and generate QR codes instantly. 

## Features ✨
* **ImgBB API Integration:** Seamless and permanent image uploads.
* **Audio URL Support:** Easy redirection for audio files.
* **Live QR Code Generation:** Instantly creates a downloadable QR code for the generated link.
* **Auto Setup:** Forces initial configuration (API Keys & URLs) on the first run.

---

## Method 1: How to Run Locally 🚀
1. **Python Setup:** Make sure Python is properly installed on your system.
2. **Open in VS Code:** Open the `app.py` file in VS Code or any other code editor.
3. **Run the Application:** Open your terminal and run the script:
   python app.py

---

## Method 2: How to Build `.exe` File (For Windows) 📦
If you want to convert this script into a standalone application (.exe), open your terminal and run this exact command:

pyinstaller --noconsole --onefile --icon="CT-Stdio.ico" --add-data "CT-Stdio.ico;." --collect-all customtkinter --name="Ct wishlink generator" app.py
