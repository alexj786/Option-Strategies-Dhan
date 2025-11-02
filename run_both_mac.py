import subprocess
import platform
import os

# Full paths to your strategy scripts
base_dir = "/Users/TRP3/python"
bear_script = os.path.join(base_dir, "SBearCall_Spread.py")
bull_script = os.path.join(base_dir, "SBullPut_Spread.py")

print("🚀 Launching both strategies in separate terminals...")

if platform.system() == "Darwin":  # macOS
    subprocess.Popen([
        "osascript", "-e",
        f'tell app "Terminal" to do script "cd {base_dir} && python3 {bear_script}"'
    ])
    subprocess.Popen([
        "osascript", "-e",
        f'tell app "Terminal" to do script "cd {base_dir} && python3 {bull_script}"'
    ])

print("✅ Both strategy scripts launched successfully.")
