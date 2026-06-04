import unittest
from unittest.mock import patch, MagicMock, ANY
import io
from datetime import datetime, timedelta
from PIL import Image
import server
import weather

class TestImageServer(unittest.TestCase):
    def setUp(self):
        self.app = server.app.test_client()
        self.app.testing = True

    @patch('server.fetch_weather', return_value=None)
    @patch('server.requests.post')
    @patch('server.requests.get')
    def test_get_image_success(self, mock_get, mock_post, mock_weather):
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
            json={'size': 1, 'type': 'IMAGE', 'personIds': ANY},
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


def _fake_slots(n=16, start_hour=15):
    slots = []
    for i in range(n):
        dt = datetime(2026, 6, 4, 0, 0) + timedelta(hours=start_hour + i * 3)
        slots.append({
            "dt": dt,
            "hour": dt.hour,
            "temp": 17 - i,
            "code": 0,
            "glyph": weather.WMO_GLYPH[0],
        })
    return slots


class TestWeatherImageEndpoint(unittest.TestCase):
    def setUp(self):
        self.app = server.app.test_client()
        self.app.testing = True

    def _assert_bitmap(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'],
                         'application/octet-stream')
        self.assertEqual(len(response.data), 15000)

    @patch('server.fetch_weather_2day', return_value=_fake_slots())
    def test_weather_image_with_slots(self, _mock):
        self._assert_bitmap(self.app.post('/get_weather_image'))

    @patch('server.fetch_weather_2day', return_value=None)
    def test_weather_image_unavailable(self, _mock):
        # Weather failure must still return a valid 15000-byte page.
        self._assert_bitmap(self.app.post('/get_weather_image'))

    @patch('server.fetch_weather_2day', return_value=[{"hour": 0}])
    def test_weather_image_render_error_falls_back(self, _mock):
        # A malformed slot makes the grid render raise; the endpoint must
        # degrade to the unavailable page rather than 500.
        self._assert_bitmap(self.app.post('/get_weather_image'))


class TestFetchWeather2Day(unittest.TestCase):
    def _mock_response(self, hours=72, start=datetime(2026, 6, 4, 0, 0)):
        times = [(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M")
                 for i in range(hours)]
        temps = [10.0 + (i % 5) for i in range(hours)]
        temps[15] = None  # 15:00 has a missing temperature
        codes = [0 for _ in range(hours)]
        resp = MagicMock()
        resp.json.return_value = {"hourly": {
            "time": times, "temperature_2m": temps, "weather_code": codes,
        }}
        return resp

    @patch('weather.datetime')
    @patch('weather.requests.get')
    def test_samples_3h_boundaries_after_now(self, mock_get, mock_dt):
        mock_get.return_value = self._mock_response()
        # now = 14:32 -> first boundary is 15:00
        mock_dt.now.return_value = datetime(2026, 6, 4, 14, 32)
        mock_dt.fromisoformat.side_effect = datetime.fromisoformat

        slots = weather.fetch_weather_2day()

        self.assertEqual(len(slots), 16)
        self.assertEqual(slots[0]["dt"], datetime(2026, 6, 4, 15, 0))
        self.assertTrue(all(s["hour"] % 3 == 0 for s in slots))
        self.assertTrue(all(s["dt"] >= datetime(2026, 6, 4, 14, 32)
                            for s in slots))
        # A None temperature is preserved (renderer shows "--"), not dropped.
        self.assertIsNone(slots[0]["temp"])

    @patch('weather.requests.get', side_effect=Exception("network down"))
    def test_returns_none_on_failure(self, _mock):
        self.assertIsNone(weather.fetch_weather_2day())


if __name__ == '__main__':
    unittest.main()
