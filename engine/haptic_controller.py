import logging
from typing import Optional

logger = logging.getLogger(__name__)

def get_vibration_js(danger_type: str) -> str:
    """
    Generate JavaScript snippet for Web Vibration API on mobile browsers.
    VEHICLE_HORN: 2 sharp pulses [150, 100, 150]
    EMERGENCY_SIREN: rapid urgent pulses [300, 100, 300, 100, 300]
    """
    if danger_type == "EMERGENCY_SIREN":
        pattern = "[300, 100, 300, 100, 300]"
    elif danger_type == "VEHICLE_HORN":
        pattern = "[150, 100, 150]"
    else:
        pattern = "0"

    return f"""
    <script>
    if ('vibrate' in navigator) {{
        navigator.vibrate({pattern});
    }}
    </script>
    """

class SerialHapticDriver:
    """
    Hardware Serial / BLE driver for ESP32 or external microcontroller vibration motors.
    Falls back gracefully if serial library or hardware port is unavailable.
    """
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.connection = None
        self._init_connection()

    def _init_connection(self):
        if not self.port:
            return
        try:
            import serial
            self.connection = serial.Serial(self.port, self.baudrate, timeout=0.1)
            logger.info(f"Serial haptic connected to {self.port}")
        except Exception as e:
            logger.warning(f"Serial haptic connection unavailable on {self.port}: {e}")
            self.connection = None

    def trigger(self, danger_type: str) -> bool:
        """
        Send single-byte trigger command to microcontroller.
        'H' for vehicle horn, 'S' for emergency siren, '0' for safe.
        """
        if not self.connection or not self.connection.is_open:
            return False

        cmd_map = {
            "VEHICLE_HORN": b"H\n",
            "EMERGENCY_SIREN": b"S\n",
            "SAFE": b"0\n",
        }
        cmd = cmd_map.get(danger_type, b"0\n")
        try:
            self.connection.write(cmd)
            self.connection.flush()
            return True
        except Exception as e:
            logger.warning(f"Failed to write to serial haptic device: {e}")
            return False

    def close(self):
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None
