from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
from config import Settings


class SettingsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = Settings()
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Load saved preferences
        prefs = self.settings.preferences
        
        # Gemini API Key
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("Gemini API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setText(prefs.get('api_key', ''))
        self.api_key_input.setPlaceholderText("Enter your Gemini API key")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.api_key_input)
        layout.addLayout(api_layout)
        
        # Gemini Model
        gemini_layout = QHBoxLayout()
        gemini_layout.addWidget(QLabel("Gemini Model:"))
        self.gemini_model_input = QLineEdit()
        self.gemini_model_input.setText(prefs.get('gemini_model', 'gemini-2.5-flash'))
        self.gemini_model_input.setPlaceholderText("e.g., gemini-2.5-flash")
        gemini_layout.addWidget(self.gemini_model_input)
        layout.addLayout(gemini_layout)
        
        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)
        
        # Model Size
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Wisper Model Size:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(self.settings.model_size)
        model_index = self.settings.model_size.index(prefs.get('model_size', 'medium'))
        self.model_combo.setCurrentIndex(model_index)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)
        
        # Device
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(self.settings.device)
        device_index = self.settings.device.index(prefs.get('device', 'auto'))
        self.device_combo.setCurrentIndex(device_index)
        device_layout.addWidget(self.device_combo)
        layout.addLayout(device_layout)
        
        # Compute Type
        compute_layout = QHBoxLayout()
        compute_layout.addWidget(QLabel("Compute Type:"))
        self.compute_combo = QComboBox()
        compute_types = ["int8", "float16", "float32"]
        self.compute_combo.addItems(compute_types)
        compute_index = compute_types.index(prefs.get('compute_type', 'int8'))
        self.compute_combo.setCurrentIndex(compute_index)
        compute_layout.addWidget(self.compute_combo)
        layout.addLayout(compute_layout)
        
        # CRF (Quality)
        crf_layout = QHBoxLayout()
        crf_layout.addWidget(QLabel("Video Quality (CRF):"))
        self.crf_combo = QComboBox()
        self.crf_combo.addItems(self.settings.crf_values)
        crf_index = self.settings.crf_values.index(prefs.get('crf', '23'))
        self.crf_combo.setCurrentIndex(crf_index)
        crf_layout.addWidget(self.crf_combo)
        layout.addLayout(crf_layout)
        
        # Preset (Speed)
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Encoding Speed:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.settings.preset_values)
        preset_index = self.settings.preset_values.index(prefs.get('preset', 'medium'))
        self.preset_combo.setCurrentIndex(preset_index)
        preset_layout.addWidget(self.preset_combo)
        layout.addLayout(preset_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
    
    def save_settings(self):
        # Validate API key
        api_key = self.api_key_input.text().strip()
        if not api_key:
            self.error_label.setText("API key cannot be empty")
            self.error_label.setVisible(True)
            return
        
        if len(api_key) < 20:
            self.error_label.setText("API key seems too short (minimum 20 characters)")
            self.error_label.setVisible(True)
            return
        
        # Validate Gemini model
        gemini_model = self.gemini_model_input.text().strip()
        if not gemini_model:
            self.error_label.setText("Gemini model cannot be empty")
            self.error_label.setVisible(True)
            return
        
        # Hide error if validation passes
        self.error_label.setVisible(False)
        
        preferences = self.get_settings()
        if self.settings.save_preferences(preferences):
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings")
    
    def get_settings(self):
        return {
            'api_key': self.api_key_input.text(),
            'gemini_model': self.gemini_model_input.text().strip(),
            'model_size': self.model_combo.currentText(),
            'device': self.device_combo.currentText(),
            'compute_type': self.compute_combo.currentText(),
            'crf': self.crf_combo.currentText(),
            'preset': self.preset_combo.currentText()
        }
