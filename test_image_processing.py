#!/usr/bin/env python3
"""
Quick test to verify image processing works
"""
import io
import sys
from PIL import Image

# Create a test gradient image
img = Image.new('RGB', (800, 600))
pixels = img.load()
for y in range(600):
    for x in range(800):
        pixels[x, y] = (x % 256, y % 256, 128)

# Save as JPEG to stream
img_stream = io.BytesIO()
img.save(img_stream, 'JPEG')
img_stream.seek(0)

# Simulate server processing
TARGET_WIDTH = 400
TARGET_HEIGHT = 300

img = Image.open(img_stream)

# Resize
w_percent = (TARGET_WIDTH / float(img.size[0]))
h_size = int((float(img.size[1]) * float(w_percent)))
img = img.resize((TARGET_WIDTH, h_size), Image.Resampling.LANCZOS)

# Convert to grayscale
img = img.convert("L")

# Crop/pad
new_img = Image.new("L", (TARGET_WIDTH, TARGET_HEIGHT), 255)
if h_size > TARGET_HEIGHT:
    top = (h_size - TARGET_HEIGHT) // 2
    bottom = top + TARGET_HEIGHT
    img = img.crop((0, top, TARGET_WIDTH, bottom))
    new_img.paste(img, (0, 0))
else:
    top = (TARGET_HEIGHT - h_size) // 2
    new_img.paste(img, (0, top))

img = new_img

# Save to JPEG
output_io = io.BytesIO()
img.convert("RGB").save(output_io, 'JPEG', quality=95)
output_io.seek(0)

# Write to file
with open('test-processing.jpg', 'wb') as f:
    f.write(output_io.read())

print(f"Test image created: test-processing.jpg ({img.size[0]}x{img.size[1]})")
print("If this opens correctly, the issue is with the server endpoint, not the processing logic")
