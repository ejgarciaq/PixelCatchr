from pathlib import Path
from PIL import Image

src = Path(__file__).parents[1] / "assets" / "icon.png"
out = Path(__file__).parents[1] / "assets" / "icon.ico"

if not src.exists():
    raise FileNotFoundError(f"Source PNG not found: {src}")

# Load PNG and convert to ICO (multiple sizes for Windows)
img = Image.open(src)
# Ensure image is RGBA
if img.mode != "RGBA":
    img = img.convert("RGBA")
# Save as ICO with typical sizes
img.save(out, format="ICO", sizes=[(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)])
print(f"Icon converted: {out}")
