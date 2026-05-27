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
        "type": "IMAGE",
        "personIds": [
            "80fe403f-e8f3-4e97-921b-2114c68883b0",
            "a117a2df-6401-4ea3-8d3b-50eb09cbf07d",
            "fe6f80fd-6841-450c-a24e-d89cddad3691",
            "6cfabf47-38ad-4cee-91c7-7afbd99ad5f6",
        ],
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

def process_image_debug(image_stream):
    """
    DEBUG VERSION: Resizes and crops, returns PIL Image (not packed binary).
    """
    try:
        img = Image.open(image_stream)
        # Apply EXIF orientation (fixes rotated photos from phones/cameras)
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except IOError:
        print("Error opening image")
        return None

    # 1. Smart resize to cover the target area (400x300)
    # Calculate aspect ratios
    target_ratio = TARGET_WIDTH / TARGET_HEIGHT  # 400/300 = 1.333
    img_ratio = img.size[0] / img.size[1]
    
    # Resize so image covers the entire target area
    # (some parts may be cropped)
    if img_ratio > target_ratio:
        # Image is wider than target - resize by height
        new_height = TARGET_HEIGHT
        new_width = int(img.size[0] * (TARGET_HEIGHT / img.size[1]))
    else:
        # Image is taller or same ratio - resize by width
        new_width = TARGET_WIDTH
        new_height = int(img.size[1] * (TARGET_WIDTH / img.size[0]))
    
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Convert to grayscale
    img = img.convert("L")
    
    # 2. Crop center to exact target size
    # Calculate crop box
    left = (new_width - TARGET_WIDTH) // 2
    top = (new_height - TARGET_HEIGHT) // 2
    right = left + TARGET_WIDTH
    bottom = top + TARGET_HEIGHT
    
    img = img.crop((left, top, right, bottom))
    
    # 3. Convert to black & white with dithering
    img = img.convert("1")  # Floyd-Steinberg dithering
    
    # 4. Pack bits for ESP32
    # 400x300 = 120,000 pixels / 8 = 15,000 bytes
    # Row-major, Top-to-Bottom, MSB First
    pixels = img.load()
    packed_bytes = bytearray()
    
    for y in range(TARGET_HEIGHT):
        current_byte = 0
        for x in range(TARGET_WIDTH):
            pixel = pixels[x, y]
            bit = 1 if pixel > 0 else 0
            
            # Pack MSB first
            bit_pos = 7 - (x % 8)
            if bit:
                current_byte |= (1 << bit_pos)
            
            if (x % 8) == 7:
                packed_bytes.append(current_byte)
                current_byte = 0
    
    return bytes(packed_bytes)

@app.route('/get_image', methods=['POST'])
def get_image():
    # 1. Get random image metadata
    metadata = fetch_random_image_metadata()
    if not metadata:
        return "Failed to fetch metadata", 500
        
    asset_id = metadata.get('id')
    
    if not asset_id:
        return "Invalid metadata", 500
        
    # 2. Download image
    image_stream = fetch_image_bytes(asset_id)
    if not image_stream:
        return "Failed to download image", 500
        
    # 3. Process image
    raw_data = process_image_debug(image_stream)
    if not raw_data:
        return "Failed to process image", 500
        
    # 4. Return raw binary bytes
    response = make_response(raw_data)
    response.headers.set('Content-Type', 'application/octet-stream')
    response.headers.set('Content-Length', str(len(raw_data)))
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
