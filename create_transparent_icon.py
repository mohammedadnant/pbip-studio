"""
Create transparent ICO file from PNG
"""
from PIL import Image
import os

# Source transparent PNG
png_path = "logos/logo pbip studio Transparent 512.png"
ico_path = "pbip-studio.ico"

if not os.path.exists(png_path):
    print(f"ERROR: {png_path} not found")
    exit(1)

print("Creating transparent icon from PNG...")
print(f"Source: {png_path}")
print(f"Target: {ico_path}")

# Open the transparent PNG
img = Image.open(png_path)

# Ensure it has an alpha channel
if img.mode != 'RGBA':
    img = img.convert('RGBA')

# Create ICO with multiple sizes (16, 32, 48, 64, 128, 256)
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# Save as ICO with all sizes
img.save(ico_path, format='ICO', sizes=sizes)

print(f"✓ Created transparent icon: {ico_path}")
print(f"  Sizes included: {', '.join([f'{s[0]}x{s[1]}' for s in sizes])}")
print("\nNext step: Run .\\build_msi.ps1 to rebuild with the new icon")
