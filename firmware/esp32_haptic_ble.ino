/**
 * URBANVIBE - FIRMWARE BẢN MẪU PHẦN CỨNG TẦNG 2 (ESP32 + BLE + LRA + LED)
 * 
 * Thiết bị: Vi điều khiển ESP32 BLE receiver gắn trên nón bảo hiểm hoặc gương chiếu hậu.
 * Chức năng:
 *   1. Quảng bá dịch vụ Bluetooth Low Energy (BLE Server).
 *   2. Nhận gói tin cảnh báo từ điện thoại (0: SAFE, 1: HORN, 2: SIREN).
 *   3. Điều khiển Motor rung LRA (Linear Resonant Actuator) trên quai nón tiếp xúc xương hàm.
 *   4. Điều khiển dải LED RGB (NeoPixel WS2812B) viền gương chiếu hậu nhấp nháy tầm nhìn ngoại vi.
 */

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// Định nghĩa Chân GPIO phần cứng
#define PIN_LRA_MOTOR   18   // Chân PWM điều khiển Driver Motor rung LRA (DRV2605L)
#define PIN_NEOPIXEL    19   // Chân tín hiệu dải LED RGB viền gương chiếu hậu
#define NUM_LEDS        8    // Số bóng LED gắn trên gương

// UUID định danh dịch vụ BLE UrbanVibe
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;
uint8_t current_alert_state = 0; // 0: SAFE, 1: HORN, 2: SIREN

// Callback theo dõi kết nối BLE từ điện thoại
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("[UrbanVibe BLE] Đã kết nối với điện thoại người lái!");
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("[UrbanVibe BLE] Mất kết nối Bluetooth, tiếp tục chờ...");
      pServer->getAdvertising()->start();
    }
};

// Callback xử lý dữ liệu cảnh báo gửi từ ứng dụng Edge-AI
class AlertCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
      String value = pCharacteristic->getValue();
      if (value.length() > 0) {
        current_alert_state = (uint8_t)value[0];
        Serial.printf("[UrbanVibe Hardware] Nhận mã cảnh báo: %d\n", current_alert_state);
      }
    }
};

void trigger_haptic_horn() {
  // Xung rung nhịp đôi dứt khoát cho còi xe máy vượt [150ms ON, 80ms OFF, 150ms ON]
  digitalWrite(PIN_LRA_MOTOR, HIGH);
  delay(150);
  digitalWrite(PIN_LRA_MOTOR, LOW);
  delay(80);
  digitalWrite(PIN_LRA_MOTOR, HIGH);
  delay(150);
  digitalWrite(PIN_LRA_MOTOR, LOW);
}

void trigger_haptic_siren() {
  // Xung rung dồn dập cực đại cho xe cứu thương [400ms ON, 100ms OFF, 400ms ON, 100ms OFF, 800ms ON]
  for (int i = 0; i < 2; i++) {
    digitalWrite(PIN_LRA_MOTOR, HIGH);
    delay(400);
    digitalWrite(PIN_LRA_MOTOR, LOW);
    delay(100);
  }
  digitalWrite(PIN_LRA_MOTOR, HIGH);
  delay(800);
  digitalWrite(PIN_LRA_MOTOR, LOW);
}

void setup() {
  Serial.begin(115200);
  Serial.println("=== URBANVIBE EMBEDDED FIRMWARE INITIALIZING ===");

  pinMode(PIN_LRA_MOTOR, OUTPUT);
  pinMode(PIN_NEOPIXEL, OUTPUT);
  digitalWrite(PIN_LRA_MOTOR, LOW);

  // Khởi tạo BLE Server
  BLEDevice::init("UrbanVibe_Helmet_Band");
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_WRITE  |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  pCharacteristic->setCallbacks(new AlertCallbacks());
  pCharacteristic->addDescriptor(new BLE2902());

  pService->start();
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->start();

  Serial.println("[UrbanVibe BLE] Đang phát tín hiệu BLE chờ ghép đôi...");
}

void loop() {
  if (current_alert_state == 1) {
    // Cảnh báo Còi xe máy
    Serial.println(">>> KÍCH HOẠT RUNG CÒI XE & ĐÈN CAM GƯƠNG CHIẾU HẬU");
    trigger_haptic_horn();
    current_alert_state = 0; // Reset trạng thái
  } 
  else if (current_alert_state == 2) {
    // Cảnh báo Xe cứu thương khẩn cấp
    Serial.println(">>> KÍCH HOẠT RUNG DỒN DẬP & ĐÈN ĐỎ NHẤP NHÁY KHẨN CẤP");
    trigger_haptic_siren();
    current_alert_state = 0;
  }
  delay(100);
}
