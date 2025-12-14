import os
from config import Settings
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QPushButton, 
                             QLabel, QFileDialog, QComboBox, QColorDialog, 
                             QFontDialog, QHBoxLayout, QToolBar, QSizePolicy, QProgressBar, QSlider, QDialog)
from PyQt6.QtGui import QFont, QColor, QAction, QPainter, QPen, QPainterPath, QPixmap, QIcon
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QRectF
from business.transcriber import Transcriber
from business.file_exporter import Exporter
from gui.settings_window import SettingsWindow
from gui.download_model import ModelDownloadDialog


class OutlineLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.outline_color = QColor(0, 0, 0, 0)
        self.outline_width = 0
        self.text_color = QColor(255, 255, 255)
    
    def set_outline(self, color, width):
        self.outline_color = color
        self.outline_width = width
        self.update()
    
    def set_text_color(self, color):
        self.text_color = color
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create text path
        path = QPainterPath()
        path.addText(self.rect().center().x() - self.fontMetrics().horizontalAdvance(self.text()) / 2,
                     self.rect().center().y() + self.fontMetrics().height() / 4,
                     self.font(), self.text())
        
        # Draw outline
        if self.outline_width > 0:
            pen = QPen(self.outline_color, self.outline_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.strokePath(path, pen)
        
        # Draw text fill
        painter.fillPath(path, self.text_color)
        painter.end()


class TranscribeThread(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    indeterminate = pyqtSignal(bool)
    
    def __init__(self, video_path, style_config, language, char_limit=0):
        super().__init__()
        self.video_path = video_path
        self.style_config = style_config
        self.language = language
        self.char_limit = char_limit
    
    def run(self):
        transcriber = Transcriber(
            status_callback=self.update_status,
            progress_callback=self.update_progress,
            indeterminate_callback=self.update_indeterminate
        )
        transcriber.transcribe(self.video_path, self.style_config, self.language, self.char_limit)
        self.finished.emit()
    
    def update_progress(self, value):
        self.progress.emit(value)

    def update_status(self, message):
        self.status.emit(message)
    
    def update_indeterminate(self, is_indeterminate):
        self.indeterminate.emit(is_indeterminate)


class ExportThread(QThread):
    finished = pyqtSignal()
    
    def __init__(self, exporter, video_path, output_path):
        super().__init__()
        self.exporter = exporter
        self.video_path = video_path
        self.output_path = output_path
    
    def run(self):
        self.exporter.export_video(self.video_path, self.output_path)
        self.finished.emit()


class Sub11Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setting = Settings()
        self.video_path = ""
        self.last_export_path = ""
        self.font = QFont("Arial", 24)
        self.font_color = QColor(255, 255, 255)
        self.border_color = QColor(255, 165, 0)
        self.border_radius = 8
        
        self.transcriber = Transcriber()
        self.exporter = Exporter()
        self.transcribe_thread = None
        self.export_thread = None
        
        self.setWindowTitle(self.setting.app_name)
        self.setGeometry(100, 100, 600, 400)
        self.setup_toolbar()
        self.setup_ui()
    
    def setup_toolbar(self):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(30, 30))
        toolbar.setStyleSheet("QToolBar { padding: 8px; background-color: #4877e2; } QLabel { color: white; }")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        
        # App icon
        import sys
        if getattr(sys, 'frozen', False):
            # Running in bundled app
            icon_path = os.path.join(sys._MEIPASS, "icon.icns")
        else:
            # Running in development
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon.icns")
        
        if os.path.exists(icon_path):
            icon_label = QLabel()
            pixmap = QPixmap(icon_path).scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pixmap)
            icon_label.setStyleSheet("padding-left: 10px;")
            toolbar.addWidget(icon_label)
        
        toolbar.addSeparator()
        
        # Model info labels in vertical layout
        model_widget = QWidget()
        model_layout = QVBoxLayout(model_widget)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(2)
        
        self.whisper_label = QLabel(f"Whisper: {self.setting.selected_model_size}")
        self.whisper_label.setStyleSheet("padding: 2px; color: white;")
        model_layout.addWidget(self.whisper_label)
        
        self.gemini_label = QLabel(f"Gemini: {self.setting.gemini_model}")
        self.gemini_label.setStyleSheet("padding: 2px; color: white;")
        model_layout.addWidget(self.gemini_label)
        
        toolbar.addWidget(model_widget)
        toolbar.addSeparator()
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        
        # Settings button with icon
        settings_action = QAction("⚙️ Settings", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)
        
        toolbar.addSeparator()
        
        # About button with icon
        about_action = QAction("ℹ️ About", self)
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)
    
    def open_settings(self):
        settings_dialog = SettingsWindow(self)
        if settings_dialog.exec():
            settings = settings_dialog.get_settings()
            self.setting = Settings()
            self.whisper_label.setText(f"Whisper: {self.setting.selected_model_size}")
            self.gemini_label.setText(f"Gemini: {self.setting.gemini_model}")
            self.status_label.setText("Settings saved successfully")
    
    def show_about(self):
        from PyQt6.QtWidgets import QMessageBox
        about_text = f"""
<h2>{self.setting.app_name}</h2>
<p><b>Video Subtitle Generator</b></p>
<p>Version 1.0</p>
<br>
<p>Features:</p>
<ul>
<li> AI-powered transcription using Whisper</li>
<li> Translation with Google Gemini</li>
<li> Custom subtitle styling</li>
<li> Export to SRT or burn into video</li>
</ul>
<br>
<p>Powered by FFmpeg, Whisper, and Gemini AI</p>
<br>
<p><b>Developer:</b> {self.setting.developer}</p>
<p><b>Email:</b> {self.setting.developer_email}</p>
        """
        QMessageBox.about(self, "About", about_text)
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Video/Audio file selection
        self.video_label = QLabel("No file selected")
        browse_btn = QPushButton("Browse Audio/Video")
        browse_btn.setStyleSheet("background-color: #3478f6; color: white; padding: 8px; font-weight: bold; margin-bottom: 15px;")
        browse_btn.clicked.connect(self.browse_video)
        layout.addWidget(self.video_label)
        layout.addWidget(browse_btn)
        
        # Box row
        box_layout = QHBoxLayout()
        box_layout.setContentsMargins(0, 10, 0, 10)

        # language selection layout
        language_layout = QVBoxLayout()
        language_layout.addWidget(QLabel("Transcribe to:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Hindi", "Hinglish", "Tamil", "Telgu", "Marathi", "Bengali", "Kannada"])
        language_layout.addWidget(self.lang_combo)

        # characters per subtitle layout
        chars_layout = QVBoxLayout()
        chars_layout.addWidget(QLabel("Characters per subtitle:"))
        self.chars_combo = QComboBox()
        self.chars_combo.addItems(["Auto (Full sentence)", "5 chars", "10 chars", "15 chars", "20 chars", "30 chars"])
        chars_layout.addWidget(self.chars_combo)

        box_layout.addLayout(language_layout, 1)
        box_layout.addLayout(chars_layout, 1)
        layout.addLayout(box_layout)
        
        # Style customization buttons
        style_layout = QHBoxLayout()
        font_btn = QPushButton("Select Font")
        font_btn.clicked.connect(self.select_font)
        font_color_btn = QPushButton("Font Color")
        font_color_btn.clicked.connect(self.select_font_color)
        border_color_btn = QPushButton("Border Color")
        border_color_btn.clicked.connect(self.select_border_color)
        style_layout.addWidget(font_btn)
        style_layout.addWidget(font_color_btn)
        style_layout.addWidget(border_color_btn)
        layout.addLayout(style_layout)
        
        # Border radius
        radius_layout = QHBoxLayout()
        radius_layout.addWidget(QLabel("Border Radius:"))
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setMinimum(0)
        self.radius_slider.setMaximum(50)
        self.radius_slider.setValue(self.border_radius)
        self.radius_slider.valueChanged.connect(self.on_radius_changed)
        radius_layout.addWidget(self.radius_slider)
        
        self.radius_label = QLabel("12px")
        self.radius_label.setMinimumWidth(40)
        radius_layout.addWidget(self.radius_label)
        layout.addLayout(radius_layout)
        
        # Unified preview
        self.style_preview = OutlineLabel(self.font.family())
        self.style_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.style_preview.setMinimumHeight(100)
        self.update_style_preview()
        layout.addWidget(self.style_preview)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        self.transcribe_btn = QPushButton("Transcribe")
        self.transcribe_btn.clicked.connect(self.transcribe)
        self.preview_btn = QPushButton("Preview/Edit")
        self.preview_btn.clicked.connect(self.preview_subtitles)
        self.preview_btn.setEnabled(False)
        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_video)
        self.export_btn.setEnabled(False)
        btn_layout.addWidget(self.transcribe_btn)
        btn_layout.addWidget(self.preview_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)
        
        # Bottom status area with Open Output Folder button
        bottom_layout = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #559131;")
        bottom_layout.addWidget(self.status_label)
        
        # Spacer to push button to right
        bottom_layout.addStretch()
        
        # Open Output Folder button (initially hidden)
        self.open_folder_btn = QPushButton("📁 Output")
        self.open_folder_btn.clicked.connect(self.open_output_folder)
        self.open_folder_btn.setVisible(False)
        self.open_folder_btn.setStyleSheet("background-color: #3478f6; color: white; padding: 5px 5px; font-size: 12px;")
        bottom_layout.addWidget(self.open_folder_btn)
        
        layout.addLayout(bottom_layout)
        
        # Check for Gemini API key on startup
        if not self.setting.api_key:
            self.status_label.setText("⚠️ Warning: Gemini API key not set. Translation will be skipped.")
    
    def browse_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio/Video", "", "Media Files (*.mp4 *.avi *.mkv *.mov *.mp3 *.wav *.m4a *.flac *.aac *.ogg)"
        )
        if file_path:
            self.video_path = file_path
            self.video_label.setText(f"Selected: {file_path.split('/')[-1]}")
    
    def update_style_preview(self):
        self.style_preview.setText(self.font.family())
        self.style_preview.setFont(self.font)
        self.style_preview.set_text_color(self.font_color)
        self.style_preview.set_outline(self.border_color, self.radius_slider.value())
        self.style_preview.setStyleSheet("background-color: transparent; border: 1px solid gray; padding: 10px;")
    
    def on_radius_changed(self):
        self.border_radius = self.radius_slider.value()
        self.radius_label.setText(f"{self.border_radius}px")
        self.update_style_preview()
    
    def select_font(self):
        font, ok = QFontDialog.getFont(self.font, self)
        if ok:
            self.font = font
            self.update_style_preview()
            self.status_label.setText(f"Font: {font.family()}, Size: {font.pointSize()}")
    
    def select_font_color(self):
        color = QColorDialog.getColor(self.font_color, self, "Select Font Color", QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.font_color = color
            self.update_style_preview()
            self.status_label.setText(f"Font Color: {color.name()}")
    
    def select_border_color(self):
        color = QColorDialog.getColor(self.border_color, self, "Select Border Color", QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.border_color = color
            self.update_style_preview()
            self.status_label.setText(f"Border Color: {color.name()}")
    
    def transcribe(self):
        if not self.video_path:
            self.status_label.setText("Please select a video first!")
            return
        
        # Check if model exists, download if needed
        model_size = self.setting.selected_model_size
        import sys
        if getattr(sys, 'frozen', False):
            model_path = Path.home() / ".sub11" / "models" / model_size
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            model_path = Path(project_root) / "models" / model_size
        
        required_files = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
        model_complete = model_path.exists() and all((model_path / f).exists() for f in required_files)
        
        if not model_complete:
            dialog = ModelDownloadDialog(model_size, model_path, self)
            if not dialog.exec():
                self.status_label.setText("Model download cancelled")
                return
        
        lang = self.lang_combo.currentText()
        chars_per_subtitle = self.chars_combo.currentIndex()
        if chars_per_subtitle == 0:
            char_limit = 0
        else:
            char_limits = [0, 6, 10, 15, 20, 30]
            char_limit = char_limits[chars_per_subtitle]
        print(char_limit, lang)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.transcribe_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

        style_config = {
            'font': self.font,
            'font_color': self.font_color,
            'border_color': self.border_color,
            'border_radius': self.border_radius
        }
        
        self.transcribe_thread = TranscribeThread(self.video_path, style_config, lang, char_limit)
        self.transcribe_thread.status.connect(self.update_status)
        self.transcribe_thread.progress.connect(self.progress_bar.setValue)
        self.transcribe_thread.indeterminate.connect(self.set_indeterminate_mode)
        self.transcribe_thread.finished.connect(self.on_transcribe_finished)
        self.transcribe_thread.start()
    
    def on_transcribe_finished(self):
        self.progress_bar.setValue(100)
        self.transcribe_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
    
    def preview_subtitles(self):
        """Open subtitle editor for preview and editing"""
        from gui.subtitle_editor import SubtitleEditor
        
        editor = SubtitleEditor(self)
        # Pass current style config to editor
        style_config = {
            'font': self.font,
            'font_color': self.font_color,
            'border_color': self.border_color,
            'border_radius': self.border_radius
        }
        editor.set_style_config(style_config)
        editor.exec()
    
    def export_video(self):
        if not self.video_path:
            self.status_label.setText("Please select a video first!")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Export Options")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Choose export format:"))
        
        btn_layout = QHBoxLayout()
        srt_btn = QPushButton("Export SRT")
        ass_btn = QPushButton("Export ASS")
        video_btn = QPushButton("Export Video")
        srt_btn.clicked.connect(lambda: self.export_srt(dialog))
        ass_btn.clicked.connect(lambda: self.export_ass(dialog))
        video_btn.clicked.connect(lambda: self.export_video_file(dialog))
        btn_layout.addWidget(srt_btn)
        btn_layout.addWidget(ass_btn)
        btn_layout.addWidget(video_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()
    
    def export_srt(self, dialog):
        dialog.accept()
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export SRT", "", "Subtitle Files (*.srt)"
        )
        if save_path:
            if self.exporter.export_srt(save_path):
                self.last_export_path = save_path
                self.status_label.setText(f"SRT exported to {save_path}")
                self.open_folder_btn.setVisible(True)
            else:
                self.status_label.setText("Error: SRT file not found")
    
    def export_ass(self, dialog):
        dialog.accept()
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export ASS", "", "Advanced SubStation Alpha Files (*.ass)"
        )
        if save_path:
            if self.exporter.export_ass(save_path):
                self.last_export_path = save_path
                self.status_label.setText(f"ASS exported to {save_path}")
                self.open_folder_btn.setVisible(True)
            else:
                self.status_label.setText("Error: ASS file not found")
    
    def export_video_file(self, dialog):
        dialog.accept()
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Export Video", "", "Video Files (*.mp4)"
        )
        if save_path:
            self.last_export_path = save_path
            self.status_label.setText(f"Exporting video...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.transcribe_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            
            self.export_thread = ExportThread(self.exporter, self.video_path, save_path)
            self.export_thread.finished.connect(self.on_export_finished)
            self.export_thread.start()
    
    def on_export_finished(self):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Export complete!")
        self.transcribe_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.open_folder_btn.setVisible(True)
    
    def open_output_folder(self):
        """Open the output folder in file manager"""
        import subprocess
        import platform
        
        if not self.last_export_path:
            self.status_label.setText("No export location available")
            return
        
        output_dir = os.path.dirname(self.last_export_path)
        
        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", output_dir])
            elif platform.system() == "Windows":
                subprocess.run(["explorer", output_dir])
            else:  # Linux
                subprocess.run(["xdg-open", output_dir])
        except Exception as e:
            self.status_label.setText(f"Error opening folder: {str(e)}")

    def update_status(self, message):
        self.status_label.setText(message)
    
    def set_indeterminate_mode(self, is_indeterminate):
        if is_indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)