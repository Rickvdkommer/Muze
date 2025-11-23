import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import requests
import sounddevice as sd
import numpy as np
import io
import torchaudio
import os
import sys
from getpass import getpass

# Determine the device to use
device = "mps" if torch.backends.mps.is_available() else "cpu"
print(f"Using device: {device}")

# Get Hugging Face token
def get_hf_token():
    # Try to get token from environment variable
    token = os.getenv('HF_TOKEN')
    if not token:
        # If not found, prompt user
        print("\nHugging Face token not found in environment variables.")
        print("Please enter your Hugging Face token (it will not be displayed):")
        token = getpass()
    return token

# Load LLaMA model and tokenizer
llama_path = "models/llama"  # Local path for the model
if not os.path.exists(llama_path):
    print("Downloading LLaMA model...")
    # Using Llama-3.2-1B-Instruct model
    model_id = "meta-llama/Llama-3.2-1B-Instruct"
    try:
        # Get token and set it in environment
        hf_token = get_hf_token()
        os.environ['HF_TOKEN'] = hf_token
        
        tokenizer = AutoTokenizer.from_pretrained(
            model_id,
            token=hf_token
        )
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float32,
            device_map=None,  # Don't use device_map for local loading
            token=hf_token
        )
        # Move model to device after loading
        model = model.to(device)
        # Save the model locally
        model.save_pretrained(llama_path)
        tokenizer.save_pretrained(llama_path)
    except Exception as e:
        print(f"Error downloading model: {str(e)}")
        print("Please make sure you have access to the model and all dependencies are installed.")
        sys.exit(1)
else:
    print("Loading local model...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(llama_path)
        model = AutoModelForCausalLM.from_pretrained(
            llama_path,
            torch_dtype=torch.float32,
            device_map=None  # Don't use device_map for local loading
        )
        # Move model to device after loading
        model = model.to(device)
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        print("Please make sure all dependencies are installed and the model files are complete.")
        sys.exit(1)

def format_prompt(user_input: str) -> str:
    """Format the prompt for the Llama-3.2-1B-Instruct model."""
    return f"""<|system|>
You are a helpful AI assistant. You provide clear, concise, and accurate responses. Only respond to the user's input, do not continue the conversation or ask follow-up questions.
<|user|>
{user_input}
<|assistant|>"""

def generate_text(prompt: str) -> str:
    try:
        # Format the prompt for the model
        formatted_prompt = format_prompt(prompt)
        
        # Tokenize the input
        inputs = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        # Generate response
        output = model.generate(
            **inputs,
            max_new_tokens=200,  # Increased for more detailed responses
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.1,  # Reduce repetition
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,  # Ensure proper ending
            no_repeat_ngram_size=3  # Prevent repetitive phrases
        )
        
        # Decode and clean up the response
        response = tokenizer.decode(output[0], skip_special_tokens=True)
        
        # Extract only the assistant's response
        if "<|assistant|>" in response:
            response = response.split("<|assistant|>")[-1].strip()
            # Remove any additional user/assistant markers
            response = response.split("<|user|>")[0].strip()
            response = response.split("<|assistant|>")[0].strip()
        
        return response
    except Exception as e:
        print(f"Error generating text: {str(e)}")
        return "I apologize, but I encountered an error while generating a response."

def play_audio(audio_data: bytes):
    # Load audio using torchaudio
    buffer = io.BytesIO(audio_data)
    audio_tensor, sample_rate = torchaudio.load(buffer)
    audio_np = audio_tensor.squeeze().numpy()
    
    # Play audio
    sd.play(audio_np, samplerate=sample_rate)
    sd.wait()  # wait until playback is finished

def main():
    print("🤖 AI Chat Interface")
    print("Type your message and press Enter. Type 'exit' or 'quit' to end the chat.")
    print("=" * 50)
    
    # Get Colab URL from user
    colab_url = input("Please enter your Colab notebook URL (e.g., https://df12-35-198-242-173.ngrok-free.app): ")
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

            # Generate response
            print("🤔 Thinking...")
            response = generate_text(user_input)
            print(f"\nAI > {response}")

            # Send to Colab for audio generation
            print("🗣️ Speaking...")
            try:
                response = requests.post(
                    f"{colab_url}/generate_audio",
                    json={"text": response},
                    stream=True  # Stream the response
                )
                if response.status_code == 200:
                    # Get audio data and play it
                    audio_data = response.content
                    play_audio(audio_data)
                else:
                    print("Error generating audio from Colab")
            except Exception as e:
                print(f"Error communicating with Colab: {str(e)}")

        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 