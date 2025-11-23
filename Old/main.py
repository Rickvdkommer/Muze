import torch
import sounddevice as sd
from transformers import AutoModelForCausalLM, AutoTokenizer
import time
import sys
import os
import requests
import json
import base64
import io
import torchaudio
import logging
from datetime import datetime
import numpy as np
from pathlib import Path

from models.sesame.generator import speak  # This is your wrapped generator function

# Setup logging with more detailed format
log_file = Path('csm_interactions.log')
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# Determine the device to use
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Using device: {device}")

# Load LLaMA model and tokenizer
llama_path = "/Users/rickvandenkommer/Muze/models/llama"  # Local path for the model
print(f"Debug - Loading model from: {llama_path}")

try:
    print("Debug - Loading local tokenizer")
    tokenizer = AutoTokenizer.from_pretrained(llama_path)
    print("Debug - Tokenizer loaded successfully")
    print(f"Debug - Tokenizer vocab size: {len(tokenizer)}")
    print(f"Debug - Tokenizer special tokens: {tokenizer.special_tokens_map}")
    
    print("Debug - Loading local model")
    model = AutoModelForCausalLM.from_pretrained(
        llama_path,
        torch_dtype=torch.float32,
        device_map="auto" if device == "mps" else None
    )
    print("Debug - Model loaded successfully")
    print(f"Debug - Model config: {model.config}")
    
    if device == "mps":
        print("Debug - Moving model to MPS device")
        model = model.to(device)
except Exception as e:
    print(f"Error loading model: {str(e)}")
    print("Please make sure all dependencies are installed and the model files are complete.")
    sys.exit(1)

# Initialize conversation history
conversation_history = []

def generate_text(prompt: str) -> str:
    try:
        print("\nDebug - Starting text generation...")
        print(f"Debug - Device: {device}")
        print(f"Debug - Model device: {next(model.parameters()).device}")
        print(f"Debug - Current conversation history length: {len(conversation_history)}")
        
        # Add the new user message to history
        conversation_history.append(f"<|user|>\n{prompt}")
        
        # Build the full prompt with conversation history
        full_prompt = f"""<|system|>
You are a helpful AI assistant. Provide clear, concise responses. Do not think out loud or describe your actions.
{" ".join(conversation_history)}
<|assistant|>"""
        
        print(f"Debug - Full prompt:\n{full_prompt}")
        
        # Tokenize and show token information
        inputs = tokenizer(full_prompt, return_tensors="pt").to(device)
        print(f"Debug - Input tensor shape: {inputs['input_ids'].shape}")
        print(f"Debug - Input tokens: {tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])}")
        
        # Generate response
        print("Debug - Generating response...")
        output = model.generate(
            **inputs,
            max_new_tokens=100,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.2  # Add repetition penalty to prevent loops
        )
        print(f"Debug - Output tensor shape: {output.shape}")
        print(f"Debug - Output tokens: {tokenizer.convert_ids_to_tokens(output[0])}")
        
        # Decode and clean up the response
        full_response = tokenizer.decode(output[0], skip_special_tokens=True)
        print(f"Debug - Full response before cleaning:\n{full_response}")
        
        # Extract just the assistant's response
        if "<|assistant|>" in full_response:
            response = full_response.split("<|assistant|>")[-1].strip()
            # Remove any trailing system or user markers
            response = response.split("<|")[0].strip()
            print(f"Debug - Found assistant marker, extracted response:\n{response}")
        else:
            print("Debug - No assistant marker found, using fallback extraction")
            # Try to find the last assistant response in the full response
            response = full_response[len(full_prompt):].strip()
            print(f"Debug - Fallback response:\n{response}")
        
        # Clean up the response
        response = response.replace("Here's my turn:", "").strip()
        response = response.replace("I'll assume", "").strip()
        response = response.replace("As a digital assistant,", "").strip()
        
        # Ensure we have a valid response
        if not response or len(response) < 2:
            print("Debug - Empty or too short response generated")
            return "I apologize, but I couldn't generate a proper response. Please try again."
        
        # Add the assistant's response to history
        conversation_history.append(f"<|assistant|>\n{response}")
        
        # Keep only the last 4 exchanges to prevent context from growing too large
        if len(conversation_history) > 8:  # 4 exchanges = 8 messages
            conversation_history = conversation_history[-8:]
            print("Debug - Trimmed conversation history to last 4 exchanges")
            
        print(f"Debug - Final cleaned response:\n{response}")
        print(f"Debug - Current conversation history:\n{conversation_history}")
        return response
    except Exception as e:
        print(f"Debug - Error in generate_text: {str(e)}")
        print(f"Debug - Error type: {type(e)}")
        import traceback
        print(f"Debug - Error traceback:\n{traceback.format_exc()}")
        return "I apologize, but I encountered an error while generating a response."

