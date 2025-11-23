# Install dependencies
!pip install torch torchaudio transformers huggingface_hub sounddevice numpy tokenizers flask flask-ngrok pyngrok

# Clone and setup CSM
!git clone https://github.com/SesameAILabs/csm.git
%cd csm
!pip install -r requirements.txt

# Disable lazy compilation in Mimi
import os
os.environ['NO_TORCH_COMPILE'] = '1'

# Get secrets from Colab
from google.colab import userdata
try:
    hf_token = userdata.get('HF_TOKEN')
    print("Successfully retrieved Hugging Face token from Colab secrets")
    
    ngrok_token = userdata.get('NGROK_TOKEN')
    print("Successfully retrieved ngrok token from Colab secrets")
except Exception as e:
    print("\nSecrets not found in Colab secrets.")
    print("Please add your tokens to Colab secrets:")
    print("1. Click on the key icon in the left sidebar")
    print("2. Click 'Add new secret'")
    print("3. Add these secrets:")
    print("   - Name: 'HF_TOKEN', Value: your Hugging Face token")
    print("   - Name: 'NGROK_TOKEN', Value: your ngrok token")
    print("4. Click 'Add' for each")
    print("\nThen restart this notebook.")
    raise

# Login to Hugging Face
from huggingface_hub import login
login(token=hf_token)  # Use the token directly

# Setup model
import torch
from generator import load_csm_1b

# Check CUDA availability
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

# Load the model
try:
    print("Loading model using built-in load_csm_1b function...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    generator = load_csm_1b(device=device)
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {str(e)}")
    print("Please make sure you have access to the model and all dependencies are installed.")
    raise

# Create a simple API endpoint
from flask import Flask, request, jsonify, Response
import torchaudio
import base64
import io
from pyngrok import ngrok

app = Flask(__name__)

# Configure ngrok
ngrok.set_auth_token(ngrok_token)  # Use the token from secrets
public_url = ngrok.connect(5000).public_url
print(f"\n * ngrok tunnel \"{public_url}\" -> http://127.0.0.1:5000")

@app.route('/generate_audio', methods=['POST'])
def generate_audio():
    data = request.json
    text = data.get('text', '')
    
    try:
        # Generate audio with longer max length
        audio = generator.generate(
            text=text,
            speaker=0,
            context=[],
            max_audio_length_ms=30_000,  # Increased to 30 seconds
        )
        
        # Convert to bytes
        buffer = io.BytesIO()
        torchaudio.save(buffer, audio.unsqueeze(0).cpu(), generator.sample_rate, format="wav")
        buffer.seek(0)
        
        # Return audio data directly
        return Response(
            buffer.getvalue(),
            mimetype='audio/wav',
            headers={
                'Content-Disposition': 'attachment; filename=audio.wav'
            }
        )
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

# Run the Flask app
if __name__ == '__main__':
    print("\nStarting Flask server...")
    print("When the server starts, you'll see an ngrok URL.")
    print("Copy that URL and use it in your local_chat.py script.")
    print("\nYou can also use the direct URL: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)