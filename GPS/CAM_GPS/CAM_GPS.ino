#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

// Camera model selection - Ensure you have the correct model uncommented
#define CAMERA_MODEL_AI_THINKER // Has PSRAM
// #define CAMERA_MODEL_WROVER_KIT
// #define CAMERA_MODEL_ESP_EYE
// #define CAMERA_MODEL_M5STACK_PSRAM
// #define CAMERA_MODEL_M5STACK_WIDE

#include "camera_pins.h"

// WiFi credentials
const char* ssid = "MySpyCar";       // Your WiFi network name
const char* password = "123456789";  // Your WiFi network password

// Web servers for different functions
WebServer controlServer(80);    // Pan/Tilt control
WebServer streamServer(81);     // Video stream
WebServer flashServer(82);      // Flashlight control

// Servo objects
Servo panServo;
Servo tiltServo;

// GPIO pins and settings
#define PAN_SERVO_PIN 14
#define TILT_SERVO_PIN 15
#define FLASHLIGHT_PIN 4
#define LEDC_CHANNEL_FLASH 1 // Use channel 1 for flashlight to avoid conflict with camera's channel 0

// Current positions
int currentPan = 90;
int currentTilt = 90;
int currentFlash = 0;

// --- Function Declarations ---
bool initCamera();
void initServos();
void initFlashlight();
void connectWiFi();
void setupControlServer();
void setupStreamServer();
void setupFlashServer();
void streamJpg();

// --- Main Setup ---
void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();
  Serial.println("🚀 Starting ESP32 Surveillance System...");

  // Initialize camera
  if (!initCamera()) {
    Serial.println("❌ Camera initialization failed! Halting.");
    return;
  }

  // Initialize servos
  initServos();

  // Initialize flashlight
  initFlashlight();

  // Connect to WiFi
  connectWiFi();

  // If WiFi is connected, start servers
  if (WiFi.status() == WL_CONNECTED) {
    // Setup web servers
    setupControlServer();
    setupStreamServer();
    setupFlashServer();

    // Start all servers
    controlServer.begin();
    streamServer.begin();
    flashServer.begin();

    Serial.println("\n✅ All servers started!");
    Serial.print("📡 Control Server: http://");
    Serial.print(WiFi.localIP());
    Serial.println(":80");
    Serial.print("📹 Stream Server:  http://");
    Serial.print(WiFi.localIP());
    Serial.println(":81/stream");
    Serial.print("💡 Flash Server:   http://");
    Serial.print(WiFi.localIP());
    Serial.println(":82");
  } else {
    Serial.println("❌ WiFi connection failed. Servers not started.");
  }
}

// --- Main Loop ---
void loop() {
  // Handle HTTP client requests
  controlServer.handleClient();
  streamServer.handleClient();
  flashServer.handleClient();
  delay(1); // Allow other tasks to run
}

// --- Initializations ---

bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_VGA;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12; // Lower number = higher quality
  config.fb_count = 1;

  // If PSRAM is available, use a larger buffer
  if(psramFound()){
    Serial.println("✅ PSRAM found. Using optimized settings.");
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    Serial.println("⚠️ No PSRAM found. Frame size may be limited.");
    config.frame_size = FRAMESIZE_SVGA;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  // Initialize camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("❌ Camera init failed with error 0x%x\n", err);
    return false;
  }

  sensor_t * s = esp_camera_sensor_get();
  // Optional settings: flip, brightness, etc.
  s->set_vflip(s, 0); // 0 = false, 1 = true
  s->set_hmirror(s, 0);
  s->set_brightness(s, 1);
  s->set_saturation(s, 0);
  s->set_framesize(s, FRAMESIZE_VGA);

  Serial.println("✅ Camera initialized successfully.");
  return true;
}

void initServos() {
  panServo.attach(PAN_SERVO_PIN);
  tiltServo.attach(TILT_SERVO_PIN);
  panServo.write(currentPan);
  tiltServo.write(currentTilt);
  Serial.println("✅ Servos initialized and centered.");
}

void initFlashlight() {
  // Setup LEDC to control brightness
  ledcSetup(LEDC_CHANNEL_FLASH, 5000, 8); // Channel, 5kHz frequency, 8-bit resolution
  ledcAttachPin(FLASHLIGHT_PIN, LEDC_CHANNEL_FLASH);
  ledcWrite(LEDC_CHANNEL_FLASH, 0); // Start with flash off
  Serial.println("✅ Flashlight initialized.");
}

