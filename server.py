import os
import io
import requests
from flask import Flask, make_response
from PIL import Image

app = Flask(__name__)

# Configuration
IMMICH_URL = "http://192.168.0.31:2283"
API_KEY = "MK9SLexmExAZ3o71QQ5VXB3qZNg7nbWxOihZDV3x2E"

TARGET_WIDTH = 400
TARGET_HEIGHT = 300

def fetch_random_image_metadata():
    """Fetches metadata for a random image from Immich."""
    url = f"{IMMICH_URL}/api/search/random"
    headers = {
        'x-api-key': API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    params = {
        'size': '1',
        # 'type': 'IMAGE' # Does not seem to be a query param in the curl example, but data body.
    }
    # The curl example uses POST with a body for search/random?size=1
    # Wait, the curl example shows:
    # curl --location '.../api/search/random?size=1' ... --data '{ "size": 1, "type": "IMAGE" }'
    # It seems it requires a POST request.
    
    payload = {
        "size": 1,
        "type": "IMAGE"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, params={'size': 1})
        response.raise_for_status()
        data = response.json()
        if not data:
            return None
        return data[0]
    except Exception as e:
        print(f"Error fetching metadata: {e}")
        return None

def fetch_image_bytes(asset_id, original_path=None):
    """
    Downloads the image data. 
    Ideally uses the API to download the asset by ID.
    """
    # Prefer API download
    download_url = f"{IMMICH_URL}/api/assets/{asset_id}/original"
    headers = {
        'x-api-key': API_KEY,
        'Accept': 'application/octet-stream'
    }
    
    try:
        print(f"Downloading image asset {asset_id} from {download_url}")
        response = requests.get(download_url, headers=headers, stream=True)
        response.raise_for_status()
        return io.BytesIO(response.content)
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def process_image(image_stream):
    """
    Resizes, crops, dithers, and packs the image.
    """
    try:
        img = Image.open(image_stream)
    except IOError:
        print("Error opening image")
        return None

    # 1. Resize to width 400px
    # Calculate new height to maintain aspect ratio
    w_percent = (TARGET_WIDTH / float(img.size[0]))
    h_size = int((float(img.size[1]) * float(w_percent)))
    
    img = img.resize((TARGET_WIDTH, h_size), Image.Resampling.LANCZOS)
    
    # Convert to grayscale to ensure correct mode before cropping/pasting
    img = img.convert("L")
    
    # 2. Central cropping to 300px height
    # If height > 300, crop center.
    # If height < 300, pad with white (or black) to reach 300?
    # Requirements: "Then central part of image is taken with 300px height window"
    
    new_img = Image.new("L", (TARGET_WIDTH, TARGET_HEIGHT), 255) # White background
    
    if h_size > TARGET_HEIGHT:
        # Crop
        top = (h_size - TARGET_HEIGHT) // 2
        bottom = top + TARGET_HEIGHT
        img = img.crop((0, top, TARGET_WIDTH, bottom))
        new_img.paste(img, (0, 0))
    else:
        # Center vertically
        top = (TARGET_HEIGHT - h_size) // 2
        new_img.paste(img, (0, top))
        
    img = new_img

    # 3. Convert to black & white with dithering
    img = img.convert("1") # Default dithering is Floyd-Steinberg
    
    # 4. Pack bits
    # 400x300 = 120,000 pixels. / 8 = 15,000 bytes.
    # Row-major, Top-to-Bottom, MSB First.
    
    pixels = img.load()
    packed_bytes = bytearray()
    
    for y in range(TARGET_HEIGHT):
        current_byte = 0
        for x in range(TARGET_WIDTH):
            # 0=Black, 1=White in PIL binary
            # E-paper usually uses: 0=Black, 1=White.
            # MSB first
            
            pixel = pixels[x, y]
            # Pixel is either 0 or 255 (if accessed as value) or 0/1 depending on PIL version/mode inner workings.
            # In '1' mode: 0 is black, 255 is white usually when mapped to L, but raw values might be 0/1.
            # Let's handle both.
            bit = 1 if pixel > 0 else 0
            
            # Pack MSB first: 
            # x=0 -> bit 7
            # x=1 -> bit 6
            # ...
            # x=7 -> bit 0
            
            bit_pos = 7 - (x % 8)
            if bit:
                current_byte |= (1 << bit_pos)
            
            if (x % 8) == 7:
                packed_bytes.append(current_byte)
                current_byte = 0
                
        # If width is not multiple of 8, we might need to handle the last byte?
        # 400 is divisible by 8 (400/8 = 50). So we are good.
        
    return bytes(packed_bytes)

@app.route('/get_image', methods=['POST'])
def get_image():
    # 1. Get random image metadata
    metadata = fetch_random_image_metadata()
    if not metadata:
        return "Failed to fetch metadata", 500
        
    asset_id = metadata.get('id')
    # original_path = metadata.get('originalPath') # Not used since we use API download
    
    if not asset_id:
        return "Invalid metadata", 500
        
    # 2. Download image
    image_stream = fetch_image_bytes(asset_id)
    if not image_stream:
        return "Failed to download image", 500
        
    # 3. Process image
    raw_data = process_image(image_stream)
    if not raw_data:
        return "Failed to process image", 500
        
    # 4. Return raw bytes
    response = make_response(raw_data)
    response.headers.set('Content-Type', 'application/octet-stream')
    response.headers.set('Content-Length', str(len(raw_data)))
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
