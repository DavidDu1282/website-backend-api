import subprocess

# List of packages to exclude
EXCLUDE_PACKAGES = {"pywin32"}

# Run pip freeze and filter out unwanted packages
result = subprocess.run(["pip", "freeze"], capture_output=True, text=True)
filtered_lines = [
    line for line in result.stdout.splitlines() if not any(pkg in line for pkg in EXCLUDE_PACKAGES)
]

# Save to requirements.txt
with open("requirements.txt", "w") as f:
    f.write("\n".join(filtered_lines) + "\n")

print("Updated requirements.txt (excluded: pywin32)")