def play_audio_from_base64(audio_base64: str, sample_rate: int):
    # Decode base64 audio
    audio_bytes = base64.b64decode(audio_base64)
    buffer = io.BytesIO(audio_bytes)
    
    # Load audio using torchaudio
    audio_tensor, _ = torchaudio.load(buffer)
    audio_np = audio_tensor.squeeze().numpy()
    
    # Play audio
    sd.play(audio_np, samplerate=sample_rate)
    sd.wait()  # wait until playback is finished

def print_thinking():
    sys.stdout.write("🤔 Thinking")
    sys.stdout.flush()
    for _ in range(3):
        time.sleep(0.5)
        sys.stdout.write(".")
        sys.stdout.flush()
    print("\r" + " " * 20 + "\r", end="")  # Clear the thinking message

def print_speaking():
    sys.stdout.write("🗣️ Speaking")
    sys.stdout.flush()
    for _ in range(3):
        time.sleep(0.5)
        sys.stdout.write(".")
        sys.stdout.flush()
    print("\r" + " " * 20 + "\r", end="")  # Clear the speaking message

def analyze_audio_characteristics(audio_tensor, sample_rate):
    """Analyze audio characteristics to help identify voice properties"""
    # Convert to numpy for analysis
    audio_np = audio_tensor.squeeze().numpy()
    
    # Calculate basic audio statistics
    duration = len(audio_np) / sample_rate
    rms = np.sqrt(np.mean(np.square(audio_np)))
    zero_crossings = np.sum(np.diff(np.signbit(audio_np)))
    
    # Estimate pitch (basic implementation)
    autocorr = np.correlate(audio_np, audio_np, mode='full')
    autocorr = autocorr[len(autocorr)//2:]
    peaks = np.where(autocorr > 0.5 * np.max(autocorr))[0]
    if len(peaks) > 1:
        peak_diff = np.diff(peaks)
        estimated_pitch = sample_rate / np.median(peak_diff)
    else:
        estimated_pitch = 0
    
    return {
        'duration_seconds': duration,
        'rms_amplitude': float(rms),
        'zero_crossings': int(zero_crossings),
        'estimated_pitch_hz': float(estimated_pitch),
        'sample_rate': sample_rate,
        'audio_length_samples': len(audio_np)
    }

def log_interaction(text, response, audio_data=None, sample_rate=None, audio_length_ms=30_000, speaker_id=0):
    """Log the interaction details including comprehensive model and audio settings"""
    # Basic interaction data
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'input_text': text,
        'response': response,
        'model_settings': {
            'device': device,
            'speaker_id': speaker_id,
            'audio_length_ms': audio_length_ms,
            'model_name': 'CSM-1B',
            'model_version': '1.0',  # From repository
            'context_length': 0,  # Current context length
            'generation_parameters': {
                'temperature': 0.7,  # Default from repository
                'top_p': 0.9,  # Default from repository
                'max_new_tokens': 100  # Default from repository
            }
        }
    }
    
    # Add audio analysis if audio data is available
    if audio_data is not None and sample_rate is not None:
        try:
            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_data)
            buffer = io.BytesIO(audio_bytes)
            audio_tensor, _ = torchaudio.load(buffer)
            
            # Analyze audio characteristics
            audio_analysis = analyze_audio_characteristics(audio_tensor, sample_rate)
            log_entry['audio_analysis'] = audio_analysis
            
            # Add voice characteristics estimation
            log_entry['voice_characteristics'] = {
                'estimated_gender': 'female' if audio_analysis['estimated_pitch_hz'] > 200 else 'male',
                'speech_rate': audio_analysis['zero_crossings'] / audio_analysis['duration_seconds'],
                'volume_level': 'loud' if audio_analysis['rms_amplitude'] > 0.5 else 'normal' if audio_analysis['rms_amplitude'] > 0.2 else 'quiet'
            }
        except Exception as e:
            log_entry['audio_analysis_error'] = str(e)
    
    logging.info(json.dumps(log_entry))
    return log_entry

