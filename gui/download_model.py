import os
import time
import requests
from pathlib import Path
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from config import Settings


class DownloadThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, model_size, model_path):
        super().__init__()
        self.model_size = model_size
        self.model_path = model_path
        self.settings = Settings()
        self.start_time = None
        self.total_downloaded = 0
    
    def run(self):
        try:
            self.model_path.mkdir(parents=True, exist_ok=True)
            
            base_url = self.settings.huggingface_base_url.format(model_size=self.model_size)
            files = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
            
            self.start_time = time.time()
            
            for idx, file in enumerate(files):
                url = f"{base_url}/{file}"
                file_path = self.model_path / file
                
                self.status.emit(f"Downloading {file}...")
                
                response = requests.get(url, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            self.total_downloaded += len(chunk)
                            
                            if total_size > 0:
                                file_progress = (idx + downloaded / total_size) / len(files) * 100
                                self.progress.emit(int(file_progress))
                                
                                elapsed = time.time() - self.start_time
                                speed = self.total_downloaded / elapsed if elapsed > 0 else 0
                                speed_mb = speed / (1024 * 1024)
                                downloaded_mb = self.total_downloaded / (1024 * 1024)
                                
                                self.status.emit(f"Downloading {file}: {downloaded_mb:.1f} MB | {speed_mb:.2f} MB/s")
            
            self.progress.emit(100)
            self.status.emit("Download complete!")
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))


class ModelDownloadDialog(QDialog):
    def __init__(self, model_size, model_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloading Model")
        self.setModal(True)
        self.setFixedSize(450, 150)
        self.model_path = model_path
        
        # Approximate model sizes in MB
        model_sizes = {
            "tiny": "75 MB",
            "base": "145 MB",
            "small": "488 MB",
            "medium": "1.5 GB",
            "large-v2": "3.1 GB",
            "large-v3": "3.1 GB"
        }
        size_text = model_sizes.get(model_size, "Unknown size")
        
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel(f"Downloading Whisper Model: {model_size} (~{size_text})")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.title_label)
        
        self.status_label = QLabel("Initializing download...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        self.download_thread = DownloadThread(model_size, model_path)
        self.download_thread.progress.connect(self.progress_bar.setValue)
        self.download_thread.status.connect(self.status_label.setText)
        self.download_thread.finished.connect(self.accept)
        self.download_thread.error.connect(self.on_error)
        self.download_thread.start()
    
    def on_error(self, error_msg):
        self.status_label.setText(f"Error: {error_msg}")
        self.reject()
