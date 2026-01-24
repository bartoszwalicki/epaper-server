import argparse
from PIL import Image
import os

def convert_image(image_path, output_path, invert=False, threshold=128):
    try:
        img = Image.open(image_path)
    except IOError:
        print(f"Error: Unable to open image file {image_path}")
        return

    # Resize to 400x300 if needed (maintaining aspect ratio usually preferred, but here we force fit or crop?)
    # Let's assume user provides correct ratio or we resize to fit.
    # Target size
    TARGET_WIDTH = 400
    TARGET_HEIGHT = 300
    
    # Convert using dithering (Mode '1' uses Floyd-Steinberg by default)
    # We first resize to ensure 1-to-1 pixel mapping
    img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
    
    # Convert to 1-bit monochrome with dithering
    # Note: convert("1") applies dithering by default.
    img = img.convert("1")
    
    # Get pixel access
    pixels = img.load()
    
    c_array = []
    
    # Process Row by Row
    for y in range(TARGET_HEIGHT):
        byte_val = 0
        for x in range(TARGET_WIDTH):
            # In Mode '1', pixels are 0 (Black) or 255 (White) usually?
            # Actually in mode '1', 0 is Black, 1 is White (or 255 depending on implementation access)
            # Let's check:
            pixel = pixels[x, y]
            
            # e-paper expected: 1=White, 0=Black
            # PIL '1' mode: 0=Black, 255=White (when mapped) but value is often 0 or 1?
            # Safe check:
            if pixel > 0:
                bit = 1 # White
            else:
                bit = 0 # Black
                
            if invert:
                bit = 1 - bit
            
            # Pack MSB first
            bit_pos = 7 - (x % 8)
            
            if bit:
                byte_val |= (1 << bit_pos)
            
            # If we filled a byte or are at end of row
            if (x % 8) == 7 or x == TARGET_WIDTH - 1:
                c_array.append(byte_val)
                byte_val = 0

    # Write to file
    with open(output_path, "w") as f:
        name = os.path.splitext(os.path.basename(output_path))[0]
        f.write(f"#include <stdint.h>\n\n")
        f.write(f"// Image: {image_path}, Size: {TARGET_WIDTH}x{TARGET_HEIGHT}\n")
        f.write(f"const uint8_t {name}_data[] = {{\n")
        
        for i, byte in enumerate(c_array):
            if i % 16 == 0:
                f.write("    ")
            f.write(f"0x{byte:02X}, ")
            if i % 16 == 15:
                f.write("\n")
        
        f.write("\n};\n")
        
    print(f"Successfully converted {image_path} to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert image to C array for SSD1683 400x300 Display")
    parser.add_argument("image", help="Input image file (png, jpg, etc.)")
    parser.add_argument("-o", "--output", help="Output C file (default: image_data.c)", default="image_data.c")
    parser.add_argument("-i", "--invert", help="Invert colors", action="store_true")
    
    args = parser.parse_args()
    
    convert_image(args.image, args.output, args.invert)
