import os
import sys
import math
import subprocess
from pathlib import Path
from faster_whisper import WhisperModel
from config import Settings
from business.gemini_processor import translate_text_list

def get_ffmpeg_path():
    """Get FFmpeg path for bundled or system installation"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        ffmpeg = os.path.join(sys._MEIPASS, 'ffmpeg_bin', 'ffmpeg')
        if os.path.exists(ffmpeg):
            return ffmpeg
    return 'ffmpeg'

def get_ffprobe_path():
    """Get FFprobe path for bundled or system installation"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        ffprobe = os.path.join(sys._MEIPASS, 'ffmpeg_bin', 'ffprobe')
        if os.path.exists(ffprobe):
            return ffprobe
    return 'ffprobe'

class Transcriber:
    def __init__(self, status_callback=None, progress_callback=None, indeterminate_callback=None):
        self.segment_data = []
        self.progress = 0
        self.settings = Settings()
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.indeterminate_callback = indeterminate_callback

    def extract_audio(self, video_path, audio_output_path):
        """
        Extracts audio from video using FFmpeg (System call)
        """
        # Check if input is already an audio file
        audio_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg')
        if video_path.lower().endswith(audio_extensions):
            print(f"🎵 Audio file detected, skipping extraction...")
            if self.status_callback:
                self.status_callback("Audio file detected")
            return video_path
        
        if os.path.exists(audio_output_path):
            os.remove(audio_output_path)
        
        print(f"🎵 Extracting audio from {video_path}...")
        if self.status_callback:
            self.status_callback("Extracting audio...")
        if self.indeterminate_callback:
            self.indeterminate_callback(True)
        
        # Check if video has audio stream
        check_command = [
            get_ffprobe_path(), "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        
        try:
            result = subprocess.run(check_command, capture_output=True, text=True)
            if not result.stdout.strip():
                error_msg = "Video has no audio stream"
                print(f"❌ {error_msg}")
                if self.status_callback:
                    self.status_callback(error_msg)
                if self.indeterminate_callback:
                    self.indeterminate_callback(False)
                raise Exception(error_msg)
        except subprocess.CalledProcessError:
            error_msg = "Failed to check audio stream"
            print(f"❌ {error_msg}")
            if self.status_callback:
                self.status_callback(error_msg)
            if self.indeterminate_callback:
                self.indeterminate_callback(False)
            raise Exception(error_msg)
        
        # ffmpeg command: -i (input) -vn (no video) -acodec pcm_s16le (wav format) -ar 16000 (16khz)
        command = [
            get_ffmpeg_path(), "-i", video_path, 
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", 
            audio_output_path, "-y", "-hide_banner", "-loglevel", "error"
        ]
        
        try:
            subprocess.run(command, check=True)
            print("✅ Audio extracted successfully.")
            if self.indeterminate_callback:
                self.indeterminate_callback(False)
            return audio_output_path
        except subprocess.CalledProcessError as e:
            error_msg = f"Error extracting audio: {str(e)}"
            print(f"❌ {error_msg}")
            if self.status_callback:
                self.status_callback(error_msg)
            if self.indeterminate_callback:
                self.indeterminate_callback(False)
            raise

    
    def transcribe_audio(self, audio_path):
        """
        Transcribe audio using Whisper model.
        """
        try:
            model_size = self.settings.selected_model_size
            device = self.settings.selected_device
            compute_type = self.settings.selected_compute_type
            
            # Use home directory for models in packaged app
            if getattr(sys, 'frozen', False):
                models_dir = Path.home() / ".sub11" / "models"
            else:
                current_script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_script_dir)
                models_dir = Path(project_root) / "models"
            
            model_path = str(models_dir / model_size)
            
            if not os.path.exists(model_path):
                raise Exception(f"Model not found at {model_path}. Please download it first.")
            
            print(f"🧠 Loading Whisper model ({model_size}) on {device} with {compute_type}...")
            if self.status_callback:
                self.status_callback("Loading model...")
            if self.indeterminate_callback:
                self.indeterminate_callback(True)
            
            model = WhisperModel(model_path, device=device, compute_type=compute_type)
        except Exception as e:
            error_msg = f"Error loading model: {str(e)}"
            print(f"❌ {error_msg}")
            if self.status_callback:
                self.status_callback(error_msg)
            if self.indeterminate_callback:
                self.indeterminate_callback(False)
            raise
        
        segments, info = model.transcribe(audio_path, beam_size=5, word_timestamps=True)
        total_duration = info.duration
        print(f"Detected language: {info.language} with probability {info.language_probability}")

        if self.indeterminate_callback:
            self.indeterminate_callback(False)
        if self.status_callback:
            self.status_callback("Transcribing audio...")
        if self.progress_callback:
            self.progress_callback(0)

        for segment in segments: 
            if total_duration > 0:
                self.progress = (segment.end / total_duration) * 100
                if self.progress_callback:
                    self.progress_callback(int(self.progress))
                if self.status_callback:
                    self.status_callback("Transcribing audio {:.1f}%".format(self.progress))

            print(f"Progress: {self.progress:.1f}% | Found: {segment.text}")
            
            # Store for SRT generator
            self.segment_data.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text,
                'words': list(segment.words) if hasattr(segment, 'words') else []
            })


    def split_translated_segments(self, segments, char_limit):
        """
        Splits segments using math instead of old timestamps.
        This PREVENTS overlapping subtitles.
        """
        if char_limit <= 0:
            return segments
            
        new_segments = []
        
        for segment in segments:
            text = segment['text'].strip()
            start = segment['start']
            end = segment['end']
            duration = end - start
            
            if not text:
                continue

            # 1. Break text into chunks based on character limit
            words_in_text = text.split()
            chunks = []
            current_chunk = []
            current_len = 0
            
            for word in words_in_text:
                # +1 is for the space character
                word_len = len(word)
                if current_len + word_len + 1 > char_limit and current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_len = 0
                
                current_chunk.append(word)
                current_len += word_len + 1
            
            if current_chunk:
                chunks.append(" ".join(current_chunk))

            # 2. Distribute time evenly (Linear Interpolation)
            # This ensures NO overlapping timestamps
            total_chars = len(text.replace(" ", "")) 
            current_time = start
            
            for chunk in chunks:
                chunk_chars = len(chunk.replace(" ", ""))
                
                # Calculate duration based on character count ratio
                if total_chars > 0:
                    ratio = chunk_chars / total_chars
                    chunk_duration = duration * ratio
                else:
                    chunk_duration = duration / len(chunks)
                
                new_segments.append({
                    'start': current_time,
                    'end': current_time + chunk_duration,
                    'text': chunk,
                    'words': [] # Clear old words to prevent confusion
                })
                # Advance time forward so the next subtitle starts exactly when this one ends
                current_time += chunk_duration
                
        return new_segments
    
    def time_to_ass_format(self, seconds):
        """Converts seconds to ASS time format (H:MM:SS.cs)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds_remainder = seconds % 60
        return f"{hours}:{minutes:02d}:{seconds_remainder:05.2f}"
    
    def time_to_srt_format(self, seconds):
        """Converts seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    

    def generate_ass(self, segments, output_filename, style_config):
        """
        Generates an .ass file with custom styling from style_config.
        """
        font = style_config['font'].family()
        font_size = style_config['font'].pointSize()
        font_color = style_config['font_color']
        border_color = style_config['border_color']
        border_radius = style_config['border_radius']
        
        # ASS COLOR FORMAT: &HAABBGGRR (Alpha, Blue, Green, Red) - Hex in reverse order!
        # Alpha: 00=opaque, FF=transparent
        def to_ass_color(color):
            alpha = 255 - color.alpha()  # Invert: 0 becomes 255 (transparent), 255 becomes 0 (opaque)
            return f"&H{alpha:02X}{color.blue():02X}{color.green():02X}{color.red():02X}"
        
        primary_color = to_ass_color(font_color)
        outline_color = to_ass_color(border_color)
        
        # BorderStyle: 1=shadow box
        border_style = 1
        outline = border_radius // 5 if border_radius > 0 else 0
        box_padding = border_radius // 5 if border_radius > 0 else 0
        
        print(f"ASS Style Debug:")
        print(f"  Font: {font} {font_size}")
        print(f"  Primary Color: {primary_color} (RGBA: {font_color.red()}, {font_color.green()}, {font_color.blue()}, {font_color.alpha()})")
        print(f"  Border Color: {outline_color} (RGBA: {border_color.red()}, {border_color.green()}, {border_color.blue()}, {border_color.alpha()})")
        print(f"  BorderStyle: {border_style}, Outline: {outline}")
        
        header = f"""[Script Info]
Title: Custom Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{font_size},{primary_color},&H000000FF,{outline_color},&H00000000,0,0,0,0,100,100,0,0,{border_style},{box_padding},0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(header)

            if self.status_callback:
                self.status_callback("Generating styled subtitles...")
            if self.indeterminate_callback:
                self.indeterminate_callback(True)
            
            for i, segment in enumerate(segments):
                start = self.time_to_ass_format(segment['start'])
                end = self.time_to_ass_format(segment['end'])
                text = segment['text'].strip().replace("\n", "\\N") # Handle line breaks
                
                # Debug: Print first few segments to verify translation
                if i < 3:
                    print(f"🔍 ASS Debug [{i}]: '{text}'")
                
                # Write the dialogue line
                f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")
        
        if self.indeterminate_callback:
            self.indeterminate_callback(False)
        print(f"🎨 ASS file saved to: {output_filename}")
    
    def generate_srt(self, segments, output_filename):
        """Generates an .srt file from segments."""
        with open(output_filename, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start = self.time_to_srt_format(segment['start'])
                end = self.time_to_srt_format(segment['end'])
                text = segment['text'].strip()
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
        print(f"🎨 SRT file saved to: {output_filename}")
    
    
    def translate_segments(self, target_language):
        """Translates segment text using Gemini."""
        if not self.settings.api_key:
            return
        
        try:
            # Extract just the text
            text_list = [seg['text'] for seg in self.segment_data]
            
            # Translate with Gemini
            translated_list = translate_text_list(
                text_list,
                target_language,
                self.settings.api_key,
                self.settings.gemini_model,
                self.status_callback,
                self.indeterminate_callback
            )
            
            # Update segments with translated text
            for i, translated_text in enumerate(translated_list):
                if i < len(self.segment_data):
                    self.segment_data[i]['text'] = translated_text
            
            print("✅ Translation completed")
        except Exception as e:
            error_msg = f"Translation failed: {str(e)}"
            print(f"⚠️ {error_msg}")
            if self.status_callback:
                self.status_callback(f"⚠️ {error_msg} (using original text)")
    

    def transcribe(self, video_path, style_config, target_language, char_limit=0):
        """
        Transcribe video and translate to target language.
        
        Args:
            video_path: Path to the video file
            style_config: Dictionary with font, colors, and border radius settings
            target_language: Target language for translation
            char_limit: Character limit per subtitle (0 = auto/full sentence)
        """
        try:
            # Step 1: Extract audio from video (or use audio file directly)
            audio_path = self.extract_audio(video_path, self.settings.audio_file) or self.settings.audio_file
            
            # Step 2: Transcribe audio using Whisper
            self.transcribe_audio(audio_path)
            
            # Step 3: Translate with Gemini first (before splitting for better context)
            self.translate_segments(target_language)
            
            # Step 4: Split segments by character limit if configured
            if char_limit > 0:
                self.segment_data = self.split_translated_segments(self.segment_data, char_limit)
            
            # Step 5: Generate both ASS and SRT files
            self.generate_ass(self.segment_data, self.settings.ass_file, style_config)
            self.generate_srt(self.segment_data, self.settings.srt_file)
            
            # Final success message
            if self.status_callback:
                self.status_callback("✅ Transcription completed!")
            print("✅ Transcription completed!")

        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            print(f"❌ {error_msg}")
            if self.status_callback:
                self.status_callback(error_msg)
            if self.indeterminate_callback:
                self.indeterminate_callback(False)
            
    
