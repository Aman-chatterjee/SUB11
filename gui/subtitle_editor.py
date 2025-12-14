from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PyQt6.QtCore import Qt
from config import Settings
from business.transcriber import Transcriber
import os


class SubtitleEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self.segments = []
        self.style_config = None
        
        self.setWindowTitle("Subtitle Editor")
        self.setModal(True)
        self.resize(800, 600)
        self.setup_ui()
        self.load_subtitles()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Table for editing subtitles
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Start Time", "End Time", "Text"])
        
        # Make columns resizable
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Changes")
        cancel_btn = QPushButton("Cancel")
        
        save_btn.clicked.connect(self.save_changes)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def load_subtitles(self):
        """Load subtitles from SRT file"""
        if not os.path.exists(self.settings.srt_file):
            QMessageBox.warning(self, "Warning", "No subtitle file found. Please transcribe first.")
            return
        
        # Parse SRT file
        with open(self.settings.srt_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            return
        
        blocks = content.split('\n\n')
        self.segments = []
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # Parse time range
                time_line = lines[1]
                start_time, end_time = time_line.split(' --> ')
                text = '\n'.join(lines[2:])
                
                self.segments.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': text
                })
        
        self.populate_table()
    
    def populate_table(self):
        """Populate table with subtitle data"""
        self.table.setRowCount(len(self.segments))
        
        for i, segment in enumerate(self.segments):
            self.table.setItem(i, 0, QTableWidgetItem(segment['start_time']))
            self.table.setItem(i, 1, QTableWidgetItem(segment['end_time']))
            self.table.setItem(i, 2, QTableWidgetItem(segment['text']))
            
            # Make time columns read-only
            self.table.item(i, 0).setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.item(i, 1).setFlags(Qt.ItemFlag.ItemIsEnabled)
    
    def save_changes(self):
        """Save edited subtitles back to files"""
        print(f"🔍 Debug: Starting save process...")
        print(f"🔍 Debug: Table rows: {self.table.rowCount()}, Segments: {len(self.segments)}")
        
        # Update segments with edited text
        for i in range(self.table.rowCount()):
            text_item = self.table.item(i, 2)
            if text_item and i < len(self.segments):
                old_text = self.segments[i]['text']
                new_text = text_item.text()
                self.segments[i]['text'] = new_text
                if old_text != new_text:
                    print(f"🔍 Debug: Changed [{i}]: '{old_text}' -> '{new_text}'")
        
        # Save SRT file
        print(f"🔍 Debug: Saving SRT to {self.settings.srt_file}")
        self.save_srt()
        
        # Regenerate ASS file with updated text
        print(f"🔍 Debug: Regenerating ASS file")
        self.regenerate_ass()
        
        QMessageBox.information(self, "Success", "Subtitles saved successfully!")
        self.accept()
    
    def save_srt(self):
        """Save updated SRT file"""
        try:
            with open(self.settings.srt_file, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(self.segments, 1):
                    f.write(f"{i}\n")
                    f.write(f"{segment['start_time']} --> {segment['end_time']}\n")
                    f.write(f"{segment['text']}\n\n")
            print(f"✅ Debug: SRT file saved successfully")
        except Exception as e:
            print(f"❌ Debug: Error saving SRT: {e}")
    
    def regenerate_ass(self):
        """Regenerate ASS file with updated text"""
        if not self.style_config:
            return
        
        # Convert SRT time format to seconds for ASS generation
        def srt_time_to_seconds(time_str):
            parts = time_str.replace(',', '.').split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        
        # Convert segments to format expected by generate_ass
        ass_segments = []
        for segment in self.segments:
            ass_segments.append({
                'start': srt_time_to_seconds(segment['start_time']),
                'end': srt_time_to_seconds(segment['end_time']),
                'text': segment['text']
            })
        
        # Generate new ASS file
        transcriber = Transcriber()
        transcriber.generate_ass(ass_segments, self.settings.ass_file, self.style_config)
    
    def set_style_config(self, style_config):
        """Set style configuration for ASS regeneration"""
        self.style_config = style_config