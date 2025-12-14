import os
import sys
import shutil
import subprocess
from config import Settings

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


class Exporter:
    def __init__(self):
        self.settings = Settings()
    
    def export_video(self, video_path, output_path):
        """
        Export video with burned-in ASS subtitles using FFmpeg.
        
        Args:
            video_path: Path to the input video
            output_path: Path to save the output video
        
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(self.settings.ass_file):
            return False
        
        # Check if input is audio file
        audio_extensions = ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg')
        is_audio = video_path.lower().endswith(audio_extensions)
        
        if is_audio:
            # Create video with black background and subtitles for audio files
            command = [
                get_ffmpeg_path(), "-f", "lavfi", "-i", "color=c=black:s=1920x1080",
                "-i", video_path,
                "-vf", f"ass={self.settings.ass_file}",
                "-c:v", "libx264",
                "-crf", self.settings.selected_crf,
                "-preset", self.settings.selected_preset,
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                output_path, "-y",
                "-hide_banner", "-loglevel", "error"
            ]
        else:
            # Standard video with subtitles
            command = [
                get_ffmpeg_path(), "-i", video_path,
                "-vf", f"ass={self.settings.ass_file}",
                "-c:v", "libx264",
                "-crf", self.settings.selected_crf,
                "-preset", self.settings.selected_preset,
                "-c:a", "copy",
                output_path, "-y",
                "-hide_banner", "-loglevel", "error"
            ]
        
        try:
            subprocess.run(command, check=True)
            print(f"✅ Video exported to {output_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Error exporting video: {str(e)}")
            return False
    
    def export_srt(self, output_path):
        """
        Export SRT file to specified path.
        
        Args:
            output_path: Path to save the SRT file
        
        Returns:
            True if successful, False otherwise
        """
        if os.path.exists(self.settings.srt_file):
            shutil.copy(self.settings.srt_file, output_path)
            return True
        return False
    
    def export_ass(self, output_path):
        """
        Export ASS file to specified path.
        
        Args:
            output_path: Path to save the ASS file
        
        Returns:
            True if successful, False otherwise
        """
        if os.path.exists(self.settings.ass_file):
            shutil.copy(self.settings.ass_file, output_path)
            return True
        return False
