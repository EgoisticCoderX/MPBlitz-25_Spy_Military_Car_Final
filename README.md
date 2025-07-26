Make a static folder and inside it a captures folder : this folder will save all the images captured by python script whenever the AI models detect any military element
captures.html : shows the captures taken by python script and saves it in captures folder
live_stream.html : flask frontend, shows the live footage of esp32 cam and shows the output of the model detection with pause for confirmation
cam.py : python script, and if the models are doing rubbish detection increase the conf (confidence) threshhold in the script itself
Make a .env file with the following contents: 
# --- Environment Configuration for Military Detection System ---

# Your secret key from your Roboflow account's workspace settings
ROBOFLOW_API_KEY=45h9MkXXrNHs7SuvoFwD

# The full URL of your ESP32-CAM.
# The Flask server will get the stream from here.
ESP32_CAM_URL=http://192.168.137.210


Note: Flashlight is not working