void connectWiFi() {
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);
  Serial.print("🔌 Connecting to WiFi");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected!");
    Serial.print("📍 IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ WiFi connection failed!");
  }
}

// --- Server Setups ---

void setupControlServer() {
  // Pan control endpoint
  controlServer.on("/pan", HTTP_GET, []() {
    if (controlServer.hasArg("angle")) {
      int angle = controlServer.arg("angle").toInt();
      angle = constrain(angle, 0, 180); // Safety constraint
      currentPan = angle;
      panServo.write(angle);
      Serial.printf("🔄 Pan set to: %d°\n", angle);
      controlServer.send(200, "application/json", "{\"status\":\"success\",\"pan\":" + String(angle) + "}");
    } else {
      controlServer.send(400, "application/json", "{\"error\":\"missing angle parameter\"}");
    }
  });

  // Tilt control endpoint
  controlServer.on("/tilt", HTTP_GET, []() {
    if (controlServer.hasArg("angle")) {
      int angle = controlServer.arg("angle").toInt();
      angle = constrain(angle, 0, 180); // Safety constraint
      currentTilt = angle;
      tiltServo.write(angle);
      Serial.printf("🔄 Tilt set to: %d°\n", angle);
      controlServer.send(200, "application/json", "{\"status\":\"success\",\"tilt\":" + String(angle) + "}");
    } else {
      controlServer.send(400, "application/json", "{\"error\":\"missing angle parameter\"}");
    }
  });

  // Main status endpoint
  controlServer.on("/status", HTTP_GET, []() {
    String json = "{";
    json += "\"pan\":" + String(currentPan) + ",";
    json += "\"tilt\":" + String(currentTilt) + ",";
    json += "\"flash\":" + String(currentFlash);
    json += "}";
    controlServer.send(200, "application/json", json);
  });
  
  controlServer.onNotFound([]() {
    controlServer.send(404, "text/plain", "Not found");
  });
}

/**
 * @brief This is the completed video streaming function.
 * It properly handles the MJPEG format.
 */
void setupStreamServer() {
  streamServer.on("/stream", HTTP_GET, []() {
    WiFiClient client = streamServer.client();
    String boundary = "frame";
    
    // Set headers for MJPEG stream
    client.print("HTTP/1.1 200 OK\r\n");
    client.print("Content-Type: multipart/x-mixed-replace; boundary=");
    client.print(boundary);
    client.print("\r\n\r\n");

    Serial.println("📹 Stream client connected.");

    while (client.connected()) {
      camera_fb_t * fb = esp_camera_fb_get();
      if (!fb) {
        Serial.println("⚠️ Camera capture failed.");
        // We could break here, but let's try to recover
        delay(100);
        continue;
      }

      // Send the frame part
      client.print("--");
      client.print(boundary);
      client.print("\r\n");
      client.print("Content-Type: image/jpeg\r\n");
      client.printf("Content-Length: %u\r\n\r\n", fb->len);
      client.write(fb->buf, fb->len);
      client.print("\r\n");
      
      // IMPORTANT: Release the frame buffer
      esp_camera_fb_return(fb);
      
      // A small delay can help prevent watchdog timer resets on some boards
      delay(10); 
    }
    Serial.println("❌ Stream client disconnected.");
  });
}

/**
 * @brief This is the new function to handle flashlight controls.
 * It uses LEDC to set brightness from 0 to 255.
 */
void setupFlashServer() {
  flashServer.on("/flashlight", HTTP_GET, []() {
    if (flashServer.hasArg("intensity")) {
      int intensity = flashServer.arg("intensity").toInt();
      intensity = constrain(intensity, 0, 255); // Safety clamp
      currentFlash = intensity;
      ledcWrite(LEDC_CHANNEL_FLASH, intensity);
      Serial.printf("💡 Flash intensity set to: %d\n", intensity);
      flashServer.send(200, "application/json", "{\"status\":\"success\",\"flash\":" + String(intensity) + "}");
    } else {
      flashServer.send(400, "application/json", "{\"error\":\"missing intensity parameter\"}");
    }
  });

  flashServer.onNotFound([]() {
    flashServer.send(404, "text/plain", "Not found");
  });
}
