# Sylvie

This project is a Flask-based web application leveraging AI. Follow the steps below to set up and run the project on your preferred operating system.

## Supported Files

PDF
DOCX
PPT

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
   - [Ubuntu](#ubuntu)
   - [Windows](#windows)
   - [macOS](#macos)
3. [Update .env file](#Update-env-file)
4. [Running the Application](#running-the-application)
5. [License](#license)

---

## Prerequisites

1. Python 3.7 or higher
2. `pip` (Python package installer)
3. Virtual environment tool (`venv` or `virtualenv`)

---

## Installation

### Ubuntu

1. **Update and install Python**:

   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv
   ```

2. **Clone the repository if applicable**:

   ```bash
   git clone <repository_url>
   cd <repository_name>
   ```

3. **Create a virtual environment and activate it**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

### Windows

1. **Install Python**: Download and install Python from the [official Python website](https://www.python.org/downloads/). Ensure `pip` is included in the installation.

2. **Clone the repository**:

   ```powershell
   git clone <repository_url>
   cd <repository_name>
   ```

3. **Create a virtual environment and activate it**:

   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

4. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

---

### macOS

1. **Install Python** (if not installed):

   ```bash
   brew install python
   ```

2. **Clone the repository**:

   ```bash
   git clone <repository_url>
   cd <repository_name>
   ```

3. **Create a virtual environment and activate it**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## Update env file

update the .env file with your Gemini API key.

## Running the Application

1. **Ensure the virtual environment is activated**:

   - Ubuntu/macOS:
     ```bash
     source venv/bin/activate
     ```
   - Windows:
     ```powershell
     .\venv\Scripts\activate
     ```

2. **Run the Flask app**:

   ```bash
   python upload_app.py
   ```

3. **Access the application**:
   Open your browser and navigate to `http://127.0.0.1:5000`.

---

4. Install tesseract-ocr (pdf conversion)
