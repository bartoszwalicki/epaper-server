import unittest
from unittest.mock import patch, MagicMock
import io
from PIL import Image
import server

class TestImageServer(unittest.TestCase):
    def setUp(self):
        self.app = server.app.test_client()
        self.app.testing = True

    @patch('server.requests.post')
    @patch('server.requests.get')
    def test_get_image_success(self, mock_get, mock_post):
        # Mock Metadata Response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = [{
            "id": "test-asset-id",
            "originalPath": "/path/to/image.jpg"
        }]

        # Mock Image Download Response
        # Create a dummy image
        img = Image.new('RGB', (800, 600), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)

        mock_get.return_value.status_code = 200
        mock_get.return_value.content = img_byte_arr.read()
        
        # Call the endpoint
        response = self.app.post('/get_image')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/octet-stream')
        
        # Expected size: 400 * 300 / 8 = 15000 bytes
        self.assertEqual(len(response.data), 15000)
        
        # Verify mocks were called
        mock_post.assert_called_with(
            f"{server.IMMICH_URL}/api/search/random",
            headers={
                'x-api-key': server.API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            json={'size': 1, 'type': 'IMAGE'},
            params={'size': 1}
        )
        
        mock_get.assert_called_with(
            f"{server.IMMICH_URL}/api/assets/test-asset-id/original",
            headers={
                'x-api-key': server.API_KEY,
                'Accept': 'application/octet-stream'
            },
            stream=True
        )

    @patch('server.requests.post')
    def test_get_image_no_metadata(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = [] # Empty list
        
        response = self.app.post('/get_image')
        self.assertEqual(response.status_code, 500)

if __name__ == '__main__':
    unittest.main()
