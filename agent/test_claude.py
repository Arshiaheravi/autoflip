import subprocess, os, tempfile

env = os.environ.copy()
appdata = os.environ.get("APPDATA", "").replace("\\", "/").replace("C:", "/c")
username = os.environ.get("USERNAME", "")
env["PATH"] = (
    appdata + "/npm" + os.pathsep +
    "/c/Users/" + username + "/AppData/Roaming/npm" + os.pathsep +
    env.get("PATH", "")
)

# Test 1: simple arg
r = subprocess.run("claude -p \"what is 2+2\"", shell=True,
    capture_output=True, text=True, timeout=30, env=env,
    cwd=r"C:\Users\arshi\OneDrive\Desktop\autoflip")
print("=== Test 1 (direct arg) ===")
print("STDOUT:", repr(r.stdout[:200]))
print("STDERR:", repr(r.stderr[:200]))
print("CODE:", r.returncode)

# Test 2: via temp file
with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
    f.write("what is 2+2")
    tmp = f.name

safe = tmp.replace("'", "\\'")
r2 = subprocess.run(f"claude -p \"$(cat '{safe}')\"", shell=True,
    capture_output=True, text=True, timeout=30, env=env,
    cwd=r"C:\Users\arshi\OneDrive\Desktop\autoflip")
print("\n=== Test 2 (via cat file) ===")
print("STDOUT:", repr(r2.stdout[:200]))
print("STDERR:", repr(r2.stderr[:200]))
print("CODE:", r2.returncode)
os.unlink(tmp)
