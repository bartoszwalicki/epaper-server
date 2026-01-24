* Application is written in Python

* Application responds to POST requests at /get_image
POST request have no body
POST request have no query params

* On POST request application run process of getting random image from local Immich server using request:

```curl
curl --location '192.168.0.31:2283/api/search/random?size=1' \
--header 'x-api-key: MK9SLexmExAZ3o71QQ5VXB3qZNg7nbWxOihZDV3x2E' \
--header 'Content-Type: application/json' \
--data '{
    "size": 1,
    "type": "IMAGE"
}'
```
 it responds:

 [
    {
        "id": "46ac76f6-8889-4d62-89e9-743feb5e54cc",
        "createdAt": "2026-01-20T00:06:10.009Z",
        "deviceAssetId": "web-IMG_20260101_193123.jpg-1767292285000",
        "ownerId": "125d2126-786c-4e7c-9fc2-72620c5a00ee",
        "deviceId": "WEB",
        "libraryId": null,
        "type": "IMAGE",
        "originalPath": "/opt/immich/upload/upload/125d2126-786c-4e7c-9fc2-72620c5a00ee/77/89/7789f9ab-ae05-4165-b396-1bcd088c97b9.jpg",
        "originalFileName": "IMG_20260101_193123.jpg",
        "originalMimeType": "image/jpeg",
        "thumbhash": "ICkGDYANslJRt5h6ebaIaAZ8dOII",
        "fileCreatedAt": "2026-01-01T18:31:25.174Z",
        "fileModifiedAt": "2026-01-01T18:31:25.000Z",
        "localDateTime": "2026-01-01T19:31:25.174Z",
        "updatedAt": "2026-01-20T00:06:10.288Z",
        "isFavorite": false,
        "isArchived": false,
        "isTrashed": false,
        "visibility": "timeline",
        "duration": "0:00:00.00000",
        "livePhotoVideoId": null,
        "people": [],
        "checksum": "Cj2xxC0CIfcEHlBcDUeZAh45TxY=",
        "isOffline": false,
        "hasMetadata": true,
        "duplicateId": null,
        "resized": true
    }
]

Then application download image from path given at "originalPath" field.

* After acquiring image processing of image begin:
    * Image is resized to width 400px
    * Then central part of image is taken with 300px height window
    * Image converted to black&white image with dithering - as in example-image-processor.py

* Application responds with C array of image data that align with requirement:
    Note: The fetched image MUST be in the correct raw binary format:
     400x300, 1-bit per pixel, Row-Major, Top-to-Bottom, MSB First.
     If the server returns PNG/JPG, this will display garbage!
     The user asked for "const uint8_t image data from local server", usually implying raw bytes.
     If server returns HTTP response body as raw bytes, this works.

