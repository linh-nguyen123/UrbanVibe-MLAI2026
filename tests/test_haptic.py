import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from engine.haptic_controller import get_vibration_js, SerialHapticDriver


class TestHapticController(unittest.TestCase):
    def test_get_vibration_js_horn(self):
        js = get_vibration_js("VEHICLE_HORN")
        self.assertIn("150, 100, 150", js)
        self.assertIn("navigator.vibrate", js)

    def test_get_vibration_js_siren(self):
        js = get_vibration_js("EMERGENCY_SIREN")
        self.assertIn("300, 100, 300, 100, 300", js)
        self.assertIn("navigator.vibrate", js)

    def test_get_vibration_js_safe(self):
        js = get_vibration_js("SAFE")
        self.assertIn("navigator.vibrate(0)", js)

    def test_serial_driver_fallback(self):
        driver = SerialHapticDriver(port=None)
        self.assertIsNone(driver.connection)
        self.assertFalse(driver.trigger("VEHICLE_HORN"))
        driver.close()

    def test_serial_driver_trigger(self):
        driver = SerialHapticDriver(port=None)
        mock_conn = MagicMock()
        mock_conn.is_open = True
        driver.connection = mock_conn

        self.assertTrue(driver.trigger("VEHICLE_HORN"))
        mock_conn.write.assert_called_with(b"H\n")

        self.assertTrue(driver.trigger("EMERGENCY_SIREN"))
        mock_conn.write.assert_called_with(b"S\n")

        self.assertTrue(driver.trigger("SAFE"))
        mock_conn.write.assert_called_with(b"0\n")

        driver.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
