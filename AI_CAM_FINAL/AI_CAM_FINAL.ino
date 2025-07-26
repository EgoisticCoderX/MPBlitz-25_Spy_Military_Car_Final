// Filename: esp32_detection_cam_final.ino

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// --- WiFi Configuration ---
const char* ssid = "your_wifi_ssid";      // <-- REPLACE WITH YOUR WIFI NAME
const char* password = "your_wifi_password"; // <-- REPLACE WITH YOUR WIFI PASSWORD
   
// --- Pin Definitions for AI-Thinker Model ---
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define LED_GPIO_NUM       4 // Onboard Flashlight
#define LEDC_FLASH_CHANNEL 1

WebServer server(80);
WebServer streamServer(81);

// --- CAMERA INITIALIZATION ---
bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM; config.pin_d1 = Y3_GPIO_NUM; config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM; config.pin_d4 = Y6_GPIO_NUM; config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM; config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_VGA; // 640x480
    config.jpeg_quality = 12;          // Lower number = higher quality
    config.fb_count = 2;               // Use 2 frame buffers for smoother stream with PSRAM
    
    if (esp_camera_init(&config) != ESP_OK) {
        Serial.println("Camera initialization failed");
        return false;
    }
    return true;
}

// --- WEB HANDLERS ---
void handleStream() {
    WiFiClient client = streamServer.client();
    if (client) {
        String response = "HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";
        client.print(response);
        while (client.connected()) {
            camera_fb_t *fb = esp_camera_fb_get();
            if (!fb) {
                Serial.println("Camera capture failed!");
                break;
            }
            client.print("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + String(fb->len) + "\r\n\r\n");
            client.write(fb->buf, fb->len);
            client.print("\r\n");
            esp_camera_fb_return(fb);

            // *** FLASHLIGHT TIMEOUT FIX ***
            // This small delay prevents the streaming loop from starving the main web server,
            // making the ESP32 responsive to /led commands from the backend.
            delay(1); 
        }
        client.stop();
    }
}

void handleLedControl() {
    if (server.hasArg("level")) {
        int level = server.arg("level").toInt();
        ledcWrite(LEDC_FLASH_CHANNEL, constrain(level, 0, 255));
        server.send(200, "text/plain", "OK");
    } else {
        server.send(400, "text/plain", "Missing 'level' parameter");
    }
}

void connectToWiFi() {
    Serial.print("Connecting to WiFi");
    WiFi.begin(ssid, password);
    for (int i = 0; i < 20 && WiFi.status() != WL_CONNECTED; i++) {
        delay(500); Serial.print(".");
    }
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("\nFATAL: WiFi failed! Restarting...");
        delay(3000); ESP.restart();
    }
    Serial.printf("\nWiFi Connected! IP Address: %s\n", WiFi.localIP().toString().c_str());
}


// --- SETUP AND MAIN LOOP ---
void setup() {
    Serial.begin(115200);
    Serial.println("\n\nBooting ESP32-CAM Detection System...");

    ledcSetup(LEDC_FLASH_CHANNEL, 5000, 8);
    ledcAttachPin(LED_GPIO_NUM, LEDC_FLASH_CHANNEL);
    ledcWrite(LEDC_FLASH_CHANNEL, 0);

    if (!initCamera()) {
        Serial.println("FATAL: Camera init failed! Restarting...");
        delay(3000);
        ESP.restart();
    }
    
    connectToWiFi();

    server.on("/led", HTTP_GET, handleLedControl);
    server.begin();

    streamServer.on("/stream", HTTP_GET, handleStream);
    streamServer.begin();
    
    Serial.println("System online and ready.");
}

void loop() {
    // If WiFi connection is lost, attempt to reconnect.
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi connection lost! Reconnecting...");
        connectToWiFi();
    }

    server.handleClient();
    streamServer.handleClient();
    delay(1);
}