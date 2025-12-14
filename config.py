import json
import os
from pathlib import Path


class Settings:
    def __init__(self):
        self.app_name = "SUB11"
        
        # Store all files in user's home directory
        config_dir = Path.home() / ".sub11"
        config_dir.mkdir(exist_ok=True)
        
        self.config_file = str(config_dir / "settings.json")
        self.audio_file = str(config_dir / "temp_audio.wav")
        self.ass_file = str(config_dir / "styled_subs.ass")
        self.srt_file = str(config_dir / "subs.srt")
        self.developer = "Aman Chatterjee"
        self.developer_email = "amanchatterjee121@gmail.com"
        self.huggingface_base_url = "https://huggingface.co/Systran/faster-whisper-{model_size}/resolve/main"
        
        # Available options
        self.model_size = ["tiny", "base", "small", "medium", "turbo", "large-v2", "large-v3"]
        self.device = ["cpu", "cuda", "auto"]
        self.compute_type = ["int8", "float16", "float32"]
        self.crf_values = ["18", "23", "28"]
        self.preset_values = ["ultrafast", "fast", "medium", "slow", "veryslow"]
        
        # Load saved preferences
        self.preferences = self.load_preferences()
        
        # Set config variables from preferences
        self.api_key = self.preferences.get('api_key', '')
        self.gemini_model = self.preferences.get('gemini_model', 'gemini-2.5-flash')
        self.selected_model_size = self.preferences.get('model_size', 'medium')
        self.selected_device = self.preferences.get('device', 'auto')
        self.selected_compute_type = self.preferences.get('compute_type', 'int8')
        self.selected_crf = self.preferences.get('crf', '23')
        self.selected_preset = self.preferences.get('preset', 'medium')
    
    def load_preferences(self):
        """Load preferences from JSON file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        # Default preferences
        return {
            'api_key': '',
            'gemini_model': 'gemini-2.5-flash',
            'model_size': 'medium',
            'device': 'auto',
            'compute_type': 'int8',
            'crf': '23',
            'preset': 'medium'
        }
    
    def save_preferences(self, preferences):
        """Save preferences to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(preferences, f, indent=4)
            self.preferences = preferences
            # Update config variables
            self.api_key = preferences.get('api_key', '')
            self.gemini_model = preferences.get('gemini_model', 'gemini-2.5-flash')
            self.selected_model_size = preferences.get('model_size', 'medium')
            self.selected_device = preferences.get('device', 'auto')
            self.selected_compute_type = preferences.get('compute_type', 'int8')
            self.selected_crf = preferences.get('crf', '23')
            self.selected_preset = preferences.get('preset', 'medium')
            return True
        except Exception as e:
            print(f"Error saving preferences: {e}")
            return False