def view_logs(limit=10):
    """View the most recent logs"""
    if not log_file.exists():
        print("No log file found.")
        return
    
    print("\nRecent Interactions:")
    print("=" * 50)
    
    try:
        with open(log_file, 'r') as f:
            # Get the last 'limit' lines
            lines = f.readlines()[-limit:]
            
            for line in lines:
                try:
                    # Parse the log entry
                    timestamp, message = line.split(' - ', 1)
                    data = json.loads(message)
                    
                    print(f"\nTime: {timestamp.strip()}")
                    print(f"Input: {data['input_text']}")
                    print(f"Response: {data['response']}")
                    
                    if 'voice_characteristics' in data:
                        voice = data['voice_characteristics']
                        print(f"Voice: {voice['estimated_gender']}, {voice['volume_level']}")
                        print(f"Speech Rate: {voice['speech_rate']:.2f} crossings/second")
                    
                    print("-" * 50)
                except json.JSONDecodeError:
                    print(f"Could not parse log entry: {line.strip()}")
    except Exception as e:
        print(f"Error reading log file: {str(e)}")

def main():
    print("🤖 AI Chat Interface")
    print("Type your message and press Enter. Type 'exit' or 'quit' to end the chat.")
    print("Type 'logs' to view recent interactions.")
    print("=" * 50)
    
    # Get Colab URL from user
    colab_url = input("Please enter your Colab notebook URL (e.g., http://localhost:8888): ")
    if not colab_url:
        print("No Colab URL provided. Exiting...")
        return
    
    while True:
        try:
            # Get user input
            user_input = input("\nYou > ")
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye! 👋")
                break
            elif user_input.lower() == "logs":
                view_logs()
                continue

            # Generate response
            print_thinking()
            response = generate_text(user_input)
            
            # Only proceed if we have a valid response
            if response and response.strip():
                # Print the response first
                print(f"\nAI > {response}")
                
                # Then generate and play audio
                print_speaking()
                try:
                    # Send the response text to Colab for audio generation
                    audio_response = requests.post(
                        f"{colab_url}/generate_audio",
                        json={"text": response}  # Send the actual response text
                    )
                    if audio_response.status_code == 200:
                        data = audio_response.json()
                        play_audio_from_base64(data["audio"], data["sample_rate"])
                        # Log the successful interaction with audio data
                        log_entry = log_interaction(
                            user_input, 
                            response,  # Use the original text response
                            audio_data=data["audio"],
                            sample_rate=data["sample_rate"]
                        )
                        # Print voice characteristics
                        if 'voice_characteristics' in log_entry:
                            voice = log_entry['voice_characteristics']
                            print(f"\nVoice characteristics:")
                            print(f"- Estimated gender: {voice['estimated_gender']}")
                            print(f"- Speech rate: {voice['speech_rate']:.2f} crossings/second")
                            print(f"- Volume level: {voice['volume_level']}")
                    else:
                        print("Error generating audio from Colab")
                except Exception as e:
                    print(f"Error communicating with Colab: {str(e)}")
            else:
                print("\nAI > I apologize, but I couldn't generate a proper response. Please try again.")

        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
