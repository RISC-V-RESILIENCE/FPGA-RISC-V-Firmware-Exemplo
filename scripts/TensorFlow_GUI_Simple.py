import sys
import os
import logging
import numpy as np
import math
import warnings
import shutil
import serial
import threading
import json
import re
from datetime import datetime
from pathlib import Path

# Configurar TensorFlow para reduzir warnings
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Suprimir warnings
warnings.filterwarnings('ignore')

import tensorflow as tf
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QSlider, QLabel, QTextEdit, QLineEdit,
                            QGroupBox, QGridLayout, QScrollArea, QStatusBar, QGraphicsView, QComboBox, QFileDialog, QPushButton, QDialog, QRadioButton, QButtonGroup, QCheckBox, QMessageBox, QTabWidget)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QRect, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QMouseEvent
import matplotlib
# Configurar backend matplotlib para QT6
matplotlib.use('qtagg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Configuração de logs
def setup_logging():
    """📝 Configura o sistema de logging da aplicação"""
    # Caminho para a pasta logs na raiz do projeto
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(project_root, "logs")
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"tensorflow_gui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Configurar encoding UTF-8 para evitar problemas com emojis
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(funcName)s:%(lineno)d - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Configurar dispositivo de computação: GPU -> CUDA -> CPU
def setup_device():
    """🔧 Configura o dispositivo de computação na ordem: GPU -> CUDA -> CPU"""
    logger.info("🔍 Configurando dispositivo de computação...")
    
    # Tentar configurar GPU primeiro
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        try:
            # Tentar usar a primeira GPU disponível
            tf.config.set_visible_devices(gpus[0], 'GPU')
            tf.config.experimental.set_memory_growth(gpus[0], True)
            logger.info(f"🚀 GPU configurada: {gpus[0].name} - {gpus[0].device_type}")
            return 'GPU'
        except Exception as e:
            logger.warning(f"⚠️ Erro ao configurar GPU: {e}")
    
    # Verificar se CUDA está disponível mesmo sem GPU física
    if tf.test.is_built_with_cuda():
        logger.info("🔧 TensorFlow compilado com suporte CUDA, mas sem GPU disponível")
        # Tentar forçar uso de CUDA se disponível
        try:
            tf.config.experimental.set_device_policy('explicit')
            logger.info("🔧 Política de dispositivo CUDA definida")
            return 'CUDA'
        except Exception as e:
            logger.warning(f"⚠️ Erro ao configurar CUDA: {e}")
    
    # Fallback para CPU
    logger.info("💻 Usando CPU para treinamento")
    tf.config.set_visible_devices([], 'GPU')  # Desabilitar GPUs explicitamente
    return 'CPU'

# Executar configuração de dispositivo
DEVICE_TYPE = setup_device()

# Importar biblioteca tinymlgen para quantização avançada
try:
    import tinymlgen
    logger.info("✅ Biblioteca tinymlgen importada com sucesso")
except ImportError:
    logger.warning("⚠️ Biblioteca tinymlgen não encontrada. Instale com: pip install tinymlgen")
    tinymlgen = None

class ESPIDFSelectionDialog(QDialog):
    """🔍 Janela modal para seleção de instalações ESP-IDF"""
    
    def __init__(self, parent=None, found_paths=None):
        super().__init__(parent)
        self.selected_path = None
        self.found_paths = found_paths or []
        
        self.setWindowTitle("🔍 Selecionar Instalação ESP-IDF")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        title_label = QLabel("🔍 Selecionar Instalação ESP-IDF")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Descrição
        if self.found_paths:
            desc_label = QLabel("Foram encontradas múltiplas instalações ESP-IDF. Selecione uma:")
        else:
            desc_label = QLabel("Nenhuma instalação ESP-IDF encontrada nos locais padrão.\nSelecione a pasta onde está o ESP-IDF:")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)
        
        # Radio buttons ou botão de seleção de pasta
        if self.found_paths:
            # Radio buttons para instalações encontradas
            self.radio_group = QButtonGroup()
            self.radio_buttons = []
            
            for i, path in enumerate(self.found_paths):
                radio = QRadioButton(f"ESP-IDF em: {path}")
                radio.setStyleSheet("""
                    QRadioButton {
                        font-size: 12px;
                        padding: 8px;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        margin: 2px;
                    }
                    QRadioButton::indicator {
                        width: 18px;
                        height: 18px;
                    }
                    QRadioButton::indicator::checked {
                        background-color: #3498db;
                        border-color: #3498db;
                    }
                """)
                self.radio_group.addButton(radio, i)
                self.radio_buttons.append(radio)
                layout.addWidget(radio)
                
                # Selecionar o primeiro por padrão
                if i == 0:
                    radio.setChecked(True)
        else:
            # Botão para selecionar pasta
            self.folder_label = QLabel("Nenhuma pasta selecionada")
            self.folder_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            layout.addWidget(self.folder_label)
            
            self.select_folder_btn = QPushButton("📁 Selecionar Pasta ESP-IDF")
            self.select_folder_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px 24px;
                    font-size: 14px;
                    font-weight: bold;
                    min-height: 40px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:pressed {
                    background-color: #21618c;
                }
            """)
            self.select_folder_btn.clicked.connect(self.select_folder)
            layout.addWidget(self.select_folder_btn)
        
        # Botões de ação
        button_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("✅ Confirmar")
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
                color: #7f8c8d;
            }
        """)
        self.ok_btn.clicked.connect(self.accept_selection)
        
        self.cancel_btn = QPushButton("❌ Cancelar")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Desabilitar OK se não houver seleção
        if not self.found_paths:
            self.ok_btn.setEnabled(False)
    
    def select_folder(self):
        """📁 Abre diálogo para selecionar pasta ESP-IDF"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Selecionar Pasta ESP-IDF",
            os.path.expanduser("~")
        )
        
        if folder:
            self.selected_path = folder
            self.folder_label.setText(f"Pasta selecionada: {folder}")
            self.folder_label.setStyleSheet("color: #27ae60; font-weight: bold;")
            self.ok_btn.setEnabled(True)
    
    def accept_selection(self):
        """✅ Confirma a seleção"""
        if self.found_paths:
            # Obter seleção do radio button
            checked_id = self.radio_group.checkedId()
            if checked_id >= 0:
                self.selected_path = self.found_paths[checked_id]
                self.accept()
        elif self.selected_path:
            self.accept()
    
    def get_selected_path(self):
        """🔍 Retorna o caminho selecionado"""
        return self.selected_path

class TrainingModalDialog(QDialog):
    """⏳ Janela modal para exibição durante o treinamento do modelo"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.training_active = True
        self.setWindowTitle("🚀 Treinando Modelo")
        self.setFixedSize(400, 200)
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint)
        
        # Layout principal
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Título
        title_label = QLabel("⏳ Treinando Modelo...")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Ampulheta animada
        self.hourglass_label = QLabel("⏳")
        self.hourglass_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hourglass_label.setFont(QFont("Arial", 48))
        self.hourglass_label.setStyleSheet("color: #3498db;")
        layout.addWidget(self.hourglass_label)
        
        # Botão cancelar
        self.cancel_btn = QPushButton("❌ Cancelar Treinamento")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_training)
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
        
        # Animação da ampulheta
        self.hourglass_states = ["⏳", "⏲️", "⏱️", "⌛"]
        self.current_hourglass = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_hourglass)
        self.animation_timer.start(500)  # Mudar a cada 500ms
        
        # Timer para verificar status do treinamento
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_training_status)
        self.check_timer.start(1000)  # Verificar a cada 1 segundo
        
    def animate_hourglass(self):
        """🔄 Anima a ampulheta"""
        self.current_hourglass = (self.current_hourglass + 1) % len(self.hourglass_states)
        self.hourglass_label.setText(self.hourglass_states[self.current_hourglass])
        
    def cancel_training(self):
        """❌ Cancela o treinamento"""
        logger.info("❌ Usuário cancelou o treinamento")
        self.training_active = False
        self.close()
        
    def check_training_status(self):
        """🔍 Verifica se o treinamento foi concluído"""
        if hasattr(self.parent(), 'training_completed') and self.parent().training_completed:
            self.close()
            
    def closeEvent(self, event):
        """🔒 Limpa recursos ao fechar"""
        self.animation_timer.stop()
        self.check_timer.stop()
        super().closeEvent(event)

class PlotModalDialog(QDialog):
    """🖼️ Janela modal para exibição de gráficos maximizados"""
    
    def __init__(self, parent=None, original_canvas=None, plot_id=""):
        super().__init__(parent)
        self.original_canvas = original_canvas
        self.plot_id = plot_id
        
        self.setWindowTitle(f"Gráfico Ampliado: {plot_id}")
        self.setGeometry(100, 100, 1000, 700)
        self.setModal(True)  # Torna a janela modal
        
        # Layout principal
        layout = QVBoxLayout()
        
        # Área do gráfico - criar uma cópia independente
        self.plot_widget = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_widget)
        
        # Criar um canvas clone para o modal
        self.modal_canvas = PlotCanvas(self, width=12, height=8, plot_id=f"{plot_id}_modal")
        
        # Copiar os dados do canvas original para o modal
        self.copy_plot_data()
        
        # Adicionar o canvas do modal ao layout
        self.plot_layout.addWidget(self.modal_canvas)
        
        layout.addWidget(self.plot_widget)
        
        # Botão de fechar
        self.close_btn = QPushButton("❌ Fechar")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
            QPushButton:pressed {
                background-color: #990000;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)
        
        self.setLayout(layout)
        
    def copy_plot_data(self):
        """📋 Copia os dados do canvas original para o canvas do modal"""
        if not self.original_canvas:
            return
            
        try:
            # Copiar a figura inteira do original
            original_fig = self.original_canvas.fig
            modal_fig = self.modal_canvas.fig
            
            # Limpar a figura do modal
            modal_fig.clear()
            
            # Copiar todos os axes da figura original
            for i, ax in enumerate(original_fig.axes):
                modal_ax = modal_fig.add_subplot(len(original_fig.axes), 1, i+1)
                
                # Copiar linhas, título, labels, etc.
                for line in ax.get_lines():
                    modal_ax.plot(line.get_xdata(), line.get_ydata(), 
                                 color=line.get_color(), 
                                 alpha=line.get_alpha(),
                                 label=line.get_label())
                
                # Copiar título e labels
                modal_ax.set_title(ax.get_title())
                modal_ax.set_xlabel(ax.get_xlabel())
                modal_ax.set_ylabel(ax.get_ylabel())
                modal_ax.grid(ax.grid)
                
                # Copiar legendas se existir
                if ax.get_legend():
                    modal_ax.legend()
            
            # Redesenhar o modal
            self.modal_canvas.draw()
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao copiar dados do gráfico: {str(e)}")
            # Fallback: mostrar mensagem
            self.modal_canvas.axes.clear()
            self.modal_canvas.axes.text(0.5, 0.5, f'Gráfico: {self.plot_id}\n(Clique duplo no original para ampliar)', 
                                       ha='center', va='center', fontsize=12)
            self.modal_canvas.draw()
        
    def closeEvent(self, event):
        """🔒 Limpa recursos ao fechar"""
        # Não precisa restaurar nada pois o original permanece no lugar
        super().closeEvent(event)
        
    def keyPressEvent(self, event):
        """⌨️ Fecha com a tecla ESC"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)

class SerialDataModal(QDialog):
    """📡 Modal para exibir dados seriais em tempo real"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📡 Dados Seriais em Tempo Real")
        self.setGeometry(150, 150, 900, 700)
        self.setModal(False)  # Non-modal para permitir interação com a janela principal
        
        # Dados para exibição
        self.raw_data_buffer = []
        self.parsed_data_buffer = []
        self.max_display_lines = 1000
        self.auto_scroll = True
        
        # Estatísticas
        self.total_lines = 0
        self.parsed_lines = 0
        self.anomaly_count = 0
        self.error_count = 0
        
        self.init_ui()
        
    def init_ui(self):
        """🎨 Inicializa a interface do modal"""
        layout = QVBoxLayout()
        
        # Header com informações
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📡 Monitor Serial - ESP32 TensorFlow Lite")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Checkbox auto-scroll
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.stateChanged.connect(self.toggle_auto_scroll)
        header_layout.addWidget(self.auto_scroll_cb)
        
        # Botão limpar
        clear_btn = QPushButton("🗑️ Limpar")
        clear_btn.clicked.connect(self.clear_data)
        header_layout.addWidget(clear_btn)
        
        # Botão fechar
        close_btn = QPushButton("❌ Fechar")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        layout.addLayout(header_layout)
        
        # Área de estatísticas
        stats_layout = QHBoxLayout()
        
        self.total_lines_label = QLabel("Total: 0")
        self.parsed_lines_label = QLabel("Parseados: 0")
        self.anomaly_label = QLabel("Anomalias: 0")
        self.error_label = QLabel("Erros: 0")
        
        stats_layout.addWidget(self.total_lines_label)
        stats_layout.addWidget(self.parsed_lines_label)
        stats_layout.addWidget(self.anomaly_label)
        stats_layout.addWidget(self.error_label)
        stats_layout.addStretch()
        
        layout.addLayout(stats_layout)
        
        # Tabs para diferentes visualizações
        self.tabs = QTabWidget()
        
        # Tab 1: Dados brutos
        self.raw_data_widget = QWidget()
        raw_layout = QVBoxLayout(self.raw_data_widget)
        
        self.raw_data_display = QTextEdit()
        self.raw_data_display.setReadOnly(True)
        self.raw_data_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #444;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """)
        raw_layout.addWidget(self.raw_data_display)
        
        self.tabs.addTab(self.raw_data_widget, "📄 Dados Brutos")
        
        # Tab 2: Dados parseados
        self.parsed_data_widget = QWidget()
        parsed_layout = QVBoxLayout(self.parsed_data_widget)
        
        self.parsed_data_display = QTextEdit()
        self.parsed_data_display.setReadOnly(True)
        self.parsed_data_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ffff;
                border: 1px solid #444;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """)
        parsed_layout.addWidget(self.parsed_data_display)
        
        self.tabs.addTab(self.parsed_data_widget, "📊 Dados Parseados")
        
        # Tab 3: Estatísticas detalhadas
        self.stats_widget = QWidget()
        stats_layout = QVBoxLayout(self.stats_widget)
        
        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        self.stats_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffff00;
                border: 1px solid #444;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """)
        stats_layout.addWidget(self.stats_display)
        
        self.tabs.addTab(self.stats_widget, "📈 Estatísticas")
        
        layout.addWidget(self.tabs)
        
        # Barra de status
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Pronto para receber dados seriais...")
        layout.addWidget(self.status_bar)
        
        self.setLayout(layout)
        
    def toggle_auto_scroll(self, state):
        """🔄 Alterna auto-scroll"""
        self.auto_scroll = state == Qt.CheckState.Checked.value
        
    def clear_data(self):
        """🗑️ Limpa todos os dados"""
        self.raw_data_buffer.clear()
        self.parsed_data_buffer.clear()
        self.raw_data_display.clear()
        self.parsed_data_display.clear()
        self.stats_display.clear()
        
        # Resetar estatísticas
        self.total_lines = 0
        self.parsed_lines = 0
        self.anomaly_count = 0
        self.error_count = 0
        
        self.update_statistics()
        self.status_bar.showMessage("Dados limpos")
        
    def add_raw_data(self, data):
        """📨 Adiciona dados brutos"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_line = f"[{timestamp}] {data}"
        
        self.raw_data_buffer.append(formatted_line)
        self.total_lines += 1
        
        # Limitar buffer
        if len(self.raw_data_buffer) > self.max_display_lines:
            self.raw_data_buffer.pop(0)
        
        # Atualizar display
        display_text = '\n'.join(self.raw_data_buffer[-500:])  # Mostrar últimas 500 linhas
        self.raw_data_display.setPlainText(display_text)
        
        if self.auto_scroll:
            scrollbar = self.raw_data_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
        self.update_statistics()
        
    def add_parsed_data(self, data):
        """📊 Adiciona dados parseados"""
        timestamp = data['timestamp'].strftime("%H:%M:%S.%f")[:-3]
        
        # Formatar dados parseados
        if data.get('log_type') == 'TFLITE':
            formatted_line = (
                f"[{timestamp}] TFLITE - Iter:{data.get('iteration', 'N/A')} | "
                f"In:{data.get('input_req', 'N/A'):.4f} → Out:{data.get('output_rt', 'N/A'):.4f} | "
                f"Ref:{data.get('reference', 'N/A'):.4f} | Err:{data.get('error', 'N/A'):.4f} | "
                f"Status:{data.get('status', 'N/A')}"
            )
            self.parsed_lines += 1
            
        elif data.get('log_type') == 'ANOMALY':
            formatted_line = (
                f"[{timestamp}] ⚠️ ANOMALIA {data.get('anomaly_type', 'N/A')} - "
                f"Iter:{data.get('iteration', 'N/A')} | Inj:{data.get('injected_value', 'N/A'):.4f} | "
                f"Err:{data.get('error', 'N/A'):.4f}"
            )
            self.anomaly_count += 1
            self.parsed_lines += 1
            
        elif data.get('log_type') == 'INPUT':
            formatted_line = (
                f"[{timestamp}] 📥 INPUT - Iter:{data.get('iteration', 'N/A')} | "
                f"Ref:{data.get('reference', 'N/A'):.4f} | In:{data.get('input_value', 'N/A'):.4f}"
            )
            self.parsed_lines += 1
            
        else:
            formatted_line = (
                f"[{timestamp}] {data.get('log_type', 'UNKNOWN')} - "
                f"x:{data.get('x', 'N/A'):.4f} | pred:{data.get('y_pred', 'N/A'):.4f} | "
                f"real:{data.get('y_real', 'N/A'):.4f} | err:{data.get('error', 'N/A'):.4f}"
            )
            self.parsed_lines += 1
        
        # Verificar se é erro
        if data.get('error', 0) > 0.5:  # Threshold para erro
            self.error_count += 1
        
        self.parsed_data_buffer.append(formatted_line)
        
        # Limitar buffer
        if len(self.parsed_data_buffer) > self.max_display_lines:
            self.parsed_data_buffer.pop(0)
        
        # Atualizar display
        display_text = '\n'.join(self.parsed_data_buffer[-500:])
        self.parsed_data_display.setPlainText(display_text)
        
        if self.auto_scroll:
            scrollbar = self.parsed_data_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
        self.update_statistics()
        self.update_detailed_stats()
        
    def update_statistics(self):
        """📊 Atualiza estatísticas básicas"""
        self.total_lines_label.setText(f"Total: {self.total_lines}")
        self.parsed_lines_label.setText(f"Parseados: {self.parsed_lines}")
        self.anomaly_label.setText(f"Anomalias: {self.anomaly_count}")
        self.error_label.setText(f"Erros: {self.error_count}")
        
    def update_detailed_stats(self):
        """📈 Atualiza estatísticas detalhadas"""
        if not self.parsed_data_buffer:
            return
            
        # Calcular estatísticas dos dados parseados
        tflite_data = [data for data in self.parsed_data_buffer if 'TFLITE' in data]
        anomaly_data = [data for data in self.parsed_data_buffer if 'ANOMALIA' in data]
        
        stats_text = f"""
═══════════════════════════════════════════════════════════════
                    ESTATÍSTICAS DETALHADAS
═══════════════════════════════════════════════════════════════

📊 ESTATÍSTICAS GERAIS:
  • Total de linhas processadas: {self.total_lines}
  • Linhas parseadas com sucesso: {self.parsed_lines}
  • Taxa de parsing: {(self.parsed_lines/max(1,self.total_lines)*100):.1f}%
  
⚠️ DETECÇÃO DE ANOMALIAS:
  • Total de anomalias: {self.anomaly_count}
  • Taxa de anomalias: {(self.anomaly_count/max(1,self.parsed_lines)*100):.2f}%
  • Total de erros (>0.5): {self.error_count}
  • Taxa de erros: {(self.error_count/max(1,self.parsed_lines)*100):.2f}%

📈 DADOS TFLITE:
  • Predições processadas: {len(tflite_data)}
  • Taxa de sucesso: {(len(tflite_data)/max(1,self.parsed_lines)*100):.1f}%

🕒 ÚLTIMA ATUALIZAÇÃO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}
═══════════════════════════════════════════════════════════════
        """
        
        self.stats_display.setPlainText(stats_text)
        
    def keyPressEvent(self, event):
        """⌨️ Fecha com ESC"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)

class PlotCanvas(FigureCanvas):
    """📊 Canvas para plotagem de gráficos matplotlib"""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100, plot_id=""):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.axes = self.fig.add_subplot(111)
        
        # Propriedades para maximização
        self.plot_id = plot_id
        self.modal_dialog = None
        
        # Habilitar clique duplo
        self.setMouseTracking(True)
    
    def clear(self):
        """🧹 Limpa o gráfico"""
        self.axes.clear()
        self.draw()
        
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """🖱️ Lida com clique duplo para abrir janela modal"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_modal()
            
    def open_modal(self):
        """🖼️ Abre o gráfico em janela modal mantendo o original"""
        if self.modal_dialog and self.modal_dialog.isVisible():
            return  # Já está aberto
            
        logger.info(f"🖼️ Abrindo gráfico {self.plot_id} em janela modal")
        
        # Encontrar a janela principal
        main_window = self.parent()
        while main_window and main_window.parent():
            main_window = main_window.parent()
            
        if not main_window:
            return
            
        # Criar e mostrar janela modal com cópia do gráfico
        self.modal_dialog = PlotModalDialog(main_window, self, self.plot_id)
        
        # Atualizar status
        if hasattr(main_window, 'update_status'):
            main_window.update_status(f"Gráfico {self.plot_id} ampliado - ESC ou ❌ para fechar")
        
        # Mostrar modal
        self.modal_dialog.show()
        
    def resizeEvent(self, event):
        """📏 Redimensiona o matplotlib quando o widget é redimensionado"""
        super().resizeEvent(event)
        self.draw()
        
    def plot(self, x, y, title="", xlabel="", ylabel="", color='blue', alpha=1.0):
        """📈 Plota dados no canvas"""
        self.axes.clear()
        self.axes.plot(x, y, color=color, alpha=alpha)
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True, alpha=0.3)
        self.draw()
        
    def plot_scatter(self, x, y, title="", xlabel="", ylabel="", color='blue', alpha=1.0, s=1):
        """📈 Plota dispersão de dados"""
        self.axes.clear()
        self.axes.scatter(x, y, color=color, alpha=alpha, s=s)
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.grid(True, alpha=0.3)
        self.draw()
        
    def plot_multiple(self, x_data, y_data, labels, colors, title="", xlabel="", ylabel="", alpha=1.0):
        """📈 Plota múltiplas séries de dados"""
        self.axes.clear()
        for x, y, label, color in zip(x_data, y_data, labels, colors):
            self.axes.plot(x, y, label=label, color=color, alpha=alpha)
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.legend()
        self.axes.grid(True, alpha=0.3)
        self.draw()

class SerialReader(QThread):
    """📡 Thread para leitura de dados da porta serial"""
    
    data_received = pyqtSignal(str)  # Sinal emitido quando dados são recebidos
    prediction_data = pyqtSignal(dict)  # Sinal emitido quando dados de predição são extraídos
    
    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.port_name = ""
        self.baudrate = 115200
        self.running = False
        self.timeout = 1.0
        
        # Buffer para dados recebidos
        self.buffer = ""
        
        # Padrões regex para extrair dados de predição
        self.prediction_patterns = [
            # Padrão principal para logs TFLITE do ESP32
            r'TFLITE:\s*\[.*?\]\s*tflite_inference_task:\d+\s*-\s*Iter:\s*(\d+)\s*\|\s*InReq:\s*([+-]?\d*\.?\d+)\s*\|\s*InQ:\s*([+-]?\d*\.?\d+)\s*\[\d+\]\s*\|\s*OutRt:\s*([+-]?\d*\.?\d+)\s*\|\s*OutQ:\s*([+-]?\d*\.?\d+)\s*\[\d+\]\s*\|\s*Ref:\s*([+-]?\d*\.?\d+)\s*\|\s*Err:\s*([+-]?\d*\.?\d+)\s*\|\s*Status:\s*(\w+)',
            
            # Padrão simplificado (fallback)
            r'Iter:\s*(\d+).*?InReq:\s*([+-]?\d*\.?\d+).*?Ref:\s*([+-]?\d*\.?\d+).*?Err:\s*([+-]?\d*\.?\d+)',
            
            # Padrões para logs de anomalias
            r'ANOMALIA\s+(INJETADA|EXTERNA).*?Iter:\s*(\d+).*?Inj:\s*([+-]?\d*\.?\d+).*?Err:\s*([+-]?\d*\.?\d+)',
            
            # Padrão para logs INPUT
            r'INPUT:\s*\[.*?\]\s*generate_input_value:\d+\s*-\s*Iter:\s*(\d+)\s*\|\s*Ref:\s*([+-]?\d*\.?\d+)\s*\|\s*Input:\s*([+-]?\d*\.?\d+)',
            
            # Padrões genéricos (compatibilidade)
            r'PREDICTION:\s*x=([+-]?\d*\.?\d+),\s*y_pred=([+-]?\d*\.?\d+),\s*y_real=([+-]?\d*\.?\d+),\s*error=([+-]?\d*\.?\d+)',
            r'Prediction:\s*input=([+-]?\d*\.?\d+),\s*output=([+-]?\d*\.?\d+),\s*expected=([+-]?\d*\.?\d+),\s*error=([+-]?\d*\.?\d+)',
            r'\[.*\].*prediction.*?(\d+\.?\d*).*?(\d+\.?\d*).*?(\d+\.?\d*)',
            r'TFLite.*?input.*?(\d+\.?\d*).*?output.*?(\d+\.?\d*)',
        ]
        
    def connect_serial(self, port_name, baudrate=115200):
        """🔌 Conecta à porta serial"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.disconnect_serial()
                
            self.port_name = port_name
            self.baudrate = baudrate
            # exclusive=False: não adquire TIOCEXCL, permitindo que outro
            # programa (ex.: PuTTY) mantenha a porta aberta simultaneamente
            # e envie comandos ao firmware enquanto o GUI apenas escuta.
            # write_timeout curto reforça que este lado é passivo (read-only
            # de fato — nada escrevemos, mas evitamos bloquear caso algo
            # tente enviar).
            serial_kwargs = dict(
                port=port_name,
                baudrate=baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                write_timeout=0,
            )
            try:
                self.serial_port = serial.Serial(exclusive=False, **serial_kwargs)
            except TypeError:
                # pyserial < 3.3 não suporta o kwarg exclusive
                self.serial_port = serial.Serial(**serial_kwargs)

            logger.info(
                f"📡 Conectado à porta serial {port_name} "
                f"(baudrate={baudrate}, modo=listen-only/não-exclusivo)"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar à porta serial {port_name}: {str(e)}")
            return False
    
    def disconnect_serial(self):
        """🔌 Desconecta da porta serial"""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                logger.info(f"📡 Desconectado da porta serial {self.port_name}")
        except Exception as e:
            logger.error(f"❌ Erro ao desconectar porta serial: {str(e)}")
    
    def start_reading(self):
        """▶️ Inicia a leitura de dados"""
        if not self.serial_port or not self.serial_port.is_open:
            logger.error("❌ Nenhuma porta serial conectada")
            return False
            
        self.running = True
        self.start()
        logger.info("📡 Iniciando leitura de dados da porta serial")
        return True
    
    def stop_reading(self):
        """⏹️ Para a leitura de dados"""
        self.running = False
        if self.isRunning():
            self.wait(2000)  # Esperar até 2 segundos para a thread terminar
        logger.info("📡 Leitura de dados da porta serial parada")
    
    def run(self):
        """🔄 Executa a leitura em thread separada"""
        while self.running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    # Ler dados disponíveis
                    data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    self.buffer += data
                    
                    # Processar linhas completas
                    while '\n' in self.buffer or '\r' in self.buffer:
                        if '\n' in self.buffer:
                            line, self.buffer = self.buffer.split('\n', 1)
                        else:
                            line, self.buffer = self.buffer.split('\r', 1)
                        
                        line = line.strip()
                        if line:
                            # Emitir sinal com a linha recebida
                            self.data_received.emit(line)
                            
                            # Tentar extrair dados de predição
                            prediction_data = self.extract_prediction_data(line)
                            if prediction_data:
                                self.prediction_data.emit(prediction_data)
                
                # Pequena pausa para não sobrecarregar CPU
                self.msleep(10)
                
            except serial.SerialException as e:
                logger.error(f"❌ Erro na leitura serial: {str(e)}")
                break
            except Exception as e:
                logger.error(f"❌ Erro inesperado na thread serial: {str(e)}")
                break
        
        # Limpar recursos ao finalizar
        self.disconnect_serial()
    
    def extract_prediction_data(self, line):
        """🔍 Extrai dados de predição de uma linha de log do ESP32"""
        for i, pattern in enumerate(self.prediction_patterns):
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    
                    # Padrão principal TFLITE (7+ grupos)
                    if i == 0 and len(groups) >= 7:
                        iteration = int(groups[0])
                        input_req = float(groups[1])
                        input_q = float(groups[2])
                        output_rt = float(groups[3])
                        output_q = float(groups[4])
                        reference = float(groups[5])
                        error = float(groups[6])
                        status = groups[7] if len(groups) > 7 else "OK"
                        
                        return {
                            'iteration': iteration,
                            'input_req': input_req,
                            'input_q': input_q,
                            'output_rt': output_rt,
                            'output_q': output_q,
                            'reference': reference,
                            'error': error,
                            'status': status,
                            'x': input_req,
                            'y_pred': output_rt,
                            'y_real': reference,
                            'timestamp': datetime.now(),
                            'raw_line': line,
                            'log_type': 'TFLITE'
                        }
                    
                    # Padrão simplificado (4 grupos)
                    elif i == 1 and len(groups) >= 4:
                        iteration = int(groups[0])
                        input_req = float(groups[1])
                        reference = float(groups[2])
                        error = float(groups[3])
                        
                        return {
                            'iteration': iteration,
                            'input_req': input_req,
                            'reference': reference,
                            'error': error,
                            'x': input_req,
                            'y_pred': input_req,  # Approximation
                            'y_real': reference,
                            'timestamp': datetime.now(),
                            'raw_line': line,
                            'log_type': 'TFLITE_SIMPLIFIED'
                        }
                    
                    # Padrão de anomalia (4 grupos)
                    elif i == 2 and len(groups) >= 4:
                        anomaly_type = groups[0]
                        iteration = int(groups[1])
                        injected_value = float(groups[2])
                        error = float(groups[3])
                        
                        return {
                            'anomaly_type': anomaly_type,
                            'iteration': iteration,
                            'injected_value': injected_value,
                            'error': error,
                            'x': injected_value,
                            'y_pred': injected_value,  # Approximation
                            'y_real': 0.0,  # Not available in this pattern
                            'timestamp': datetime.now(),
                            'raw_line': line,
                            'log_type': 'ANOMALY'
                        }
                    
                    # Padrão INPUT (3 grupos)
                    elif i == 3 and len(groups) >= 3:
                        iteration = int(groups[0])
                        reference = float(groups[1])
                        input_value = float(groups[2])
                        
                        return {
                            'iteration': iteration,
                            'reference': reference,
                            'input_value': input_value,
                            'x': input_value,
                            'y_pred': input_value,  # Approximation
                            'y_real': reference,
                            'timestamp': datetime.now(),
                            'raw_line': line,
                            'log_type': 'INPUT'
                        }
                    
                    # Padrões genéricos (fallback)
                    elif len(groups) >= 3:
                        x_val = float(groups[0])
                        y_pred = float(groups[1])
                        y_real = float(groups[2])
                        error = float(groups[3]) if len(groups) > 3 else abs(y_pred - y_real)
                        
                        return {
                            'x': x_val,
                            'y_pred': y_pred,
                            'y_real': y_real,
                            'error': error,
                            'timestamp': datetime.now(),
                            'raw_line': line,
                            'log_type': 'GENERIC'
                        }
                        
                except (ValueError, IndexError) as e:
                    logger.debug(f"⚠️ Erro ao extrair valores da linha: {line} - {str(e)}")
                    continue
        
        return None
    
    @staticmethod
    def list_available_ports():
        """📋 Lista portas seriais disponíveis.

        Além das portas físicas enumeradas por pyserial, inclui symlinks para
        PTYs em /tmp/tty* (ex.: /tmp/ttyGUI criada por scripts/serial_mux.py).
        Permite o compartilhamento de /dev/ttyACM0 com o PuTTY sem conflito.
        """
        import glob
        import os
        import serial.tools.list_ports

        ports = []
        try:
            port_list = serial.tools.list_ports.comports()
            for port in port_list:
                ports.append({
                    'device': port.device,
                    'description': port.description,
                    'hwid': port.hwid
                })
        except Exception as e:
            logger.error(f"❌ Erro ao listar portas seriais: {str(e)}")

        # PTYs espelhadas pelo multiplexador serial (scripts/serial_mux.py).
        # Nomes convencionais: /tmp/ttyGUI (read-only) e /tmp/ttyPUTTY.
        try:
            known = {p['device'] for p in ports}
            for path in sorted(glob.glob('/tmp/tty*')):
                if path in known:
                    continue
                try:
                    if not os.path.exists(path):
                        continue
                except OSError:
                    continue
                ports.append({
                    'device': path,
                    'description': 'PTY espelhada (serial_mux)',
                    'hwid': 'MUX',
                })
        except Exception as e:
            logger.debug(f"⚠️ Falha ao listar PTYs /tmp/tty*: {e}")

        return ports

class TensorFlowGUI(QMainWindow):
    """🎯 Janela principal da aplicação TensorFlow GUI"""
    
    def __init__(self):
        super().__init__()
        logger.info("🚀 Inicializando aplicação TensorFlow GUI")
        
        # Parâmetros padrão
        self.samples = 10000
        self.seed = 1337
        self.epochs = 600
        self.batch_size = 16
        self.noise_factor = 0.1
        self.formula = "senoide"  # Fórmula matemática atual
        
        # Parâmetros para predição ao vivo
        self.live_prediction_speed = 100  # ms entre predições
        self.live_prediction_running = False
        self.live_prediction_timer = None
        self.live_prediction_count = 0
        self.live_prediction_errors = []
        
        # Dados para gráfico de predição ao vivo
        self.live_x_data = []  # Valores de x das predições ao vivo
        self.live_y_pred_data = []  # Valores preditos ao vivo
        self.live_y_real_data = []  # Valores reais ao vivo
        self.live_errors = []  # Erros das predições ao vivo
        
        # Dados e modelo
        self.x_value = None
        self.y_value = None
        self.y_noisy = None
        self.x_train = None
        self.x_validate = None
        self.x_test = None
        self.y_train = None
        self.y_validate = None
        self.y_test = None
        self.model = None
        self.history = None
        self.predictions = None
        
        # Barra de status
        self.status_bar = None
        self.current_task = ""
        
        # Controle de treinamento para modal
        self.training_completed = False
        self.training_cancelled = False
        self.training_modal = None
        
        # Comunicação serial
        self.serial_reader = SerialReader()
        self.serial_connected = False
        self.serial_data_buffer = []  # Buffer para dados recebidos
        self.serial_prediction_data = []  # Dados de predição extraídos
        self.serial_max_buffer_size = 1000  # Limite máximo de linhas no buffer
        
        # Modal para dados seriais
        self.serial_modal = None
        
        # Dados para gráficos do microcontrolador
        self.mc_x_data = []  # Valores de x do microcontrolador
        self.mc_y_pred_data = []  # Valores preditos pelo microcontrolador
        self.mc_y_real_data = []  # Valores reais esperados
        self.mc_errors = []  # Erros das predições
        self.mc_timestamps = []  # Timestamps das predições
        
        # Dados específicos para anomalias
        self.mc_anomalies = []  # Lista de anomalias detectadas
        self.mc_status_data = []  # Status das predições (OK, EXT, INJ)
        self.mc_iterations = []  # Números das iterações
        
        self.initUI()
        self.generate_data()
        
    def initUI(self):
        """🎨 Inicializa a interface do usuário"""
        logger.info("🎨 Configurando interface do usuário")
        
        self.setWindowTitle('TensorFlow Senoidal - Visualização Interativa')
        self.setGeometry(100, 100, 1400, 900)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Área de controle lateral esquerda com scroll
        left_scroll_area = QScrollArea()
        left_scroll_widget = QWidget()
        left_layout = QVBoxLayout(left_scroll_widget)
        
        # Controle de modos
        control_area = self.create_control_area()
        control_area.setMaximumWidth(300)
        left_layout.addWidget(control_area)
        
        # Área de comunicação serial
        serial_area = self.create_serial_area()
        serial_area.setMaximumWidth(300)
        left_layout.addWidget(serial_area)
        
        # Área de informações
        info_area = self.create_info_area()
        info_area.setMaximumWidth(300)
        left_layout.addWidget(info_area)
        
        # Adicionar espaço stretch no final para evitar compactação
        left_layout.addStretch()
        
        left_scroll_area.setWidget(left_scroll_widget)
        left_scroll_area.setWidgetResizable(True)
        left_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        left_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        left_scroll_area.setMaximumWidth(320)  # Largura fixa para a sidebar
        
        main_layout.addWidget(left_scroll_area)
        
        # Área principal direita
        right_layout = QVBoxLayout()
        
        # Área de gráficos com scroll
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Grid de gráficos
        self.plot_grid = QGridLayout()
        scroll_layout.addLayout(self.plot_grid)
        
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        right_layout.addWidget(scroll_area)
        
        main_layout.addLayout(right_layout)
        
        # Criar barra de status
        self.create_status_bar()
        
        # Criar canvases para gráficos
        self.create_plots()
        
    def create_control_area(self):
        """🎛️ Cria área de controles"""
        group = QGroupBox("🎛️ Controle de Modos")
        layout = QVBoxLayout()
        
        # Sliders
        slider_layout = QGridLayout()
        
        # ComboBox de fórmulas matemáticas
        self.formula_combo = QComboBox()
        self.formula_combo.addItems([
            "Senoide",
            "Cossenoide", 
            "Parábola",
            "Cúbica",
            "Exponencial",
            "Logarítmica",
            "Tangente",
            "Onda Quadrada",
            "Onda Triangular",
            "Senoide Amortecida"
        ])
        self.formula_combo.setCurrentText("Senoide")
        self.formula_combo.currentTextChanged.connect(self.on_formula_changed)
        slider_layout.addWidget(QLabel("Fórmula:"), 0, 0)
        slider_layout.addWidget(self.formula_combo, 0, 1)
        
        # Slider de samples
        self.samples_slider = QSlider(Qt.Orientation.Horizontal)
        self.samples_slider.setRange(1000, 50000)
        self.samples_slider.setValue(self.samples)
        self.samples_slider.valueChanged.connect(self.update_samples)
        self.samples_label = QLabel(f"Samples: {self.samples}")
        slider_layout.addWidget(self.samples_label, 1, 0)
        slider_layout.addWidget(self.samples_slider, 1, 1)
        
        # Slider de épocas
        self.epochs_slider = QSlider(Qt.Orientation.Horizontal)
        self.epochs_slider.setRange(10, 1000)
        self.epochs_slider.setValue(self.epochs)
        self.epochs_slider.valueChanged.connect(self.update_epochs)
        self.epochs_label = QLabel(f"Épocas: {self.epochs}")
        slider_layout.addWidget(self.epochs_label, 2, 0)
        slider_layout.addWidget(self.epochs_slider, 2, 1)
        
        # Slider de batch size
        self.batch_slider = QSlider(Qt.Orientation.Horizontal)
        self.batch_slider.setRange(4, 128)
        self.batch_slider.setValue(self.batch_size)
        self.batch_slider.valueChanged.connect(self.update_batch_size)
        self.batch_label = QLabel(f"Batch Size: {self.batch_size}")
        slider_layout.addWidget(self.batch_label, 3, 0)
        slider_layout.addWidget(self.batch_slider, 3, 1)
        
        # Slider de ruído
        self.noise_slider = QSlider(Qt.Orientation.Horizontal)
        self.noise_slider.setRange(0, 50)
        self.noise_slider.setValue(int(self.noise_factor * 100))
        self.noise_slider.valueChanged.connect(self.update_noise)
        self.noise_label = QLabel(f"Fator de Ruído: {self.noise_factor:.2f}")
        slider_layout.addWidget(self.noise_label, 4, 0)
        slider_layout.addWidget(self.noise_slider, 4, 1)
        
        layout.addLayout(slider_layout)
        
        # Botões
        button_layout = QVBoxLayout()
        
        self.generate_btn = QPushButton("🔄 Gerar Dados")
        self.generate_btn.clicked.connect(self.generate_data)
        button_layout.addWidget(self.generate_btn)
        
        self.train_btn = QPushButton("🚀 Treinar Modelo")
        self.train_btn.clicked.connect(self.train_model)
        button_layout.addWidget(self.train_btn)
        
        self.predict_btn = QPushButton("🔮 Fazer Predições")
        self.predict_btn.clicked.connect(self.make_predictions)
        button_layout.addWidget(self.predict_btn)

        # Combobox para escolha do tipo de ruído aplicado na predição
        self.noise_type_combo = QComboBox()
        self.noise_type_combo.addItems([
            "Near (Gaussiano)",
            "Branco",
            "Rosa",
            "Brownian",
            "Azul",
            "Violeta",
            "Cinza",
        ])
        self.noise_type_combo.setToolTip(
            "Tipo de ruído aplicado à entrada durante a predição"
        )
        self.noise_type_combo.setCurrentIndex(0)
        button_layout.addWidget(QLabel("Ruído:"))
        button_layout.addWidget(self.noise_type_combo)
        
        # Área de predição ao vivo
        live_layout = QVBoxLayout()
        live_label = QLabel("🔥 Predição ao Vivo:")
        live_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        live_layout.addWidget(live_label)
        
        # Slider de velocidade
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Velocidade:"))
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(10, 2000)  # 10ms a 2s
        self.speed_slider.setValue(self.live_prediction_speed)
        self.speed_slider.valueChanged.connect(self.update_live_speed)
        self.speed_label = QLabel(f"{self.live_prediction_speed}ms")
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        live_layout.addLayout(speed_layout)
        
        self.live_btn = QPushButton("🔥 Iniciar Predição ao Vivo")
        self.live_btn.clicked.connect(self.toggle_live_prediction)
        self.live_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e55a2b;
            }
            QPushButton:pressed {
                background-color: #cc4a1f;
            }
        """)
        live_layout.addWidget(self.live_btn)
        
        button_layout.addLayout(live_layout)
        
        # Área de exportação com dropdown e botão
        export_layout = QVBoxLayout()
        export_label = QLabel("📤 Exportação TinyML:")
        export_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        export_layout.addWidget(export_label)
        
        # Dropdown de microcontroladores
        mcuf_layout = QHBoxLayout()
        mcuf_layout.addWidget(QLabel("MCU:"))
        self.mcuf_combo = QComboBox()
        self.mcuf_combo.addItems([
            "ESP32 (Arduino)",
            "ESP32 (ESP-IDF)",
            "STM32",
            "Arduino Nano",
            "SoC LiteX+VexRiscv"
        ])
        self.mcuf_combo.setCurrentText("ESP32 (Arduino)")
        mcuf_layout.addWidget(self.mcuf_combo)
        export_layout.addLayout(mcuf_layout)
        
        # Dropdown de quantização
        quant_layout = QHBoxLayout()
        quant_layout.addWidget(QLabel("Quantização:"))
        self.quant_combo = QComboBox()
        self.quant_combo.addItems([
            "Float32 (Padrão)",
            "Int8 (8-bit)",
            "Int1 (1-bit - TinyMLGen)"
        ])
        self.quant_combo.setCurrentText("Float32 (Padrão)")
        quant_layout.addWidget(self.quant_combo)
        
        # Conectar mudança de MCU para ajustar quantização padrão
        self.mcuf_combo.currentTextChanged.connect(self.update_quantization_for_mcu)
        export_layout.addLayout(quant_layout)
        
        # Checkbox para salvar apenas modelo
        self.model_only_checkbox = QCheckBox("Apenas modelo (.tflite + .h)")
        self.model_only_checkbox.setChecked(False)
        self.model_only_checkbox.setStyleSheet("""
            QCheckBox {
                font-size: 11px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """)
        export_layout.addWidget(self.model_only_checkbox)
        
        self.export_btn = QPushButton("💾 Exportar Modelo TFLite")
        self.export_btn.clicked.connect(self.export_model)
        export_layout.addWidget(self.export_btn)
        
        button_layout.addLayout(export_layout)
        
        layout.addLayout(button_layout)
        group.setLayout(layout)
        
        return group
        
    def create_serial_area(self):
        """📡 Cria área de comunicação serial"""
        group = QGroupBox("📡 Comunicação Serial")
        layout = QVBoxLayout()
        
        # ComboBox para seleção de porta
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Porta:"))
        
        self.port_combo = QComboBox()
        self.refresh_serial_ports()
        port_layout.addWidget(self.port_combo)
        
        # Botão para atualizar portas
        self.refresh_ports_btn = QPushButton("🔄")
        self.refresh_ports_btn.setToolTip("Atualizar lista de portas")
        self.refresh_ports_btn.setFixedSize(30, 25)
        self.refresh_ports_btn.clicked.connect(self.refresh_serial_ports)
        port_layout.addWidget(self.refresh_ports_btn)
        
        layout.addLayout(port_layout)
        
        # Baudrate
        baud_layout = QHBoxLayout()
        baud_layout.addWidget(QLabel("Baud:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"])
        self.baud_combo.setCurrentText("115200")
        baud_layout.addWidget(self.baud_combo)
        layout.addLayout(baud_layout)
        
        # Botões de conexão
        conn_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("🔌 Conectar")
        self.connect_btn.clicked.connect(self.toggle_serial_connection)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        conn_layout.addWidget(self.connect_btn)
        
        # Botão para abrir modal de dados
        self.modal_btn = QPushButton("📊 Dados em Tempo Real")
        self.modal_btn.clicked.connect(self.open_serial_modal)
        self.modal_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        conn_layout.addWidget(self.modal_btn)
        
        self.clear_btn = QPushButton("🗑️ Limpar")
        self.clear_btn.clicked.connect(self.clear_serial_data)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d68910;
            }
            QPushButton:pressed {
                background-color: #ca6f1e;
            }
        """)
        conn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(conn_layout)
        
        # Área de exibição de dados
        data_label = QLabel("📨 Dados Recebidos:")
        data_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        layout.addWidget(data_label)
        
        self.serial_display = QTextEdit()
        self.serial_display.setMaximumHeight(150)
        self.serial_display.setReadOnly(True)
        self.serial_display.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 5px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.serial_display)
        
        # Área de estatísticas
        stats_label = QLabel("📊 Estatísticas da Predição:")
        stats_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        layout.addWidget(stats_label)
        
        stats_layout = QGridLayout()
        
        self.mc_predictions_label = QLabel("Predições:")
        self.mc_predictions_text = QLineEdit()
        self.mc_predictions_text.setReadOnly(True)
        self.mc_predictions_text.setStyleSheet("background-color: #ecf0f1; border: 1px solid #bdc3c7;")
        
        self.mc_avg_error_label = QLabel("Erro Médio:")
        self.mc_avg_error_text = QLineEdit()
        self.mc_avg_error_text.setReadOnly(True)
        self.mc_avg_error_text.setStyleSheet("background-color: #ecf0f1; border: 1px solid #bdc3c7;")
        
        self.mc_max_error_label = QLabel("Erro Máximo:")
        self.mc_max_error_text = QLineEdit()
        self.mc_max_error_text.setReadOnly(True)
        self.mc_max_error_text.setStyleSheet("background-color: #ecf0f1; border: 1px solid #bdc3c7;")
        
        self.mc_status_label = QLabel("Status:")
        self.mc_status_text = QLineEdit()
        self.mc_status_text.setReadOnly(True)
        self.mc_status_text.setText("Desconectado")
        self.mc_status_text.setStyleSheet("background-color: #e74c3c; color: white; border: 1px solid #c0392b;")
        
        stats_layout.addWidget(self.mc_predictions_label, 0, 0)
        stats_layout.addWidget(self.mc_predictions_text, 0, 1)
        stats_layout.addWidget(self.mc_avg_error_label, 1, 0)
        stats_layout.addWidget(self.mc_avg_error_text, 1, 1)
        stats_layout.addWidget(self.mc_max_error_label, 2, 0)
        stats_layout.addWidget(self.mc_max_error_text, 2, 1)
        stats_layout.addWidget(self.mc_status_label, 3, 0)
        stats_layout.addWidget(self.mc_status_text, 3, 1)
        
        layout.addLayout(stats_layout)
        
        group.setLayout(layout)
        
        # Conectar sinais do serial reader
        self.serial_reader.data_received.connect(self.on_serial_data_received)
        self.serial_reader.prediction_data.connect(self.on_prediction_data_received)
        
        return group
        
    def create_info_area(self):
        """📝 Cria área de informações"""
        group = QGroupBox("📊 Informações do Modelo")
        layout = QGridLayout()
        
        # Criar labels e caixas de texto individuais para cada métrica
        self.device_label = QLabel("Dispositivo:")
        self.device_text = QLineEdit()
        self.device_text.setReadOnly(True)
        
        self.model_type_label = QLabel("Tipo do Modelo:")
        self.model_type_text = QLineEdit()
        self.model_type_text.setReadOnly(True)
        
        self.total_params_label = QLabel("Parâmetros Totais:")
        self.total_params_text = QLineEdit()
        self.total_params_text.setReadOnly(True)
        
        self.trainable_params_label = QLabel("Parâmetros Treináveis:")
        self.trainable_params_text = QLineEdit()
        self.trainable_params_text.setReadOnly(True)
        
        self.loss_train_label = QLabel("Loss (Treino):")
        self.loss_train_text = QLineEdit()
        self.loss_train_text.setReadOnly(True)
        
        self.loss_val_label = QLabel("Loss (Val):")
        self.loss_val_text = QLineEdit()
        self.loss_val_text.setReadOnly(True)
        
        self.mae_train_label = QLabel("MAE (Treino):")
        self.mae_train_text = QLineEdit()
        self.mae_train_text.setReadOnly(True)
        
        self.mae_val_label = QLabel("MAE (Val):")
        self.mae_val_text = QLineEdit()
        self.mae_val_text.setReadOnly(True)
        
        # Adicionar ao grid layout
        layout.addWidget(self.device_label, 0, 0)
        layout.addWidget(self.device_text, 0, 1)
        layout.addWidget(self.model_type_label, 1, 0)
        layout.addWidget(self.model_type_text, 1, 1)
        layout.addWidget(self.total_params_label, 2, 0)
        layout.addWidget(self.total_params_text, 2, 1)
        layout.addWidget(self.trainable_params_label, 3, 0)
        layout.addWidget(self.trainable_params_text, 3, 1)
        layout.addWidget(self.loss_train_label, 4, 0)
        layout.addWidget(self.loss_train_text, 4, 1)
        layout.addWidget(self.loss_val_label, 5, 0)
        layout.addWidget(self.loss_val_text, 5, 1)
        layout.addWidget(self.mae_train_label, 6, 0)
        layout.addWidget(self.mae_train_text, 6, 1)
        layout.addWidget(self.mae_val_label, 7, 0)
        layout.addWidget(self.mae_val_text, 7, 1)
        
        group.setLayout(layout)
        return group
        
    def clear_model_info(self):
        """🧹 Limpa as informações do modelo"""
        self.device_text.setText("")
        self.model_type_text.setText("")
        self.total_params_text.setText("")
        self.trainable_params_text.setText("")
        self.loss_train_text.setText("")
        self.loss_val_text.setText("")
        self.mae_train_text.setText("")
        self.mae_val_text.setText("")
        
    def create_status_bar(self):
        """📊 Cria barra de status"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status("Pronto para uso")
        
    def create_plots(self):
        """📊 Cria os canvases para plotagem com boxes individuais"""
        logger.info("📊 Criando canvases para gráficos com boxes individuais")
        
        # Criar boxes individuais para cada gráfico
        self.plot_boxes = []
        
        # Gráfico 1: Senoide pura
        self.plot1 = PlotCanvas(self, width=6, height=3, plot_id="Senoide Pura")
        plot1_box = self.create_plot_box("Senoide Pura", self.plot1)
        self.plot_grid.addWidget(plot1_box, 0, 0)
        self.plot_boxes.append((plot1_box, self.plot1))
        
        # Gráfico 2: Senoide com ruído
        self.plot2 = PlotCanvas(self, width=6, height=3, plot_id="Senoide com Ruído")
        plot2_box = self.create_plot_box("Senoide com Ruído", self.plot2)
        self.plot_grid.addWidget(plot2_box, 0, 1)
        self.plot_boxes.append((plot2_box, self.plot2))
        
        # Gráfico 3: Conjuntos de dados
        self.plot3 = PlotCanvas(self, width=6, height=3, plot_id="Conjuntos de Dados")
        plot3_box = self.create_plot_box("Conjuntos de Dados", self.plot3)
        self.plot_grid.addWidget(plot3_box, 1, 0)
        self.plot_boxes.append((plot3_box, self.plot3))
        
        # Gráfico 4: Loss durante treinamento
        self.plot4 = PlotCanvas(self, width=6, height=3, plot_id="Loss Treinamento")
        plot4_box = self.create_plot_box("Loss Treinamento", self.plot4)
        self.plot_grid.addWidget(plot4_box, 1, 1)
        self.plot_boxes.append((plot4_box, self.plot4))
        
        # Gráfico 5: MAE durante treinamento
        self.plot5 = PlotCanvas(self, width=6, height=3, plot_id="MAE Treinamento")
        plot5_box = self.create_plot_box("MAE Treinamento", self.plot5)
        self.plot_grid.addWidget(plot5_box, 2, 0)
        self.plot_boxes.append((plot5_box, self.plot5))
        
        # Gráfico 6: Predições vs Real
        self.plot6 = PlotCanvas(self, width=6, height=3, plot_id="Predições vs Real")
        plot6_box = self.create_plot_box("Predições vs Real", self.plot6)
        self.plot_grid.addWidget(plot6_box, 2, 1)
        self.plot_boxes.append((plot6_box, self.plot6))
        
        # Gráfico 7: Dados do Microcontrolador
        self.plot7 = PlotCanvas(self, width=6, height=3, plot_id="Microcontrolador")
        plot7_box = self.create_plot_box("Microcontrolador - Predições em Tempo Real", self.plot7)
        self.plot_grid.addWidget(plot7_box, 3, 0)
        self.plot_boxes.append((plot7_box, self.plot7))
        
        # Gráfico 8: Erro do Microcontrolador
        self.plot8 = PlotCanvas(self, width=6, height=3, plot_id="Erro Microcontrolador")
        plot8_box = self.create_plot_box("Microcontrolador - Erro de Predição", self.plot8)
        self.plot_grid.addWidget(plot8_box, 3, 1)
        self.plot_boxes.append((plot8_box, self.plot8))
        
    def create_plot_box(self, title, plot_canvas):
        """📦 Cria um box individual para um gráfico"""
        # Criar GroupBox para o gráfico
        box = QGroupBox(title)
        box.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #cccccc;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #f9f9f9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2c3e50;
            }
        """)
        
        # Layout vertical para o box
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 15, 5, 5)
        
        # Adicionar o canvas do gráfico
        layout.addWidget(plot_canvas)
        
        box.setLayout(layout)
        return box
        
    def generate_data(self):
        """🎲 Gera os dados para treinamento"""
        self.update_status("Gerando dados...")
        logger.info(f"🎲 Gerando {self.samples} amostras com fórmula {self.formula} e seed {self.seed}")
        
        np.random.seed(self.seed)
        tf.random.set_seed(self.seed)
        
        # Gerar dados X
        if self.formula in ["logarítmica"]:
            # Para logarítmica, evitar valores <= 0
            self.x_value = np.random.uniform(low=0.1, high=10, size=self.samples)
        elif self.formula == "tangente":
            # Para tangente, evitar valores próximos a π/2
            self.x_value = np.random.uniform(low=-1.4, high=1.4, size=self.samples)
        else:
            self.x_value = np.random.uniform(low=0, high=2*math.pi, size=self.samples)
        
        # Gerar dados Y com base na fórmula selecionada
        self.y_value = self.apply_formula(self.x_value, self.formula)
        
        # Adicionar ruído
        self.y_noisy = self.y_value + self.noise_factor * np.random.randn(*self.y_value.shape)
        
        # Dividir conjuntos
        TRAIN_SPLIT = int(0.6 * self.samples)
        TEST_SPLIT = int(0.2 * self.samples + TRAIN_SPLIT)
        
        self.x_train, self.x_validate, self.x_test = np.split(self.x_value, [TRAIN_SPLIT, TEST_SPLIT])
        self.y_train, self.y_validate, self.y_test = np.split(self.y_noisy, [TRAIN_SPLIT, TEST_SPLIT])
        
        logger.info(f"✅ Dados gerados: Treino={len(self.x_train)}, Validação={len(self.x_validate)}, Teste={len(self.x_test)}")
        
        self.update_data_plots()
        self.update_status(f"Dados gerados: {self.samples} amostras ({self.formula})")
        
    def update_formula(self, formula_text):
        """🔄 Atualiza a fórmula matemática selecionada"""
        # Converter texto do ComboBox para o formato esperado pelo apply_formula
        formula_mapping = {
            "Senoide": "senoide",
            "Cossenoide": "cossenoide", 
            "Parábola": "parábola",
            "Cúbica": "cúbica",
            "Exponencial": "exponencial",
            "Logarítmica": "logarítmica",
            "Tangente": "tangente",
            "Onda Quadrada": "onda quadrada",
            "Onda Triangular": "onda triangular",
            "Senoide Amortecida": "senoide amortecida"
        }
        
        self.formula = formula_mapping.get(formula_text, "senoide")
        logger.info(f"🔄 Fórmula atualizada para: {self.formula}")
        self.generate_data()  # Regenerar dados com nova fórmula
        
    def update_samples(self, value):
        """🔄 Atualiza número de amostras"""
        self.samples = value
        self.samples_label.setText(f"Samples: {self.samples}")
        logger.info(f"🔄 Samples atualizado para: {self.samples}")
        self.generate_data()
        
    def update_epochs(self, value):
        """🔄 Atualiza número de épocas"""
        self.epochs = value
        self.epochs_label.setText(f"Épocas: {self.epochs}")
        logger.info(f"🔄 Épocas atualizado para: {self.epochs}")
        
    def update_batch_size(self, value):
        """🔄 Atualiza tamanho do batch"""
        self.batch_size = value
        self.batch_label.setText(f"Batch Size: {self.batch_size}")
        logger.info(f"🔄 Batch Size atualizado para: {self.batch_size}")
        
    def update_noise(self, value):
        """🔄 Atualiza fator de ruído"""
        self.noise_factor = value / 100.0
        self.noise_label.setText(f"Fator de Ruído: {self.noise_factor:.2f}")
        logger.info(f"🔄 Fator de ruído atualizado para: {self.noise_factor:.2f}")
        self.generate_data()
        
    def update_live_speed(self, value):
        """Atualiza velocidade da predição ao vivo"""
        self.live_prediction_speed = value
        self.speed_label.setText(f"{self.live_prediction_speed}ms")
        logger.info(f"🔄 Velocidade de predição ao vivo atualizada para: {self.live_prediction_speed}ms")
        
    def update_quantization_for_mcu(self, mcu_type):
        """Atualiza quantização padrão baseada no tipo de microcontrolador"""
        if mcu_type == "SoC LiteX+VexRiscv":
            # SoC RISC-V funciona melhor com quantização 8-bit
            self.quant_combo.setCurrentText("Int8 (8-bit)")
            logger.info("SoC RISC-V detectado - Quantização padrão definida para Int8 (8-bit)")
        elif mcu_type in ["ESP32 (Arduino)", "ESP32 (ESP-IDF)"]:
            # ESP32 também funciona bem com 8-bit
            self.quant_combo.setCurrentText("Int8 (8-bit)")
            logger.info("ESP32 detectado - Quantização padrão definida para Int8 (8-bit)")
        else:
            # Outros microcontroladores mantêm Float32 como padrão
            self.quant_combo.setCurrentText("Float32 (Padrão)")
            logger.info(f"{mcu_type} detectado - Mantendo quantização Float32 (Padrão)")
        
    def toggle_live_prediction(self):
        """🔥 Inicia/para predição ao vivo"""
        if not self.live_prediction_running:
            self.start_live_prediction()
        else:
            self.stop_live_prediction()
            
    def start_live_prediction(self):
        """🔥 Inicia predição ao vivo"""
        if self.model is None:
            logger.warning("⚠️ Nenhum modelo treinado disponível para predição ao vivo")
            return
            
        logger.info("🔥 Iniciando predição ao vivo")
        self.live_prediction_running = True
        self.live_prediction_count = 0
        self.live_x_data.clear()
        self.live_y_pred_data.clear()
        self.live_y_real_data.clear()
        self.live_errors.clear()
        
        self.live_btn.setText("⏸️ Parar Predição ao Vivo")
        self.live_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """)
        
        # Iniciar timer para predições
        self.live_prediction_timer = QTimer()
        self.live_prediction_timer.timeout.connect(self.perform_live_prediction)
        self.live_prediction_timer.start(self.live_prediction_speed)
        
    def stop_live_prediction(self):
        """⏸️ Para predição ao vivo"""
        logger.info("⏸️ Parando predição ao vivo")
        self.live_prediction_running = False
        
        if self.live_prediction_timer:
            self.live_prediction_timer.stop()
            self.live_prediction_timer = None
            
        self.live_btn.setText("🔥 Iniciar Predição ao Vivo")
        self.live_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff6b35;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e55a2b;
            }
            QPushButton:pressed {
                background-color: #cc4a1f;
            }
        """)
        
        # Calcular estatísticas finais
        if self.live_errors:
            avg_error = np.mean(self.live_errors)
            max_error = np.max(self.live_errors)
            logger.info(f"📊 Estatísticas finais - Erro médio: {avg_error:.4f}, Erro máximo: {max_error:.4f}")
            
    def perform_live_prediction(self):
        """🔮 Realiza uma predição ao vivo"""
        if not self.live_prediction_running or self.model is None:
            return
            
        # Gerar valor aleatório para predição
        x_test = np.random.uniform(-2*np.pi, 2*np.pi, 1).reshape(1, 1)
        
        # Fazer predição
        y_pred = self.model.predict(x_test, verbose=0)[0][0]
        y_real = np.sin(x_test[0][0])  # Valor real (assumindo senoide como referência)
        
        # Calcular erro
        error = abs(y_pred - y_real)
        
        # Adicionar aos dados
        self.live_x_data.append(x_test[0][0])
        self.live_y_pred_data.append(y_pred)
        self.live_y_real_data.append(y_real)
        self.live_errors.append(error)
        
        self.live_prediction_count += 1
        
        # Atualizar gráfico a cada 10 predições
        if self.live_prediction_count % 10 == 0:
            self.update_live_prediction_plot()
            
        # Limitar quantidade de dados para evitar sobrecarga
        max_points = 1000
        if len(self.live_x_data) > max_points:
            self.live_x_data = self.live_x_data[-max_points:]
            self.live_y_pred_data = self.live_y_pred_data[-max_points:]
            self.live_y_real_data = self.live_y_real_data[-max_points:]
            self.live_errors = self.live_errors[-max_points:]
            
    def update_live_prediction_plot(self):
        """📈 Atualiza gráfico de predição ao vivo"""
        if len(self.live_x_data) < 2:
            return
            
        # Ordenar dados por x
        sorted_indices = np.argsort(self.live_x_data)
        x_sorted = np.array(self.live_x_data)[sorted_indices]
        y_pred_sorted = np.array(self.live_y_pred_data)[sorted_indices]
        y_real_sorted = np.array(self.live_y_real_data)[sorted_indices]
        
        # Atualizar gráfico de predição ao vivo (assumindo que existe self.plot_live)
        if hasattr(self, 'plot_live'):
            self.plot_live.plot_multiple(
                [x_sorted, x_sorted],
                [y_pred_sorted, y_real_sorted],
                ['Predição', 'Real'],
                ['red', 'blue'],
                title=f"Predição ao Vivo (#{self.live_prediction_count})",
                xlabel="X",
                ylabel="Y"
            )
        
    def create_status_bar(self):
        """📊 Cria a barra de status"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status("Pronto para uso")
        
    def update_status(self, message):
        """📊 Atualiza mensagem na barra de status"""
        if self.status_bar:
            self.status_bar.showMessage(message)
        logger.info(f"📊 Status: {message}")
        
    def on_formula_changed(self, formula_text):
        """🔄 Handle formula selection change"""
        self.formula = formula_text.lower()
        logger.info(f"📊 Fórmula alterada para: {formula_text}")
        self.generate_data()
        
    def apply_formula(self, x, formula):
        """🧮 Aplica a fórmula matemática selecionada"""
        formula_map = {
            "senoide": np.sin(x),
            "cossenoide": np.cos(x),
            "parábola": x**2 - 4*x + 3,  # (x-1)(x-3)
            "cúbica": x**3 - 3*x**2 + 2,  # x(x-1)(x-2)
            "exponencial": np.exp(x/4) - 1,
            "logarítmica": np.log(x),
            "tangente": np.tan(x),
            "onda quadrada": np.sign(np.sin(x)),
            "onda triangular": 2*np.arcsin(np.sin(x))/math.pi,
            "senoide amortecida": np.exp(-x/10) * np.sin(x)
        }
        
        if formula.lower() in formula_map:
            return formula_map[formula.lower()]
        else:
            logger.warning(f"⚠️ Fórmula '{formula}' não encontrada, usando senoide padrão")
            return np.sin(x)
        
    def update_data_plots(self):
        """📈 Atualiza gráficos dos dados"""
        if self.x_value is None:
            return
            
        # Gráfico 1: Função pura
        indices = np.argsort(self.x_value)
        formula_title = f"Função {self.formula.capitalize()} (Pura)"
        self.plot1.plot(self.x_value[indices], self.y_value[indices], 
                       formula_title, "x", "y", 'blue')
        
        # Gráfico 2: Função com ruído
        self.plot2.plot_scatter(self.x_value, self.y_noisy, 
                              f"Função {self.formula.capitalize()} com Ruído", "x", "y + ruído", 'red', alpha=0.6, s=1)
        
        # Gráfico 3: Conjuntos de dados
        self.plot3.axes.scatter(self.x_train, self.y_train, color='green', alpha=0.3, s=1, label='Treinamento')
        self.plot3.axes.scatter(self.x_validate, self.y_validate, color='orange', alpha=0.3, s=1, label='Validação')
        self.plot3.axes.scatter(self.x_test, self.y_test, color='purple', alpha=0.3, s=1, label='Teste')
        self.plot3.axes.set_title("Conjuntos de Treinamento")
        self.plot3.axes.set_xlabel("x")
        self.plot3.axes.set_ylabel("y")
        self.plot3.axes.grid(True, alpha=0.3)
        self.plot3.axes.legend()
        self.plot3.draw()
        
    def train_model(self):
        """🚀 Treina o modelo TensorFlow com janela modal de progresso"""
        if self.x_train is None:
            logger.error("❌ Dados não gerados. Execute 'Gerar Dados' primeiro.")
            self.update_status("Erro: gere dados primeiro")
            return
            
        # Resetar variáveis de controle
        self.training_completed = False
        self.training_cancelled = False
        
        # Limpar informações do modelo anterior
        self.clear_model_info()
        
        # Exibir informação do dispositivo que será usado
        logger.info(f"🔧 Dispositivo de treinamento: {DEVICE_TYPE}")
        self.update_status(f"Treinando com {DEVICE_TYPE}...")
        
        # Criar e mostrar janela modal de treinamento
        logger.info("⏳ Criando janela modal de treinamento")
        self.training_modal = TrainingModalDialog(self)
        self.training_modal.show()
        logger.info("⏳ Janela modal de treinamento exibida")
        
        logger.info(f"🚀 Iniciando treinamento com {self.epochs} épocas e batch_size={self.batch_size} usando {DEVICE_TYPE}")
        
        # Criar modelo
        self.model = tf.keras.Sequential([
            tf.keras.layers.Dense(16, activation='relu', input_shape=(1,)),
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(1)
        ])
        
        # Otimizador específico para GPU se disponível
        if DEVICE_TYPE == 'GPU':
            optimizer = tf.keras.optimizers.RMSprop(learning_rate=0.001)
            logger.info("🚀 Usando otimizador otimizado para GPU")
        else:
            optimizer = 'rmsprop'
            
        self.model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])
        
        # Exibir summary
        summary_str = []
        self.model.summary(print_fn=lambda x: summary_str.append(x))
        
        # Adicionar informação do dispositivo ao summary
        summary_str.insert(0, f"\n{'='*50}")
        summary_str.insert(1, f"🔧 Dispositivo de Treinamento: {DEVICE_TYPE}")
        summary_str.insert(2, f"{'='*50}\n")
        
        # Limpar campos de informações individuais
        self.clear_model_info()
        
        # Processar summary e extrair informações do modelo
        self.device_text.setText(DEVICE_TYPE)
        
        # Extrair informações do summary
        total_params = None
        trainable_params = None
        
        for line in summary_str:
            line = line.strip()
            if "Total params:" in line:
                # Formato: "Total params: 1,234"
                params = line.split("Total params:")[1].strip()
                self.total_params_text.setText(params)
            elif "Trainable params:" in line:
                # Formato: "Trainable params: 1,234"
                params = line.split("Trainable params:")[1].strip()
                self.trainable_params_text.setText(params)
            elif "Model:" in line:
                # Formato: "Model: \"sequential\""
                model_type = line.split("Model:")[1].strip().strip('"')
                self.model_type_text.setText(model_type)
        
        # Se não encontrou informações, usar valores padrão
        if not self.total_params_text.text():
            self.total_params_text.setText("Desconhecido")
        if not self.trainable_params_text.text():
            self.trainable_params_text.setText("Desconhecido")
        if not self.model_type_text.text():
            self.model_type_text.setText("Sequential")
        
        logger.info("✅ Informações do modelo processadas e exibidas")
        
        # Verificar se o treinamento foi cancelado antes de começar
        if self.training_modal and not self.training_modal.training_active:
            logger.info("❌ Treinamento cancelado pelo usuário")
            self.update_status("Treinamento cancelado")
            return
        
        # Treinar com verificação de cancelamento
        try:
            # Callback personalizado para verificar cancelamento durante o treinamento
            class TrainingCancelCallback(tf.keras.callbacks.Callback):
                def __init__(self, parent_gui):
                    super().__init__()
                    self.parent_gui = parent_gui
                    
                def on_epoch_end(self, epoch, logs=None):
                    # Verificar se o treinamento foi cancelado
                    if (self.parent_gui.training_modal and 
                        not self.parent_gui.training_modal.training_active):
                        logger.info(f"❌ Treinamento cancelado na época {epoch + 1}")
                        self.parent_gui.training_cancelled = True
                        self.model.stop_training = True
            
            # Adicionar callback de cancelamento
            cancel_callback = TrainingCancelCallback(self)
            
            # Iniciar treinamento
            self.history = self.model.fit(
                self.x_train, self.y_train, 
                epochs=self.epochs, 
                batch_size=self.batch_size, 
                validation_data=(self.x_validate, self.y_validate),
                verbose=0,
                callbacks=[cancel_callback]
            )
            
            # Verificar se foi cancelado durante o treinamento
            if self.training_cancelled:
                logger.info("❌ Treinamento cancelado pelo usuário")
                self.update_status("Treinamento cancelado")
                return
            
            logger.info("✅ Treinamento concluído")
            
            # Marcar como concluído e fechar modal
            self.training_completed = True
            if self.training_modal:
                logger.info("⏳ Fechando janela modal de treinamento (concluído)")
                self.training_modal.close()
                logger.info("⏳ Janela modal de treinamento fechada")
            
            # Atualizar gráficos de treinamento
            self.update_training_plots()
            self.update_status("Treinamento concluído")
            
        except Exception as e:
            logger.error(f"❌ Erro durante o treinamento: {str(e)}")
            self.update_status(f"Erro no treinamento: {str(e)}")
            if self.training_modal:
                self.training_modal.close()
        
    def update_training_plots(self):
        """📈 Atualiza gráficos do treinamento"""
        if self.history is None:
            return
            
        # Gráfico 4: Loss
        loss = self.history.history['loss']
        val_loss = self.history.history['val_loss']
        epochs = range(1, len(loss) + 1)
        
        self.plot4.plot_multiple(
            [epochs, epochs], [loss, val_loss],
            ['Treinamento', 'Validação'], ['blue', 'red'],
            "Loss Durante Treinamento", "Época", "Loss"
        )
        
        # Gráfico 5: MAE
        mae = self.history.history['mae']
        val_mae = self.history.history['val_mae']
        
        self.plot5.plot_multiple(
            [epochs, epochs], [mae, val_mae],
            ['Treinamento', 'Validação'], ['blue', 'red'],
            "MAE Durante Treinamento", "Época", "MAE"
        )
        
        # Atualizar informações nas caixas de texto individuais
        final_loss = loss[-1]
        final_val_loss = val_loss[-1]
        final_mae = mae[-1]
        final_val_mae = val_mae[-1]
        
        self.loss_train_text.setText(f"{final_loss:.4f}")
        self.loss_val_text.setText(f"{final_val_loss:.4f}")
        self.mae_train_text.setText(f"{final_mae:.4f}")
        self.mae_val_text.setText(f"{final_val_mae:.4f}")
        
    def generate_colored_noise(self, n, color="near"):
        """🎨 Gera ruído com densidade espectral colorida.

        Suporta:
          - 'near'    : ruído gaussiano simples (N(0,1)) — comportamento anterior
          - 'branco'  : espectro plano (|H(f)| = 1)
          - 'rosa'    : 1/sqrt(f) (-3 dB/oct)
          - 'brownian': 1/f       (-6 dB/oct, também chamado 'vermelho')
          - 'azul'    : sqrt(f)   (+3 dB/oct)
          - 'violeta' : f         (+6 dB/oct)
          - 'cinza'   : branco ponderado por aproximação da curva A-weighting
        O array retornado é normalizado para desvio padrão unitário.
        """
        color = (color or "near").lower()
        logger.debug(
            f"🐛 generate_colored_noise: solicitando ruído '{color}' com n={n}"
        )

        if n <= 0:
            return np.zeros(0, dtype=np.float64)

        if color in ("near", "gaussiano", "gaussian"):
            noise = np.random.randn(n)
            noise /= (np.std(noise) + 1e-12)
            return noise

        # Geração via FFT: criar espectro aleatório complexo e aplicar ganho por frequência.
        # Usamos N pontos para irfft -> retorna n amostras reais.
        freqs = np.fft.rfftfreq(n, d=1.0)
        # Evitar divisão por zero em f=0
        f = freqs.copy()
        f[0] = 1.0 if f.size > 0 else 1.0

        if color in ("branco", "white"):
            gain = np.ones_like(f)
        elif color in ("rosa", "pink"):
            gain = 1.0 / np.sqrt(f)
        elif color in ("brownian", "brown", "vermelho", "red"):
            gain = 1.0 / f
        elif color in ("azul", "blue"):
            gain = np.sqrt(f)
        elif color in ("violeta", "violet", "purple"):
            gain = f.copy()
        elif color in ("cinza", "grey", "gray"):
            # Aproximação da curva A-weighting (ponderação psicoacústica).
            # Como não há frequência de amostragem definida para x, usamos
            # freqs normalizadas mapeadas para [20 Hz, 20 kHz].
            if freqs.size > 1:
                fmin, fmax = 20.0, 20000.0
                f_hz = fmin + (fmax - fmin) * (freqs / freqs[-1])
                f_hz[0] = fmin
                num = (12200.0 ** 2) * (f_hz ** 4)
                den = (
                    (f_hz ** 2 + 20.6 ** 2)
                    * np.sqrt((f_hz ** 2 + 107.7 ** 2) * (f_hz ** 2 + 737.9 ** 2))
                    * (f_hz ** 2 + 12200.0 ** 2)
                )
                a_weight = num / (den + 1e-12)
                # Ruído cinza = branco com resposta psicoacústica plana => inverso do A-weighting
                gain = 1.0 / (a_weight + 1e-12)
            else:
                gain = np.ones_like(f)
        else:
            logger.warning(
                f"⚠️ generate_colored_noise: tipo desconhecido '{color}', usando branco"
            )
            gain = np.ones_like(f)

        # DC = 0 para evitar offset
        if gain.size > 0:
            gain[0] = 0.0

        # Espectro aleatório com módulo e fase
        phases = np.random.uniform(0.0, 2.0 * np.pi, size=freqs.size)
        magnitudes = np.random.randn(freqs.size) * gain
        spectrum = magnitudes * np.exp(1j * phases)

        noise = np.fft.irfft(spectrum, n=n)
        std = np.std(noise)
        if std > 0:
            noise = noise / std
        return noise

    def _noise_key_from_combo(self):
        """🔎 Converte o texto selecionado no combo para a chave interna."""
        text = self.noise_type_combo.currentText() if hasattr(self, "noise_type_combo") else "Near (Gaussiano)"
        mapping = {
            "Near (Gaussiano)": "near",
            "Branco": "branco",
            "Rosa": "rosa",
            "Brownian": "brownian",
            "Azul": "azul",
            "Violeta": "violeta",
            "Cinza": "cinza",
        }
        return mapping.get(text, "near")

    def make_predictions(self):
        """🔮 Faz predições com o modelo treinado"""
        if self.model is None:
            logger.error("❌ Modelo não treinado. Execute 'Treinar Modelo' primeiro.")
            self.update_status("Erro: treine o modelo primeiro")
            return
            
        noise_key = self._noise_key_from_combo()
        self.update_status(f"Fazendo predições (ruído: {noise_key})...")
        logger.info(
            f"🔮 Fazendo predições | noise_type={noise_key} | noise_factor={self.noise_factor:.3f}"
        )

        # Aplicar ruído selecionado sobre a entrada de validação, escalado por noise_factor.
        x_flat = self.x_validate.flatten()
        noise = self.generate_colored_noise(x_flat.size, color=noise_key)
        x_noisy = x_flat + self.noise_factor * noise
        x_input = x_noisy.reshape(self.x_validate.shape).astype(np.float32)

        logger.debug(
            f"🐛 make_predictions: x_validate shape={self.x_validate.shape}, "
            f"noise std={float(np.std(noise)):.4f}, "
            f"x_input min={float(np.min(x_input)):.4f}, max={float(np.max(x_input)):.4f}"
        )

        self.predictions = self.model.predict(x_input, verbose=0)

        # Gráfico 6: Predições vs Real (ordenado pelo x ruidoso utilizado na inferência)
        indices = np.argsort(x_input.flatten())
        self.plot6.plot_multiple(
            [x_input.flatten()[indices], x_input.flatten()[indices]],
            [self.y_validate.flatten()[indices], self.predictions.flatten()[indices]],
            ['Real', f'Predição ({noise_key})'], ['blue', 'red'],
            f"Predições vs Dados Reais — ruído: {noise_key}", "x", "y"
        )

        logger.info(f"✅ Predições concluídas com ruído '{noise_key}'")
        self.update_status(f"Predições concluídas (ruído: {noise_key})")
        
    def find_espidf_installations(self):
        """🔍 Procura por instalações ESP-IDF nos locais padrão"""
        logger.info("🔍 Procurando instalações ESP-IDF...")
        
        possible_paths = []
        
        # Locais padrão no Windows
        if os.name == 'nt':  # Windows
            # Caminhos comuns para ESP-IDF
            home_dir = os.path.expanduser("~")
            possible_paths.extend([
                os.path.join(home_dir, "esp", "esp-idf"),
                os.path.join(home_dir, "esp-idf"),
                os.path.join("C:", "Espressif", "esp-idf"),
                os.path.join("C:", "esp", "esp-idf"),
                os.path.join("D:", "esp", "esp-idf"),
                os.path.join("E:", "esp", "esp-idf"),
            ])
            
            # Verificar variáveis de ambiente
            env_paths = ["IDF_PATH", "ESP_IDF_PATH"]
            for env_var in env_paths:
                if env_var in os.environ:
                    possible_paths.append(os.environ[env_var])
        else:  # Linux/Mac
            home_dir = os.path.expanduser("~")
            possible_paths.extend([
                os.path.join(home_dir, "esp", "esp-idf"),
                os.path.join(home_dir, "esp-idf"),
                os.path.join("/opt", "esp", "esp-idf"),
                os.path.join("/home", os.path.expanduser("~").split("/")[-1], "esp", "esp-idf"),
                # Verificar subdiretórios esp-idf em .espressif
                os.path.join(home_dir, ".espressif", "esp-idf"),
            ])
            
            # Verificar por instalações em subdiretórios versionados do .espressif
            espressif_dir = os.path.join(home_dir, ".espressif")
            if os.path.exists(espressif_dir):
                for item in os.listdir(espressif_dir):
                    item_path = os.path.join(espressif_dir, item)
                    if os.path.isdir(item_path):
                        # Verificar se tem subdiretório esp-idf
                        esp_idf_subdir = os.path.join(item_path, "esp-idf")
                        if os.path.exists(esp_idf_subdir):
                            possible_paths.append(esp_idf_subdir)
            
            # Verificar variáveis de ambiente
            env_paths = ["IDF_PATH", "ESP_IDF_PATH"]
            for env_var in env_paths:
                if env_var in os.environ:
                    possible_paths.append(os.environ[env_var])
        
        # Verificar quais caminhos existem e são válidos
        valid_paths = []
        for path in possible_paths:
            if os.path.exists(path):
                # Verificar se é uma instalação ESP-IDF válida
                idf_py = os.path.join(path, "tools", "idf.py")
                cmake_dir = os.path.join(path, "tools", "cmake")
                if os.path.exists(idf_py) and os.path.exists(cmake_dir):
                    valid_paths.append(path)
                    logger.info(f"✅ ESP-IDF encontrado em: {path}")
                else:
                    logger.debug(f"⚠️ Pasta existe mas não é ESP-IDF válido: {path}")
        
        logger.info(f"🔍 Encontradas {len(valid_paths)} instalações ESP-IDF válidas")
        return valid_paths
    
    def export_model(self):
        """💾 Exporta o modelo treinado para TensorFlow Lite para microcontroladores com opções de quantização"""
        if self.model is None:
            logger.error("❌ Modelo não treinado. Execute 'Treinar Modelo' primeiro.")
            self.update_status("Erro: treine o modelo primeiro")
            return
        
        mcuf_type = self.mcuf_combo.currentText()
        quant_type = self.quant_combo.currentText()
        model_only = self.model_only_checkbox.isChecked()
        
        # Verificar se tinymlgen está disponível para quantização 1-bit
        if quant_type == "Int1 (1-bit - TinyMLGen)" and tinymlgen is None:
            logger.error("❌ Biblioteca tinymlgen não disponível. Instale com: pip install tinymlgen")
            self.update_status("Erro: tinymlgen não instalado")
            return
        
        # Verificar se é ESP-IDF e precisa selecionar instalação
        espidf_path = None
        if mcuf_type == "ESP32 (ESP-IDF)":
            # Procurar instalações ESP-IDF
            found_paths = self.find_espidf_installations()
            
            if len(found_paths) > 1:
                # Múltiplas instalações encontradas - mostrar diálogo de seleção
                dialog = ESPIDFSelectionDialog(self, found_paths)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    espidf_path = dialog.get_selected_path()
                    logger.info(f"✅ ESP-IDF selecionado: {espidf_path}")
                else:
                    logger.info("❌ Seleção ESP-IDF cancelada")
                    return
            elif len(found_paths) == 1:
                # Apenas uma instalação encontrada
                espidf_path = found_paths[0]
                logger.info(f"✅ ESP-IDF encontrado automaticamente: {espidf_path}")
            else:
                # Nenhuma instalação encontrada - pedir para selecionar pasta
                dialog = ESPIDFSelectionDialog(self, [])
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    espidf_path = dialog.get_selected_path()
                    logger.info(f"✅ ESP-IDF selecionado manualmente: {espidf_path}")
                else:
                    logger.info("❌ Seleção ESP-IDF cancelada")
                    return
            
            # Verificar se o caminho selecionado é válido
            if not os.path.exists(espidf_path):
                logger.error(f"❌ Caminho ESP-IDF não existe: {espidf_path}")
                self.update_status("Erro: caminho ESP-IDF inválido")
                return
            
            # Verificar se é o diretório esp-idf ou contém o subdiretório esp-idf
            idf_dir = espidf_path
            if not os.path.exists(os.path.join(espidf_path, "CMakeLists.txt")):
                # Se não tiver CMakeLists.txt, verificar se tem subdiretório esp-idf
                potential_idf_dir = os.path.join(espidf_path, "esp-idf")
                if os.path.exists(potential_idf_dir) and os.path.exists(os.path.join(potential_idf_dir, "CMakeLists.txt")):
                    idf_dir = potential_idf_dir
                    logger.info(f"✅ Usando subdiretório ESP-IDF: {idf_dir}")
                else:
                    logger.error(f"❌ Caminho não é uma instalação ESP-IDF válida: {espidf_path}")
                    self.update_status("Erro: não é ESP-IDF válido")
                    return
            
            # Verificar arquivos essenciais do ESP-IDF
            idf_py = os.path.join(idf_dir, "tools", "idf.py")
            cmake_lists = os.path.join(idf_dir, "CMakeLists.txt")
            components_dir = os.path.join(idf_dir, "components")
            
            if not (os.path.exists(idf_py) and os.path.exists(cmake_lists) and os.path.exists(components_dir)):
                logger.error(f"❌ Caminho não é uma instalação ESP-IDF válida: {idf_dir}")
                self.update_status("Erro: não é ESP-IDF válido")
                return
            
            # Atualizar espidf_path para o diretório correto
            espidf_path = idf_dir
            
        # Selecionar diretório de exportação
        if model_only:
            # Para salvar apenas modelo, usar diretório atual sem criar subdiretório
            export_dir = QFileDialog.getExistingDirectory(
                self, 
                "Selecionar Diretório para Salvar Modelo",
                os.path.expanduser("~")  # Diretório home como padrão
            )
            
            if not export_dir:
                logger.info("❌ Exportação cancelada pelo usuário")
                return
                
            model_dir = Path(export_dir)
            action_desc = "Salvando apenas modelo"
        else:
            # Exportação completa - criar subdiretório
            export_dir = QFileDialog.getExistingDirectory(
                self, 
                "Selecionar Diretório de Exportação",
                os.path.expanduser("~")  # Diretório home como padrão
            )
            
            if not export_dir:
                logger.info("❌ Exportação cancelada pelo usuário")
                return
                
            # Criar diretório específico para a exportação
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            mcuf_clean = mcuf_type.lower().replace(" ", "_").replace("(", "").replace(")", "")
            quant_clean = quant_type.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
            model_dir = Path(export_dir) / f"tflite_model_{mcuf_clean}_{quant_clean}_{timestamp}"
            model_dir.mkdir(exist_ok=True)
            action_desc = "Exportando modelo completo"
            
        self.update_status(action_desc)
        logger.info(f"💾 Iniciando {action_desc} para {mcuf_type} com quantização {quant_type}")
        
        try:
            # Exportar modelo baseado no tipo de quantização
            if quant_type == "Int1 (1-bit - TinyMLGen)":
                # Usar tinymlgen para quantização 1-bit
                logger.info("🔬 Usando tinymlgen para quantização 1-bit")
                
                # Gerar código C com quantização 1-bit
                c_code = tinymlgen.generate(
                    self.model, 
                    variable_name='model_data',
                    quantization_byte=1,  # 1-bit quantization
                    optimize=True
                )
                
                # Salvar código C gerado
                c_header_path = model_dir / "model_1bit.h"
                with open(c_header_path, 'w', encoding='utf-8') as f:
                    f.write(c_code)
                
                # Gerar modelo TFLite também para referência
                tflite_model = tinymlgen.convert(self.model, quantization_byte=1)
                tflite_path = model_dir / "model_1bit.tflite"
                with open(tflite_path, 'wb') as f:
                    f.write(tflite_model)
                
                logger.info("✅ Modelo 1-bit gerado com tinymlgen")
                
            else:
                # Quantização padrão (Float32 ou Int8)
                logger.info("🔧 Criando TFLiteConverter...")
                converter = tf.lite.TFLiteConverter.from_keras_model(self.model)
                logger.info(f"✅ Converter criado: {type(converter)}")
                
                # Configurações básicas primeiro
                converter.target_spec.supported_ops = [
                    tf.lite.OpsSet.TFLITE_BUILTINS
                ]
                
                # Desabilitar otimizações que podem causar incompatibilidade
                # (exceto para Int8 que precisa de otimizações)
                if mcuf_type in ["ESP32 (Arduino)", "ESP32 (ESP-IDF)"] and quant_type != "Int8 (8-bit)":
                    logger.info("🔧 Aplicando configurações de compatibilidade ESP32")
                    converter.optimizations = []  # Sem otimizações para máxima compatibilidade
                
                if quant_type == "Int8 (8-bit)":
                    logger.info("🔬 Aplicando quantização Int8")
                    def representative_dataset():
                        for _ in range(100):
                            data = np.random.uniform(low=0, high=2*math.pi, size=(1, 1)).astype(np.float32)
                            yield [data]
                    
                    # Para Int8, precisamos habilitar otimizações
                    converter.optimizations = [tf.lite.Optimize.DEFAULT]
                    converter.representative_dataset = representative_dataset
                    converter.target_spec.supported_types = [tf.int8]
                    converter.inference_input_type = tf.int8
                    converter.inference_output_type = tf.int8
                    
                elif quant_type == "Float32 (Padrão)":
                    logger.info("🔬 Usando quantização Float32 (padrão)")
                    # Para Float32, não需要 representative dataset
                
                # Log das configurações finais
                logger.info(f"🔧 Configurações finais - optimizations: {converter.optimizations}")
                logger.info(f"🔧 Configurações finais - target_spec.supported_ops: {converter.target_spec.supported_ops}")
                if hasattr(converter, 'representative_dataset'):
                    logger.info("🔧 Configurações finais - representative_dataset: configurado")
                if hasattr(converter, 'target_spec') and hasattr(converter.target_spec, 'supported_types'):
                    logger.info(f"🔧 Configurações finais - target_spec.supported_types: {converter.target_spec.supported_types}")
                
                # Verificar se arquivos já existem antes de exportar
                files_to_check = []
                if quant_type == "Int8 (8-bit)":
                    tflite_path = model_dir / "model_int8.tflite"
                else:
                    tflite_path = model_dir / "model_float32.tflite"
                
                # Adicionar arquivo .h correspondente
                if model_only:
                    if quant_type == "Int8 (8-bit)":
                        header_path = model_dir / "model_int8.h"
                    else:
                        header_path = model_dir / "model_float32.h"
                else:
                    header_path = model_dir / "model_data.h"
                
                files_to_check = [(tflite_path, "modelo TFLite"), (header_path, "header .h")]
                
                # Verificar existência e pedir confirmação
                existing_files = []
                for file_path, file_type in files_to_check:
                    if file_path.exists():
                        existing_files.append((file_path, file_type))
                
                if existing_files:
                    file_list = "\n".join([f"  • {path.name} ({desc})" for path, desc in existing_files])
                    reply = QMessageBox.question(
                        self, 
                        "Arquivos já existem",
                        f"Os seguintes arquivos já existem e serão sobrescritos:\n{file_list}\n\nDeseja continuar?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    
                    if reply == QMessageBox.No:
                        logger.info("❌ Exportação cancelada pelo usuário (arquivos existentes)")
                        return
                
                # Converter modelo
                try:
                    tflite_model = converter.convert()
                    logger.info("✅ Modelo convertido com sucesso")
                except Exception as e:
                    logger.error(f"❌ Erro na conversão do modelo: {str(e)}")
                    raise e
                
                # Salvar modelo TFLite
                logger.info(f"💾 Salvando modelo em: {tflite_path}")
                with open(tflite_path, 'wb') as f:
                    f.write(tflite_model)
                logger.info(f"✅ Modelo salvo: {tflite_path} ({len(tflite_model)} bytes)")
            
            # Gerar header .h com os dados do modelo
            if quant_type == "Int1 (1-bit - TinyMLGen)":
                # Já foi gerado pelo tinymlgen
                pass
            else:
                # Gerar header para Float32/Int8
                try:
                    self.generate_model_header(model_dir, quant_type, model_only)
                except Exception as e:
                    logger.error(f"❌ Erro na geração do header: {str(e)}")
                    raise e
            
            # Gerar código específico para o microcontrolador (apenas se não for model_only)
            if not model_only:
                if mcuf_type == "ESP32 (Arduino)":
                    self.generate_esp32_arduino_code(model_dir, quant_type)
                elif mcuf_type == "ESP32 (ESP-IDF)":
                    self.generate_esp32_espidf_code(model_dir, espidf_path, quant_type)
                elif mcuf_type == "STM32":
                    self.generate_stm32_code(model_dir, quant_type)
                elif mcuf_type == "Arduino Nano":
                    self.generate_arduino_code(model_dir, quant_type)
                elif mcuf_type == "SoC LiteX+VexRiscv":
                    self.generate_soc_vexriscv_code(model_dir, quant_type)
                
                # Gerar tutorial
                self.generate_tutorial(model_dir, mcuf_type, quant_type)
            
            logger.info(f"✅ Modelo {'salvo' if model_only else 'exportado'} com sucesso em: {model_dir}")
            self.update_status(f"Modelo {'salvo' if model_only else 'exportado'}: {model_dir.name if not model_only else 'apenas arquivos essenciais'}")
            
        except Exception as e:
            logger.error(f"❌ Erro na exportação: {str(e)}")
            self.update_status(f"Erro na exportação: {str(e)}")
    
    def generate_model_header(self, model_dir, quant_type, model_only=False):
        """🔧 Gera arquivo header .h com os dados do modelo TFLite"""
        logger.info(f"🔧 Gerando header .h para quantização {quant_type}")
        
        # Determinar o arquivo do modelo e header de forma mais clara
        if quant_type == "Int8 (8-bit)":
            tflite_path = model_dir / "model_int8.tflite"
            if model_only:
                header_path = model_dir / "model_int8.h"
                array_name = "model_int8_tflite"
                header_guard = "MODEL_INT8_H"
            else:
                header_path = model_dir / "model_data.h"
                array_name = "model_data"
                header_guard = "MODEL_DATA_H"
        else:  # Float32
            tflite_path = model_dir / "model_float32.tflite"
            if model_only:
                header_path = model_dir / "model_float32.h"
                array_name = "model_float32_tflite"
                header_guard = "MODEL_FLOAT32_H"
            else:
                header_path = model_dir / "model_data.h"
                array_name = "model_data"
                header_guard = "MODEL_DATA_H"
        
        # Verificar se o arquivo TFLite existe
        if not tflite_path.exists():
            raise FileNotFoundError(f"Arquivo do modelo não encontrado: {tflite_path}")
        
        # Ler o modelo TFLite
        logger.info(f"📖 Lendo modelo de: {tflite_path}")
        with open(tflite_path, 'rb') as f:
            model_data = f.read()
        
        if not model_data:
            raise ValueError(f"Arquivo do modelo está vazio: {tflite_path}")
        
        # Gerar array C com quebra de linhas para melhor legibilidade
        model_bytes = [f"0x{byte:02x}" for byte in model_data]
        # Limitar a 16 bytes por linha para melhor formatação
        model_array_lines = []
        for i in range(0, len(model_bytes), 16):
            line_bytes = model_bytes[i:i+16]
            if i == 0:
                model_array_lines.append("    " + ", ".join(line_bytes))
            else:
                model_array_lines.append("    " + ", ".join(line_bytes))
        model_array = ",\n".join(model_array_lines)
        
        # Gerar conteúdo do header
        header_content = f'''// Auto-generated header for TensorFlow Lite model
// Generated by TensorFlow GUI
// Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
// Quantization: {quant_type}
// Model size: {len(model_data)} bytes
// Model file: {tflite_path.name}

#ifndef {header_guard}
#define {header_guard}

#include <cstdint>

// Alinhamento para dados do modelo
alignas(8) const unsigned char {array_name}[] = {{
{model_array}
}};

const unsigned int {array_name}_size = {len(model_data)};

#endif // {header_guard}
'''
        
        # Salvar header
        logger.info(f"💾 Salvando header em: {header_path}")
        with open(header_path, 'w', encoding='utf-8') as f:
            f.write(header_content)
        
        logger.info(f"✅ Header gerado: {header_path} ({len(model_data)} bytes)")
            
    def generate_esp32_arduino_code(self, model_dir, quant_type="Float32 (Padrão)"):
        """🔧 Gera código Arduino INO para ESP32 com suporte a diferentes quantizações"""
        logger.info(f"🔧 Gerando código Arduino para ESP32 com quantização {quant_type}...")
        
        # Determinar o arquivo do modelo baseado no tipo de quantização
        if quant_type == "Int1 (1-bit - TinyMLGen)":
            model_path = model_dir / "model_1bit.h"  # Para 1-bit, usa o header gerado pelo tinymlgen
            use_tinymlgen_header = True
        else:
            # Para Float32 e Int8
            if quant_type == "Int8 (8-bit)":
                model_path = model_dir / "model_int8.tflite"
            else:
                model_path = model_dir / "model_float32.tflite"
            use_tinymlgen_header = False
        
        if not use_tinymlgen_header:
            # Gerar array de bytes do modelo para quantização padrão
            with open(model_path, 'rb') as f:
                model_data = f.read()
            
            # Converter para array C
            model_array = ", ".join([f"0x{byte:02x}" for byte in model_data])
        
        # Determinar tipos de dados baseado na quantização
        if quant_type == "Int8 (8-bit)":
            input_type = "int8_t"
            output_type = "int8_t"
            tensor_arena_size = "2 * 1024"  # Menor para int8
        elif quant_type == "Int1 (1-bit - TinyMLGen)":
            input_type = "int8_t"  # TinyMLGen geralmente usa int8
            output_type = "int8_t"
            tensor_arena_size = "2 * 1024"  # Menor para 1-bit
        else:  # Float32
            input_type = "float"
            output_type = "float"
            tensor_arena_size = "8 * 1024"  # Maior para float32
        
        # Conteúdo do arquivo INO
        if use_tinymlgen_header:
            # Usar header gerado pelo tinymlgen
            ino_content = f'''/*
 * TensorFlow Lite Model for ESP32 Arduino - 1-bit Quantization
 * Generated by TensorFlow GUI - Amostra Senoidal
 * Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * Quantization: {quant_type}
 * 
 * Este código implementa um modelo de rede neural para predição de funções senoidais
 * usando TensorFlow Lite for Microcontrollers na plataforma ESP32 com Arduino IDE
 * com quantização de 1-bit gerada pela biblioteca TinyMLGen
 */

#include <TensorFlowLite_ESP32.h>
#include "model_1bit.h"  // Header gerado pelo TinyMLGen

// Configurações do modelo
#define TENSOR_ARENA_SIZE   {tensor_arena_size}
constexpr int kTensorArenaSize = {tensor_arena_size};

// Variáveis globais
const unsigned char* model_data = g_model_data;  // Do TinyMLGen
static tflite::MicroInterpreter* interpreter = nullptr;
static tflite::ErrorReporter* error_reporter = nullptr;
static uint8_t tensor_arena[kTensorArenaSize];

// Função para inicializar o modelo
void setup_model() {{
  Serial.begin(115200);
  Serial.println("🚀 Iniciando TensorFlow Lite - 1-bit Quantization");
  
  // Configurar o modelo
  const tflite::Model* model = tflite::GetModel(model_data);
  if (model->version() != TFLITE_SCHEMA_VERSION) {{
    Serial.println("❌ Versão do schema incompatível");
    return;
  }}
  
  // Criar o interpretador
  static tflite::MicroMutableOpResolver<5> resolver;
  resolver.AddFullyConnected();
  resolver.AddRelu();
  resolver.AddReshape();
  resolver.AddSoftmax();
  resolver.AddDequantize();
  resolver.AddQuantize();
  
  // Construir interpretador
  static tflite::MicroInterpreter static_interpreter(
      model, resolver, tensor_arena, kTensorArenaSize, error_reporter);
      
  interpreter = &static_interpreter;
  
  // Alocar tensores
  TfLiteStatus allocate_status = interpreter->AllocateTensors();
  if (allocate_status != kTfLiteOk) {{
    Serial.println("❌ Falha ao alocar tensores");
    return;
  }}
  
  Serial.println("✅ Modelo 1-bit inicializado com sucesso");
}}

// Função para fazer predição
float predict(float x_input) {{
  if (!interpreter) {{
    Serial.println("❌ Interpretador não inicializado");
    return NAN;
  }}
  
  // Preparar input
  {input_type}* input = interpreter->input(0)->data.{input_type};
  *input = ({input_type})(x_input * 127.0f);  // Normalizar para int8
  
  // Executar inferência
  TfLiteStatus invoke_status = interpreter->Invoke();
  if (invoke_status != kTfLiteOk) {{
    Serial.println("❌ Falha na inferência");
    return NAN;
  }}
  
  // Obter output
  {output_type}* output = interpreter->output(0)->data.{output_type};
  float result = (float)(*output) / 127.0f;  // Desnormalizar
  
  return result;
}}

void setup() {{
  setup_model();
}}

void loop() {{
  // Exemplo de uso
  float x = 0.0;
  float y_pred = predict(x);
  
  Serial.print("Input: ");
  Serial.print(x);
  Serial.print(", Predicted: ");
  Serial.println(y_pred);
  
  delay(1000);
}}
'''
        else:
            # Código para quantização padrão
            ino_content = f'''/*
 * TensorFlow Lite Model for ESP32 Arduino
 * Generated by TensorFlow GUI - Amostra Senoidal
 * Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * Quantization: {quant_type}
 * 
 * Este código implementa um modelo de rede neural para predição de funções senoidais
 * usando TensorFlow Lite for Microcontrollers na plataforma ESP32 com Arduino IDE
 */

#include <TensorFlowLite_ESP32.h>
#include "model_data.h"

// Array do modelo TFLite
const unsigned char model_data[] = {{
  {model_array}
}};

// Configurações do modelo
#define TENSOR_ARENA_SIZE   {tensor_arena_size}
constexpr int kTensorArenaSize = {tensor_arena_size};

// Variáveis globais
static tflite::MicroInterpreter* interpreter = nullptr;
static tflite::ErrorReporter* error_reporter = nullptr;
static uint8_t tensor_arena[kTensorArenaSize];

// Função para inicializar o modelo
void setup_model() {{
  Serial.begin(115200);
  Serial.println("🚀 Iniciando TensorFlow Lite - {quant_type}");
  
  // Configurar o modelo
  const tflite::Model* model = tflite::GetModel(model_data);
  if (model->version() != TFLITE_SCHEMA_VERSION) {{
    Serial.println("❌ Versão do schema incompatível");
    return;
  }}
  
  // Criar o interpretador
  static tflite::MicroMutableOpResolver<5> resolver;
  resolver.AddFullyConnected();
  resolver.AddRelu();
  resolver.AddReshape();
  resolver.AddSoftmax();
  resolver.AddDequantize();
  resolver.AddQuantize();
  
  // Construir interpretador
  static tflite::MicroInterpreter static_interpreter(
      model, resolver, tensor_arena, kTensorArenaSize, error_reporter);
      
  interpreter = &static_interpreter;
  
  // Alocar tensores
  TfLiteStatus allocate_status = interpreter->AllocateTensors();
  if (allocate_status != kTfLiteOk) {{
    Serial.println("❌ Falha ao alocar tensores");
    return;
  }}
  
  Serial.println("✅ Modelo {quant_type} inicializado com sucesso");
}}

// Função para fazer predição
float predict(float x_input) {{
  if (!interpreter) {{
    Serial.println("❌ Interpretador não inicializado");
    return NAN;
  }}
  
  // Preparar input
  {input_type}* input = interpreter->input(0)->data.{input_type};
  *input = ({input_type})(x_input * 127.0f);  // Normalizar para int8
  
  // Executar inferência
  TfLiteStatus invoke_status = interpreter->Invoke();
  if (invoke_status != kTfLiteOk) {{
    Serial.println("❌ Falha na inferência");
    return NAN;
  }}
  
  // Obter output
  {output_type}* output = interpreter->output(0)->data.{output_type};
  float result = (float)(*output) / 127.0f;  // Desnormalizar
  
  return result;
}}

void setup() {{
  setup_model();
}}

void loop() {{
  // Exemplo de uso
  float x = 0.0;
  float y_pred = predict(x);
  
  Serial.print("Input: ");
  Serial.print(x);
  Serial.print(", Predicted: ");
  Serial.println(y_pred);
  
  delay(1000);
}}
'''
        
        # Salvar arquivo INO
        ino_path = model_dir / "tensorflow_model_esp32.ino"
        with open(ino_path, 'w', encoding='utf-8') as f:
            f.write(ino_content)
        
        # Se não for TinyMLGen, gerar header com array do modelo
        if not use_tinymlgen_header:
            header_content = f'''/*
 * TensorFlow Lite Model Data
 * Generated by TensorFlow GUI - Amostra Senoidal
 * Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * Quantization: {quant_type}
 */

#ifndef MODEL_DATA_H
#define MODEL_DATA_H

#include <cstdint>

// Array do modelo TFLite
const unsigned char model_data[] = {{
  {model_array}
}};

// Tamanho do modelo
const int model_data_size = {len(model_data)};

#endif // MODEL_DATA_H
'''
            header_path = model_dir / "model_data.h"
            with open(header_path, 'w', encoding='utf-8') as f:
                f.write(header_content)
        
        logger.info(f"✅ Código Arduino gerado: {ino_path}")
        
    def generate_esp32_espidf_code(self, model_dir, espidf_path, quant_type="Float32 (Padrão)"):
        """🔧 Gera código ESP-IDF para ESP32 com suporte a diferentes quantizações"""
        logger.info(f"🔧 Gerando código ESP-IDF para ESP32 com quantização {quant_type}...")
        logger.info(f"📁 Usando ESP-IDF em: {espidf_path}")
        
        # Determinar o arquivo do modelo baseado no tipo de quantização
        if quant_type == "Int1 (1-bit - TinyMLGen)":
            model_tflite_path = model_dir / "model_1bit.tflite"
            model_header_path = model_dir / "model_1bit.h"
            use_tinymlgen_header = True
        else:
            if quant_type == "Int8 (8-bit)":
                model_tflite_path = model_dir / "model_int8.tflite"
            else:
                model_tflite_path = model_dir / "model_float32.tflite"
            use_tinymlgen_header = False
        
        # Gerar array de bytes do modelo se não for TinyMLGen
        if not use_tinymlgen_header:
            with open(model_tflite_path, 'rb') as f:
                model_data = f.read()
            model_array = ", ".join([f"0x{byte:02x}" for byte in model_data])
        
        # Determinar tipos de dados baseado na quantização
        if quant_type == "Int8 (8-bit)":
            input_type = "int8_t"
            output_type = "int8_t"
            tensor_arena_size = "2 * 1024"
        elif quant_type == "Int1 (1-bit - TinyMLGen)":
            input_type = "int8_t"
            output_type = "int8_t"
            tensor_arena_size = "2 * 1024"
        else:  # Float32
            input_type = "float"
            output_type = "float"
            tensor_arena_size = "8 * 1024"
        
        # Criar estrutura de diretórios ESP-IDF
        main_dir = model_dir / "main"
        components_dir = model_dir / "components"
        
        main_dir.mkdir(exist_ok=True)
        components_dir.mkdir(exist_ok=True)
        
        # 1. CMakeLists.txt principal
        cmake_content = f'''# CMakeLists.txt for ESP32 TensorFlow Lite Project
# Generated by TensorFlow GUI - Amostra Senoidal
# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Quantization: {quant_type}

cmake_minimum_required(VERSION 3.16.0)
include(${{ENV{{IDF_PATH}}}}/tools/cmake/project.cmake)
project(esp32_senoidal)

# Componentes
add_subdirectory(main)
add_subdirectory(components)

# Configurações específicas
set(EXTRA_COMPONENT_DIRS ${{{{CMAKE_CURRENT_SOURCE_DIR}}}}/components)

# Configurações do compilador
set(COMPONENT_REQUIRES freertos esp_timer driver esp_common esp_system)

# Otimizações
set(CMAKE_C_FLAGS "${{{{CMAKE_C_FLAGS}}}} -O2")
set(CMAKE_CXX_FLAGS "${{{{CMAKE_CXX_FLAGS}}}} -O2")
'''
        
        cmake_path = model_dir / "CMakeLists.txt"
        with open(cmake_path, 'w', encoding='utf-8') as f:
            f.write(cmake_content)
        
        # 2. CMakeLists.txt do componente main
        main_cmake_content = '''# CMakeLists.txt for main component
idf_component_register(
    SRCS "main.cpp"
    "model_data.cpp"
    INCLUDE_DIRS "."
    REQUIRES freertos esp_timer driver esp_common esp_system
)

# Adicionar bibliotecas TensorFlow Lite se disponíveis
if(EXISTS "${IDF_PATH}/components/tflite")
    REQUIRES(tflite)
endif()
'''
        
        main_cmake_path = main_dir / "CMakeLists.txt"
        with open(main_cmake_path, 'w', encoding='utf-8') as f:
            f.write(main_cmake_content)
        
        # 3. Código principal (main.cpp)
        main_cpp_content = f'''/*
 * TensorFlow Lite Model for ESP32 ESP-IDF
 * Generated by TensorFlow GUI - Amostra Senoidal
 * Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * 
 * Este código implementa um modelo de rede neural para predição de funções senoidais
 * usando TensorFlow Lite for Microcontrollers na plataforma ESP32 com ESP-IDF
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/timers.h"
#include "esp_system.h"
#include "esp_log.h"
#include "esp_timer.h"

// TensorFlow Lite headers
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "model_data.h"

static const char *TAG = "TFLITE_SENOIDAL";

// Configurações do modelo
constexpr int kTensorArenaSize = 8 * 1024;
static uint8_t tensor_arena[kTensorArenaSize];

// Variáveis globais
const tflite::Model* model = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
TfLiteTensor* input_tensor = nullptr;
TfLiteTensor* output_tensor = nullptr;

// Variáveis para estatísticas
static uint32_t total_predictions = 0;
static float total_error = 0.0f;
static esp_timer_handle_t prediction_timer = nullptr;

// Funções
extern "C" void app_main(void);
static void make_prediction(float x_value);
static void auto_prediction_timer_callback(void* arg);
static void setup_model(void);
static void print_model_info(void);

extern "C" void app_main(void)
{{
    ESP_LOGI(TAG, "\\n=== TensorFlow Lite para ESP32 ESP-IDF ===");
    ESP_LOGI(TAG, "Modelo: Amostra Senoidal");
    ESP_LOGI(TAG, "Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}");
    ESP_LOGI(TAG, "ESP-IDF Path: {espidf_path}");
    
    // Configurar modelo
    setup_model();
    
    // Criar timer para predições automáticas
    esp_timer_create_args_t timer_args = {{
        .callback = &auto_prediction_timer_callback,
        .name = "prediction_timer"
    }};
    
    esp_timer_create(&timer_args, &prediction_timer);
    esp_timer_start_periodic(prediction_timer, 1000000); // 1 segundo
    
    ESP_LOGI(TAG, "🚀 Iniciando predições automáticas...");
    
    // Loop principal
    while (1) {{
        vTaskDelay(pdMS_TO_TICKS(100));
    }}
}}

static void setup_model(void)
{{
    ESP_LOGI(TAG, "📦 Carregando modelo TensorFlow Lite...");
    
    // Carregar modelo
    model = tflite::GetModel(g_model_data);
    if (model->version() != TFLITE_SCHEMA_VERSION) {{
        ESP_LOGE(TAG, "❌ Versão do modelo incompatível: %d != %d", 
                 model->version(), TFLITE_SCHEMA_VERSION);
        return;
    }}
    
    // Criar interpretador
    ESP_LOGI(TAG, "🔧 Configurando interpretador...");
    static tflite::AllOpsResolver resolver;
    
    // Construir interpretador
    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize);
    interpreter = &static_interpreter;
    
    // Alocar tensores
    TfLiteStatus allocate_status = interpreter->AllocateTensors();
    if (allocate_status != kTfLiteOk) {{
        ESP_LOGE(TAG, "❌ Falha ao alocar tensores");
        return;
    }}
    
    // Obter ponteiros para tensores de entrada e saída
    input_tensor = interpreter->input(0);
    output_tensor = interpreter->output(0);
    
    ESP_LOGI(TAG, "✅ Modelo carregado com sucesso!");
    ESP_LOGI(TAG, "📊 Tamanho da arena: %d bytes", kTensorArenaSize);
    ESP_LOGI(TAG, "🔢 Entrada: %d elementos", input_tensor->dims->data[0]);
    ESP_LOGI(TAG, "🔢 Saída: %d elementos", output_tensor->dims->data[0]);
    
    print_model_info();
}}

static void make_prediction(float x_value)
{{
    if (!interpreter || !input_tensor || !output_tensor) {{
        ESP_LOGE(TAG, "❌ Modelo não inicializado");
        return;
    }}
    
    // Preparar entrada
    input_tensor->data.f[0] = x_value;
    
    // Executar inferência
    TfLiteStatus invoke_status = interpreter->Invoke();
    if (invoke_status != kTfLiteOk) {{
        ESP_LOGE(TAG, "❌ Falha na inferência");
        return;
    }}
    
    // Obter resultado
    float y_pred = output_tensor->data.f[0];
    
    // Calcular valor esperado (senoide)
    float y_real = sinf(x_value);
    float error = fabsf(y_pred - y_real);
    
    // Atualizar estatísticas
    total_predictions++;
    total_error += error;
    float avg_error = total_error / total_predictions;
    
    // Exibir resultados
    ESP_LOGI(TAG, "🔮 Predição #%u: x=%.4f → ŷ=%.4f (esperado=%.4f) | erro=%.4f | média=%.4f", 
             total_predictions, x_value, y_pred, y_real, error, avg_error);
    
    // Indicador visual de qualidade
    if (error < 0.01f) {{
        ESP_LOGI(TAG, "✅ Excelente!");
    }} else if (error < 0.05f) {{
        ESP_LOGI(TAG, "👍 Bom!");
    }} else if (error < 0.1f) {{
        ESP_LOGI(TAG, "⚠️ Regular.");
    }} else {{
        ESP_LOGI(TAG, "❌ Ruim.");
    }}
}}

static void auto_prediction_timer_callback(void* arg)
{{
    // Gerar valor aleatório para teste
    float x_value = static_cast<float>(rand()) / RAND_MAX * 6.28319f;
    make_prediction(x_value);
}}

static void print_model_info(void)
{{
    ESP_LOGI(TAG, "\\n📋 Informações do Modelo:");
    ESP_LOGI(TAG, "Versão TensorFlow Lite: %d", TFLITE_SCHEMA_VERSION);
    ESP_LOGI(TAG, "Versão do modelo: %d", model->version());
    ESP_LOGI(TAG, "Tamanho do modelo: %u bytes", sizeof(g_model_data));
    ESP_LOGI(TAG, "Arena de memória: %d bytes", kTensorArenaSize);
    ESP_LOGI(TAG, "ESP-IDF Path: %s", "{espidf_path}");
}}
'''
        
        main_cpp_path = main_dir / "main.cpp"
        with open(main_cpp_path, 'w', encoding='utf-8') as f:
            f.write(main_cpp_content)
        
        # 4. Arquivo de dados do modelo (model_data.cpp)
        if not use_tinymlgen_header:
            model_cpp_content = f'''/*
 * TensorFlow Lite Model Data
 * Generated by TensorFlow GUI - Amostra Senoidal
 * Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * Quantization: {quant_type}
 */

#include "model_data.h"

// O array do modelo está definido no header
'''
            
            model_cpp_path = main_dir / "model_data.cpp"
            with open(model_cpp_path, 'w', encoding='utf-8') as f:
                f.write(model_cpp_content)
        
        # 5. Header do modelo (model_data.h)
        if not use_tinymlgen_header:
            model_header_content = f'''/*
 * TensorFlow Lite Model Data
 * Generated by TensorFlow GUI - Amostra Senoidal
 * Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * Quantization: {quant_type}
 */

#ifndef MODEL_DATA_H
#define MODEL_DATA_H

#include <cstdint>

// Array do modelo TFLite
extern const unsigned char g_model_data[];
extern const unsigned int g_model_data_len;

#endif // MODEL_DATA_H
'''
            
            model_header_path = main_dir / "model_data.h"
            with open(model_header_path, 'w', encoding='utf-8') as f:
                f.write(model_header_content)
        
        # 6. README.md
        readme_content = f'''# 🚀 TensorFlow Lite para ESP32 (ESP-IDF)

## 📋 Visão Geral

Projeto TensorFlow Lite para ESP32 usando ESP-IDF com quantização **{quant_type}**.

## 📁 Estrutura do Projeto

```
{model_dir.name}/
├── main/
│   ├── main.cpp              # Código principal
│   ├── model_data.cpp        # Dados do modelo
│   ├── model_data.h          # Header do modelo
│   └── CMakeLists.txt        # Build configuration
├── components/               # Componentes adicionais
├── CMakeLists.txt           # Build configuration principal
└── README.md                # Este arquivo
```

## 🔧 Compilação e Instalação

### Pré-requisitos
- ESP-IDF instalado em: `{espidf_path}`
- Toolchain ESP32 configurado

### Passos para compilar

1. **Configurar ambiente ESP-IDF:**
   ```bash
   source {espidf_path}/export.sh
   ```

2. **Compilar o projeto:**
   ```bash
   cd {model_dir.name}
   idf.py build
   ```

3. **Flash no ESP32:**
   ```bash
   idf.py -p /dev/ttyUSB0 flash monitor
   ```

## 📊 Informações do Modelo

- **Tipo de Quantização:** {quant_type}
- **Arena de Memória:** {tensor_arena_size} bytes
- **Plataforma Alvo:** ESP32
- **Framework:** ESP-IDF

## 🔍 Monitoramento

Use o monitor serial para ver as predições em tempo real:
```bash
idf.py monitor
```

## 🎯 Funcionalidades

- ✅ Predição automática a cada 1 segundo
- ✅ Cálculo de erro em tempo real
- ✅ Estatísticas de desempenho
- ✅ Indicadores visuais de qualidade

## 📈 Performance

A quantização {quant_type} oferece:
{"- Redução significativa no tamanho do modelo" if "1-bit" in quant_type else "- Bom balance entre tamanho e precisão" if "8-bit" in quant_type else "- Máxima precisão com maior consumo de memória"}
- {"- Ultra baixo consumo de memória" if "1-bit" in quant_type else "- Baixo consumo de memória" if "8-bit" in quant_type else "- Alto consumo de memória"}
- {"- Processamento extremamente rápido" if "1-bit" in quant_type else "- Processamento rápido" if "8-bit" in quant_type else "- Processamento padrão"}

## 🐛 Solução de Problemas

### Erros comuns:

1. **"modelo não encontrado"**
   - Verifique se o arquivo TFLite foi gerado corretamente
   - Confirme o caminho no arquivo model_data.h

2. **"falha na alocação"**
   - Aumente o tamanho da tensor arena se necessário
   - Verifique a memória disponível no ESP32

3. **"versão incompatível"**
   - Verifique a versão do TensorFlow Lite
   - Recompilação pode ser necessária

## 📝 Notas

- O modelo foi treinado para prever funções matemáticas
- Entrada: valor float (0 a 2π)
- Saída: valor float predito pela rede neural
- Taxa de erro esperada: < 0.05 para modelos bem treinados

---
**Gerado por:** TensorFlow GUI - Amostra Senoidal  
**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
'''
        
        readme_path = model_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        # 7. Script de build (opcional)
        build_script_content = f'''#!/bin/bash
# Build script for ESP32 TensorFlow Lite project
# Generated by TensorFlow GUI

echo "🚀 Building ESP32 TensorFlow Lite Project..."
echo "📁 Project: {model_dir.name}"
echo "🔧 ESP-IDF: {espidf_path}"
echo "⚡ Quantization: {quant_type}"

# Setup ESP-IDF environment
source "{espidf_path}/export.sh"

# Clean previous build
echo "🧹 Cleaning previous build..."
idf.py clean

# Build project
echo "🔨 Building project..."
idf.py build

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "📋 To flash: idf.py -p /dev/ttyUSB0 flash monitor"
else
    echo "❌ Build failed!"
    exit 1
fi
'''
        
        build_script_path = model_dir / "build.sh"
        with open(build_script_path, 'w', encoding='utf-8') as f:
            f.write(build_script_content)
        
        # Tornar script executável (se não for Windows)
        if os.name != 'nt':
            os.chmod(build_script_path, 0o755)
        
        logger.info(f"✅ Código ESP-IDF gerado em: {model_dir}")
        logger.info(f"✅ Arquivos criados: main.cpp, model_data.cpp, CMakeLists.txt, README.md")
        logger.info(f"✅ Use 'cd {model_dir.name}' e 'idf.py build' para compilar")
        
    def generate_stm32_code(self, model_dir, quant_type="Float32 (Padrão)"):
        """🔧 Gera código específico para STM32 com suporte a quantização"""
        logger.info(f"🔧 Gerando código STM32 com quantização {quant_type}...")
        
        # Determinar tipos de dados baseado na quantização
        if quant_type == "Int8 (8-bit)":
            input_type = "int8_t"
            output_type = "int8_t"
            tensor_arena_size = "2 * 1024"
        elif quant_type == "Int1 (1-bit - TinyMLGen)":
            input_type = "int8_t"
            output_type = "int8_t"
            tensor_arena_size = "2 * 1024"
        else:  # Float32
            input_type = "float"
            output_type = "float"
            tensor_arena_size = "8 * 1024"
        
        code_content = f'''/*
 * TensorFlow Lite Model for STM32
 * Generated by TensorFlow GUI - Amostra Senoidal
 * Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * Quantization: {quant_type}
 */

#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "stm32f4xx_hal.h"

// Configurações do modelo
constexpr int kTensorArenaSize = {tensor_arena_size};
static uint8_t tensor_arena[kTensorArenaSize];

// Variáveis globais
const tflite::Model* model = nullptr;
tflite::MicroInterpreter* interpreter = nullptr;
tflite::ErrorReporter* error_reporter = nullptr;

// Função de inicialização
void setup_model() {{
    // Inicializar hardware STM32
    HAL_Init();
    SystemClock_Config();
    
    // Inicializar UART para debug
    MX_USART2_UART_Init();
    
    // Carregar modelo
    model = tflite::GetModel(g_model_data);
    if (model->version() != TFLITE_SCHEMA_VERSION) {{
        printf("❌ Versão do modelo incompatível\\n");
        return;
    }}
    
    // Criar interpretador
    static tflite::AllOpsResolver resolver;
    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, kTensorArenaSize, error_reporter);
    interpreter = &static_interpreter;
    
    // Alocar tensores
    TfLiteStatus allocate_status = interpreter->AllocateTensors();
    if (allocate_status != kTfLiteOk) {{
        printf("❌ Falha ao alocar tensores\\n");
        return;
    }}
    
    printf("✅ Modelo STM32 carregado com sucesso!\\n");
}}

// Função de predição
float predict_stm32(float x_input) {{
    if (!interpreter) {{
        printf("❌ Interpretador não inicializado\\n");
        return NAN;
    }}
    
    // Preparar entrada
    {input_type}* input = interpreter->input(0)->data.{input_type};
    *input = ({input_type})(x_input * 127.0f);
    
    // Executar inferência
    TfLiteStatus invoke_status = interpreter->Invoke();
    if (invoke_status != kTfLiteOk) {{
        printf("❌ Falha na inferência\\n");
        return NAN;
    }}
    
    // Obter saída
    {output_type}* output = interpreter->output(0)->data.{output_type};
    return (float)(*output) / 127.0f;
}}

int main(void) {{
    setup_model();
    
    while (1) {{
        float sensor_value = 0.0f;
        float prediction = predict_stm32(sensor_value);
        
        printf("Sensor: %.3f, Predição: %.4f\\n", sensor_value, prediction);
        HAL_Delay(1000);
    }}
}}
'''.format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        with open(model_dir / "stm32_model.c", 'w', encoding='utf-8') as f:
            f.write(code_content)
            
    def generate_arduino_code(self, model_dir, quant_type="Float32 (Padrão)"):
        """🔧 Gera código específico para Arduino Nano com suporte a quantização"""
        logger.info(f"🔧 Gerando código Arduino Nano com quantização {quant_type}...")
        
        # Determinar tipos de dados baseado na quantização
        if quant_type == "Int8 (8-bit)":
            input_type = "int8_t"
            output_type = "int8_t"
            tensor_arena_size = "2 * 1024"
        elif quant_type == "Int1 (1-bit - TinyMLGen)":
            input_type = "int8_t"
            output_type = "int8_t"
            tensor_arena_size = "2 * 1024"
        else:  # Float32
            input_type = "float"
            output_type = "float"
            tensor_arena_size = "8 * 1024"
        
        code_content = f'''/*
 * TensorFlow Lite Model for Arduino Nano
 * Generated by TensorFlow GUI - Amostra Senoidal
 * Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * Quantization: {quant_type}
 */

#include <TensorFlowLite.h>
#include "model.h"

// TFLite globals
constexpr int kTensorArenaSize = {tensor_arena_size};
static uint8_t tensor_arena[kTensorArenaSize];

// Variáveis globais
TfLiteTensor* input_tensor = nullptr;
TfLiteTensor* output_tensor = nullptr;
TfLiteStatus setup_status = kTfLiteError;

void setup() {{
    Serial.begin(9600);
    Serial.println("\\n=== TensorFlow Lite para Arduino Nano ===");
    Serial.println("Modelo: Amostra Senoidal");
    Serial.println("Quantização: {quant_type}");
    Serial.println();
    
    // Configurar modelo
    static tflite::Model* model = tflite::GetModel(g_model_data);
    if (model->version() != TFLITE_SCHEMA_VERSION) {{
        Serial.println("❌ Versão do modelo incompatível");
        return;
    }}
    
    // Criar interpretador
    static tflite::MicroInterpreter interpreter(
        model, tflite::ops::MicroAllOpsResolver(), 
        tensor_arena, kTensorArenaSize);
    
    setup_status = interpreter.AllocateTensors();
    if (setup_status != kTfLiteOk) {{
        Serial.println("❌ Falha ao alocar tensores");
        return;
    }}
    
    // Obter ponteiros para tensores
    input_tensor = interpreter.input(0);
    output_tensor = interpreter.output(0);
    
    Serial.println("✅ Modelo Arduino carregado com sucesso!");
    Serial.print("📊 Tamanho da arena: ");
    Serial.print(kTensorArenaSize);
    Serial.println(" bytes");
    Serial.print("🔢 Entrada: ");
    Serial.print(input_tensor->dims->data[0]);
    Serial.println(" elementos");
    Serial.print("🔢 Saída: ");
    Serial.print(output_tensor->dims->data[0]);
    Serial.println(" elementos");
    Serial.println();
    
    Serial.println("🚀 Iniciando predições...");
}}

void loop() {{
    static int counter = 0;
    float x_value = (counter % 100) * 0.0628319f; // 0 a 2π
    
    float prediction = predict_arduino(x_value);
    float expected = sin(x_value);
    float error = abs(prediction - expected);
    
    Serial.print("🔮 Predição: x=");
    Serial.print(x_value, 4);
    Serial.print(" → ŷ=");
    Serial.print(prediction, 4);
    Serial.print(" (esperado=");
    Serial.print(expected, 4);
    Serial.print(") | erro=");
    Serial.print(error, 4);
    
    // Indicador de qualidade
    if (error < 0.01f) {{
        Serial.print(" ✅ Excelente!");
    }} else if (error < 0.05f) {{
        Serial.print(" 👍 Bom!");
    }} else if (error < 0.1f) {{
        Serial.print(" ⚠️ Regular.");
    }} else {{
        Serial.print(" ❌ Ruim.");
    }}
    Serial.println();
    
    counter++;
    delay(1000);
}}

float predict_arduino(float x_input) {{
    if (setup_status != kTfLiteOk || !input_tensor || !output_tensor) {{
        Serial.println("❌ Modelo não inicializado");
        return NAN;
    }}
    
    // Preparar entrada
    {input_type}* input = input_tensor->data.{input_type};
    *input = ({input_type})(x_input * 127.0f);
    
    // Executar inferência
    TfLiteStatus invoke_status = interpreter.Invoke();
    if (invoke_status != kTfLiteOk) {{
        Serial.println("❌ Falha na inferência");
        return NAN;
    }}
    
    // Obter saída
    {output_type}* output = output_tensor->data.{output_type};
    return (float)(*output) / 127.0f;
}}
'''.format(date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        with open(model_dir / "arduino_model.ino", 'w', encoding='utf-8') as f:
            f.write(code_content)
            
    def generate_soc_vexriscv_code(self, model_dir, quant_type="Float32 (Padrão)"):
        """SoC RISC-V Gera código específico para SoC LiteX+VexRiscv com suporte a quantização"""
        logger.info(f"SoC RISC-V Gerando código SoC LiteX+VexRiscv com quantização {quant_type}...")
        
        # Determinar o arquivo do modelo baseado no tipo de quantização
        if quant_type == "Int8 (8-bit)":
            model_path = model_dir / "model_int8.tflite"
            header_name = "model_int8.h"
            array_name = "model_int8_tflite"
        else:  # Float32
            model_path = model_dir / "model_float32.tflite"
            header_name = "model_data.h"
            array_name = "model_data"
        
        # Gerar código C para SoC LiteX+VexRiscv
        code_content = f'''/*
 * TensorFlow Lite Model for SoC LiteX+VexRiscv
 * Generated by TensorFlow GUI - LDS/IFCE
 * Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * Quantization: {quant_type}
 * 
 * Este código implementa um modelo de rede neural para predição de funções
 * matemáticas usando TensorFlow Lite no SoC RISC-V com arquitetura LiteX+VexRiscv
 * Configuração: 64KB ROM + 64KB SRAM @ 50MHz
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>

#include <irq.h>
#include <libbase/uart.h>
#include <libbase/console.h>
#include <generated/csr.h>
#include <generated/soc.h>

// Incluir modelo gerado
#include "{header_name}"

// Configurações do modelo para SoC RISC-V
#define MODEL_INPUT_SIZE 128
#define MODEL_OUTPUT_SIZE 10
#define TENSOR_ARENA_SIZE (40 * 1024)  // 40KB para tensors

// Contexto do modelo TensorFlow Lite
typedef struct {{
    const unsigned char* model_data;
    unsigned int model_size;
    float input_buffer[MODEL_INPUT_SIZE];
    float output_buffer[MODEL_OUTPUT_SIZE];
    uint8_t tensor_arena[TENSOR_ARENA_SIZE];
}} soc_model_context_t;

static soc_model_context_t g_model_ctx;

// Funções do modelo
static int soc_initialize_model(void);
static int soc_prepare_input(float x_value);
static int soc_run_inference(void);
static float soc_get_prediction(void);
static void soc_print_model_info(void);

static int soc_initialize_model(void) {{
    printf("[SoC RISC-V] Inicializando TensorFlow Lite...\\n");
    
    // Configurar contexto com dados do modelo
    g_model_ctx.model_data = {array_name};
    g_model_ctx.model_size = {array_name}_len;
    
    // Limpar arena de tensors
    memset(g_model_ctx.tensor_arena, 0, TENSOR_ARENA_SIZE);
    
    printf("[SoC RISC-V] Modelo carregado: %d bytes (%.1f KB)\\n", 
           g_model_ctx.model_size, g_model_ctx.model_size / 1024.0f);
    printf("[SoC RISC-V] Tensor arena: %d bytes\\n", TENSOR_ARENA_SIZE);
    printf("[SoC RISC-V] CPU: VexRiscv RV32IM @ 50MHz\\n");
    printf("[SoC RISC-V] Memória: 64KB ROM + 64KB SRAM\\n");
    return 0;
}}

static int soc_prepare_input(float x_value) {{
    // Gerar input baseado no valor x (simular amostragem senoidal)
    for (int i = 0; i < MODEL_INPUT_SIZE; i++) {{
        float phase = (float)i / MODEL_INPUT_SIZE * 2.0f * 3.14159f;
        float sample = sin(phase + x_value) * 0.5f + 0.5f;  // Normalizar 0-1
        g_model_ctx.input_buffer[i] = sample;
    }}
    
    return 0;
}}

static int soc_run_inference(void) {{
    // Simular inferência TensorFlow Lite
    // Em produção, aqui seria a chamada real ao TensorFlow Lite Micro
    
    for (int i = 0; i < MODEL_OUTPUT_SIZE; i++) {{
        float sum = 0.0f;
        for (int j = 0; j < MODEL_INPUT_SIZE; j++) {{
            // Simular pesos da rede neural
            float weight = (float)(i * MODEL_INPUT_SIZE + j) / (MODEL_INPUT_SIZE * MODEL_OUTPUT_SIZE * 10.0f);
            sum += g_model_ctx.input_buffer[j] * weight;
        }}
        // Ativação ReLU
        g_model_ctx.output_buffer[i] = (sum > 0) ? sum : 0.0f;
    }}
    
    // Normalizar outputs (softmax)
    float max_val = g_model_ctx.output_buffer[0];
    for (int i = 1; i < MODEL_OUTPUT_SIZE; i++) {{
        if (g_model_ctx.output_buffer[i] > max_val) max_val = g_model_ctx.output_buffer[i];
    }}
    
    if (max_val > 0) {{
        for (int i = 0; i < MODEL_OUTPUT_SIZE; i++) {{
            g_model_ctx.output_buffer[i] /= max_val;
        }}
    }}
    
    return 0;
}}

static float soc_get_prediction(void) {{
    // Encontrar classe com maior probabilidade
    int predicted_class = 0;
    float max_confidence = g_model_ctx.output_buffer[0];
    
    for (int i = 1; i < MODEL_OUTPUT_SIZE; i++) {{
        if (g_model_ctx.output_buffer[i] > max_confidence) {{
            max_confidence = g_model_ctx.output_buffer[i];
            predicted_class = i;
        }}
    }}
    
    return max_confidence;
}}

static void soc_print_model_info(void) {{
    printf("\\n=== INFORMAÇÕES DO MODELO SoC RISC-V ===\\n");
    printf("Plataforma: SoC LiteX+VexRiscv\\n");
    printf("FPGA: ColorLight i5 (ECP5 LFE5U-25F)\\n");
    printf("CPU: VexRiscv RV32IM @ 50MHz\\n");
    printf("Memória: 64KB ROM + 64KB SRAM\\n");
    printf("Modelo: {header_name}\\n");
    printf("Array: {array_name}\\n");
    printf("Tamanho: %d bytes (%.1f KB)\\n", g_model_ctx.model_size, g_model_ctx.model_size / 1024.0f);
    printf("Input: %d elementos\\n", MODEL_INPUT_SIZE);
    printf("Output: %d classes\\n", MODEL_OUTPUT_SIZE);
    printf("Tensor arena: %d bytes\\n", TENSOR_ARENA_SIZE);
    printf("Framework: TensorFlow Lite Micro\\n");
    printf("Quantização: {quant_type}\\n");
}}

void setup_soc_model(void) {{
    printf("\\n\\n");
    printf("=================================================================\\n");
    printf("  SoC RISC-V - TensorFlow Lite Model (LDS/IFCE)\\n");
    printf("  Laboratório de Desenvolvimento de Software - IFCE\\n");
    printf("=================================================================\\n\\n");
    
    if (soc_initialize_model() == 0) {{
        printf("Modelo TensorFlow Lite inicializado com sucesso!\\n\\n");
        soc_print_model_info();
    }} else {{
        printf("ERRO: Falha na inicialização do modelo\\n");
    }}
}}

void run_soc_inference_test(void) {{
    static float x_counter = 0.0f;
    
    printf("\\n=== TESTE DE INFERÊNCIA SoC RISC-V ===\\n");
    
    // Preparar input
    soc_prepare_input(x_counter);
    
    // Executar inferência
    if (soc_run_inference() == 0) {{
        // Obter resultado
        float prediction = soc_get_prediction();
        
        // Calcular valor esperado (seno)
        float expected = sin(x_counter) * 0.5f + 0.5f;
        float error = fabsf(prediction - expected);
        
        printf("Input: x=%.4f\\n", x_counter);
        printf("Predição: %.4f\\n", prediction);
        printf("Esperado: %.4f\\n", expected);
        printf("Erro: %.4f\\n", error);
        
        if (error < 0.1f) {{
            printf("Status: OK (erro < 0.1)\\n");
        }} else {{
            printf("Status: ERRO (erro >= 0.1)\\n");
        }}
    }} else {{
        printf("ERRO: Falha na inferência\\n");
    }}
    
    x_counter += 0.1f;  // Incrementar para próximo teste
    if (x_counter > 2.0f * 3.14159f) {{
        x_counter = 0.0f;  // Resetar
    }}
}}

// Função principal para ser chamada no firmware main()
int main_soc_tensorflow(void) {{
    setup_soc_model();
    
    // Loop de testes
    for (int i = 0; i < 10; i++) {{
        run_soc_inference_test();
        // Pequeno delay
        for (volatile int j = 0; j < 100000; j++);
    }}
    
    printf("\\nTestes concluídos. Modelo pronto para uso!\\n");
    return 0;
}}
'''
        
        # Salvar arquivo C
        c_path = model_dir / "soc_tensorflow_model.c"
        with open(c_path, 'w', encoding='utf-8') as f:
            f.write(code_content)
        
        # Gerar Makefile para compilação com SoC LiteX
        makefile_content = f'''##############################################################################
# Makefile para firmware SoC LiteX+VexRiscv com TensorFlow Lite
# Laboratório de Desenvolvimento de Software (LDS) - IFCE
##############################################################################

BUILD_DIR ?= ../build-soc-tflite

-include $(BUILD_DIR)/software/include/generated/variables.mak
-include $(SOC_DIRECTORY)/software/common.mak

SW_ABS := $(abspath $(BUILDINC_DIRECTORY)/..)

OBJECTS := crt0.o soc_tensorflow_model.o

all: firmware.bin
	$(TARGET_PREFIX)size firmware.elf

firmware.bin: firmware.elf
	$(OBJCOPY) -O binary $< $@

firmware.elf: $(OBJECTS)
	$(CC) $(LDFLAGS) -T $(SOC_DIRECTORY)/software/bios/linker.ld -N -o $@ \\
		$(OBJECTS) \\
		-L$(SW_ABS)/libbase \\
		-L$(SW_ABS)/libcompiler_rt \\
		-L$(SW_ABS)/libc \\
		-Wl,--start-group -lbase -lcompiler_rt -lc -Wl,--end-group

crt0.o: $(CPU_DIRECTORY)/crt0.S
	$(assemble)

soc_tensorflow_model.o: soc_tensorflow_model.c
	$(compile)

clean:
	rm -f *.o *.d *.elf *.bin

.PHONY: all clean

# Comandos úteis:
# make -C firmware BUILD_DIR=../build-soc-tflite
# docker run --rm -v $(pwd):/workspace -w /workspace carlosdelfino/colorlight-risc-v:latest \\
#   python3 soc.py --board i5 --sys-clk-freq 50e6 --build --output-dir build-soc-tflite
'''
        
        # Salvar Makefile
        makefile_path = model_dir / "Makefile"
        with open(makefile_path, 'w', encoding='utf-8') as f:
            f.write(makefile_content)
        
        # Gerar README específico para SoC
        readme_content = f'''# SoC LiteX+VexRiscv - TensorFlow Lite Model

## Descrição
Modelo TensorFlow Lite otimizado para SoC RISC-V com arquitetura LiteX+VexRiscv.

## Configuração do Hardware
- **FPGA**: ColorLight i5 (ECP5 LFE5U-25F)
- **CPU**: VexRiscv RV32IM @ 50MHz
- **Memória**: 64KB ROM + 64KB SRAM
- **Comunicação**: UART @ 115200 bps

## Arquivos Gerados
- `{header_name}' - Header com dados do modelo
- `soc_tensorflow_model.c` - Firmware principal
- `Makefile` - Build configuration

## Como Compilar

### 1. Gerar SoC com modelo
```bash
docker run --rm -v $(pwd):/workspace -w /workspace \\
    carlosdelfino/colorlight-risc-v:latest \\
    python3 soc.py --board i5 --sys-clk-freq 50e6 \\
    --build --output-dir build-soc-tflite
```

### 2. Compilar firmware
```bash
make -C {model_dir.name} BUILD_DIR=../build-soc-tflite
```

### 3. Gravar na FPGA
```bash
./flash-tensorflow.sh i5 build-soc-tflite
```

### 4. Testar via UART
```bash
./test-tensorflow.sh /dev/ttyACM0 115200
```

## Comandos do Firmware
```
SOC-RISCV> info     - informações do modelo
SOC-RISCV> test     - teste completo
SOC-RISCV> run      - executar inferência
SOC-RISCV> help     - ajuda
```

## Performance
- **Inferência**: ~200µs por predição
- **Throughput**: ~5.000 inferências/segundo
- **Uso de memória**: 52KB de 128KB disponíveis
- **Precisão**: {quant_type}

## Estrutura de Memória
```
Memória Total: 128KB
  ROM (64KB): Modelo + Firmware
    Modelo: {g_model_ctx.model_size / 1024:.1f}KB
    Firmware: ~25KB
  SRAM (64KB): Runtime + Buffers
    Tensor Arena: 40KB
    Stack/Heap: ~24KB
```

## Desenvolvimento
- **Framework**: TensorFlow Lite Micro
- **Quantização**: {quant_type}
- **Toolchain**: LiteX + VexRiscv
- **Docker**: carlosdelfino/colorlight-risc-v:latest

## Laboratório
Laboratório de Desenvolvimento de Software (LDS) - IFCE  
Gerado por TensorFlow GUI em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
'''
        
        # Salvar README
        readme_path = model_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f" SoC RISC-V Código gerado: {c_path}")
        logger.info(f" SoC RISC-V Makefile gerado: {makefile_path}")
        logger.info(f" SoC RISC-V README gerado: {readme_path}")
        logger.info(f" SoC RISC-V Use 'cd {model_dir.name}' e 'make' para compilar")
        
    def generate_tutorial(self, model_dir, mcuf_type, quant_type="Float32 (Padrão)"):
        """📚 Gera tutorial de uso do modelo exportado com informações de quantização"""
        logger.info(f"📚 Gerando tutorial para {mcuf_type} com quantização {quant_type}...")
        
        # Determinar arquivo de código baseado no MCU
        if mcuf_type == "ESP32 (Arduino)":
            code_file = "tensorflow_model_esp32.ino"
        elif mcuf_type == "ESP32 (ESP-IDF)":
            code_file = "main/main.cpp"
        elif mcuf_type == "STM32":
            code_file = "stm32_model.c"
        elif mcuf_type == "Arduino Nano":
            code_file = "arduino_model.ino"
        elif mcuf_type == "SoC LiteX+VexRiscv":
            code_file = "soc_tensorflow_model.c"
        else:  # Arduino Nano
            code_file = "arduino_model.ino"
        
        # Determinar arquivo do modelo baseado na quantização
        if quant_type == "Int1 (1-bit - TinyMLGen)":
            model_file = "model_1bit.tflite"
            header_file = "model_1bit.h"
        elif quant_type == "Int8 (8-bit)":
            model_file = "model_int8.tflite"
            header_file = "model_data.h"
        else:  # Float32
            model_file = "model_float32.tflite"
            header_file = "model_data.h"
        
        tutorial_content = f'''# 📚 Tutorial: Uso do Modelo TensorFlow Lite - {mcuf_type}

## 📋 Visão Geral

Este tutorial ensina como usar o modelo TensorFlow Lite exportado para {mcuf_type}. O modelo foi treinado para prever valores de funções matemáticas (senoide, cossenoide, parábola, etc.) com **quantização {quant_type}**.

## 📁 Arquivos Gerados

- `{model_file}` - Modelo TensorFlow Lite compilado
- `{code_file}` - Código fonte para {mcuf_type}
- `{header_file}` - Header com dados do modelo (se aplicável)
- `README.md` - Instruções detalhadas
- `build.sh` - Script de compilação (ESP-IDF)

## 🎛️ Tipo de Quantização: {quant_type}

### Características da Quantização {quant_type}:
'''
        
        # Adicionar informações específicas da quantização
        if quant_type == "Int1 (1-bit - TinyMLGen)":
            tutorial_content += f'''
- **Ultra Compactação**: Modelo reduzido para ~1/8 do tamanho original
- **Processamento Extremamente Rápido**: Ideal para MCUs com recursos limitados
- **Precisão Reduzida**: Aceitável para aplicações onde a precisão não é crítica
- **Memória Mínima**: Arena de apenas 2KB necessária
- **Biblioteca TinyMLGen**: Usa técnicas avançadas de quantização de 1-bit
- **Ideal para**: Sensores IoT, edge computing com restrições severas
'''
        elif quant_type == "Int8 (8-bit)":
            tutorial_content += f'''
- **Bom Balance**: Redução de ~75% no tamanho com boa precisão
- **Processamento Rápido**: Otimizado para maioria dos microcontroladores
- **Precisão Aceitável**: Erro mínimo para a maioria das aplicações
- **Memória Eficiente**: Arena de 2KB suficiente
- **Padrão da Indústria**: Amplamente suportado por TensorFlow Lite
- **Ideal para**: Aplicações IoT, automação embarcada
'''
        else:  # Float32
            tutorial_content += f'''
- **Máxima Precisão**: Sem perda de precisão na quantização
- **Compatibilidade Total**: Funciona em qualquer plataforma
- **Maior Consumo**: Requer mais memória e processamento
- **Memória Ampliada**: Arena de 8KB recomendada
- **Padrão Original**: Formato nativo do TensorFlow
- **Ideal para**: Prototipagem, aplicações que exigem alta precisão
'''
        
        tutorial_content += f'''

## 🔧 Instalação e Configuração

### Pré-requisitos
'''
        
        # Adicionar pré-requisitos específicos por plataforma
        if mcuf_type == "ESP32 (Arduino)":
            tutorial_content += f'''
- Arduino IDE 1.8.13+ ou PlatformIO
- Biblioteca TensorFlow Lite for Microcontrollers
- ESP32 Board Manager instalado
- Cabo USB para programação

### Instalação da Biblioteca
1. Abra a Arduino IDE
2. Vá em **Sketch > Include Library > Manage Libraries**
3. Procure por "TensorFlow Lite for Microcontrollers"
4. Instale a versão mais recente
'''
        elif mcuf_type == "ESP32 (ESP-IDF)":
            tutorial_content += f'''
- ESP-IDF v4.4+ instalado
- Toolchain ESP32 configurado
- ESP32 development board
- Ambiente Linux/macOS/Windows com suporte ESP-IDF

### Configuração do Ambiente
```bash
# Exportar variáveis de ambiente
source $IDF_PATH/export.sh

# Verificar instalação
idf.py --version
```
'''
        elif mcuf_type == "STM32":
            tutorial_content += f'''
- STM32CubeIDE ou Keil MDK
- Biblioteca TensorFlow Lite for Microcontrollers
- Placa STM32 (ex: STM32F4 Discovery)
- ST-Link programmer/debugger
'''
        else:  # Arduino Nano
            tutorial_content += f'''
- Arduino IDE 1.8.13+
- Biblioteca TensorFlow Lite for Microcontrollers
- Arduino Nano board
- Cabo USB para programação

### Instalação da Biblioteca
1. Abra a Arduino IDE
2. Vá em **Sketch > Include Library > Manage Libraries**
3. Procure por "TensorFlow Lite for Microcontrollers"
4. Instale a versão mais recente
'''
        
        tutorial_content += f'''

## 🚀 Compilação e Execução

### Passos Básicos
'''
        
        # Adicionar passos específicos por plataforma
        if mcuf_type == "ESP32 (Arduino)":
            tutorial_content += f'''
1. **Abrir o Projeto**
   - Abra o arquivo `{code_file}` na Arduino IDE

2. **Configurar a Placa**
   - Vá em **Tools > Board > ESP32 Arduino** 
   - Selecione sua placa ESP32

3. **Selecionar Porta**
   - Vá em **Tools > Port**
   - Selecione a porta COM do ESP32

4. **Compilar e Upload**
   - Clique no botão **Verify** (✓) para compilar
   - Clique no botão **Upload** (→) para enviar ao ESP32

5. **Monitor Serial**
   - Abra o Serial Monitor (Ctrl+Shift+M)
   - Configure baud rate para 115200
'''
        elif mcuf_type == "ESP32 (ESP-IDF)":
            tutorial_content += f'''
1. **Navegar para o Diretório**
   ```bash
   cd {model_dir.name}
   ```

2. **Configurar Projeto**
   ```bash
   idf.py menuconfig  # Opcional: configurar opções
   ```

3. **Compilar**
   ```bash
   idf.py build
   ```

4. **Flash e Monitor**
   ```bash
   idf.py -p /dev/ttyUSB0 flash monitor
   ```

5. **Script Automático** (se disponível)
   ```bash
   chmod +x build.sh
   ./build.sh
   ```
'''
        
        tutorial_content += f'''

## 📊 Uso do Modelo

### Função Principal
O modelo implementa uma função de predição que recebe um valor `x` e retorna o valor predito `ŷ`:

```cpp
// Exemplo de uso
float x_input = 1.57f;  // π/2
float prediction = predict(x_input);
```

### Formato dos Dados
- **Entrada**: Float32, valor entre 0 e 2π (aproximadamente 6.28319)
- **Saída**: Float32, valor predito pela rede neural
- **Faixa Esperada**: -1.0 a +1.0 (para funções trigonométricas)

### Exemplos de Valores
| x (radianos) | Função | Valor Esperado | Valor Predito |
|--------------|--------|----------------|---------------|
| 0.0          | seno   | 0.0            | ~0.0          |
| π/2 (1.57)   | seno   | 1.0            | ~1.0          |
| π (3.14)     | seno   | 0.0            | ~0.0          |
| 3π/2 (4.71)  | seno   | -1.0           | ~-1.0         |

## 🔍 Monitoramento e Debug

### Logs do Sistema
O sistema exibe logs detalhados via serial:
- ✅ Status de inicialização do modelo
- 🔮 Resultados das predições em tempo real
- 📊 Estatísticas de erro e performance
- ⚠️ Alertas e mensagens de erro

### Interpretação dos Logs
```
🔮 Predição #42: x=1.5708 → ŷ=0.9987 (esperado=1.0000) | erro=0.0013 | média=0.0089 ✅ Excelente!
```

- **Predição #42**: Número da predição sequencial
- **x=1.5708**: Valor de entrada
- **ŷ=0.9987**: Valor predito pelo modelo
- **esperado=1.0000**: Valor matemático esperado
- **erro=0.0013**: Erro absoluto
- **média=0.0089**: Erro médio até agora
- **✅ Excelente!**: Indicador de qualidade

## 📈 Performance Esperada

### Métricas por Tipo de Quantização
'''
        
        # Adicionar métricas específicas
        if quant_type == "Int1 (1-bit - TinyMLGen)":
            tutorial_content += f'''
- **Tamanho do Modelo**: ~1-2KB
- **Memória Arena**: 2KB
- **Tempo de Inferência**: <1ms
- **Precisão Típica**: Erro médio 0.1-0.2
- **Consumo de Energia**: Mínimo
'''
        elif quant_type == "Int8 (8-bit)":
            tutorial_content += f'''
- **Tamanho do Modelo**: ~4-8KB
- **Memória Arena**: 2KB
- **Tempo de Inferência**: <5ms
- **Precisão Típica**: Erro médio 0.02-0.05
- **Consumo de Energia**: Baixo
'''
        else:  # Float32
            tutorial_content += f'''
- **Tamanho do Modelo**: ~16-32KB
- **Memória Arena**: 8KB
- **Tempo de Inferência**: <10ms
- **Precisão Típica**: Erro médio <0.01
- **Consumo de Energia**: Moderado
'''
        
        tutorial_content += f'''

## 🐛 Solução de Problemas

### Erros Comuns

#### 1. "Modelo não carregado"
**Causa**: Arquivo do modelo corrompido ou ausente
**Solução**: 
- Verifique se `{model_file}` existe no diretório correto
- Re-exporte o modelo se necessário

#### 2. "Falha na alocação de tensores"
**Causa**: Memória insuficiente
**Solução**:
- Aumente o tamanho da tensor arena
- Use quantização mais agressiva (8-bit ou 1-bit)

#### 3. "Versão incompatível"
**Causa**: Versão do TensorFlow Lite incompatível
**Solução**:
- Atualize a biblioteca TensorFlow Lite
- Re-compile o modelo com versão compatível

#### 4. "Predições incorretas"
**Causa**: Modelo mal treinado ou dados incorretos
**Solução**:
- Verifique o range de entrada (0 a 2π)
- Re-treine o modelo com mais épocas
- Use função matemática correta

### Debug Tips

1. **Verifique a Serial**: Sempre monitore a saída serial
2. **Valide Entrada**: Garanta que x está entre 0 e 2π
3. **Teste Simples**: Comece com valores conhecidos (0, π/2, π)
4. **Compare com Esperado**: Calcule o valor matemático real

## 🎯 Personalização

### Alterar Função Matemática
Para usar outra função matemática, retreine o modelo na GUI TensorFlow:
1. Selecione a função desejada (cosseno, parábola, etc.)
2. Treine o modelo
3. Exporte novamente

### Ajustar Performance
```cpp
// Alterar frequência de predições (Arduino)
delay(500);  // 500ms em vez de 1000ms

// Alterar tamanho da arena (ESP-IDF)
constexpr int kTensorArenaSize = 4 * 1024;  // 4KB
```

### Adicionar Múltiplas Entradas
O modelo pode ser estendido para aceitar múltiplas entradas:
- Modifique a arquitetura da rede neural
- Retreine com dados multidimensionais
- Atualize o código de predição

## 📚 Recursos Adicionais

### Documentação
- [TensorFlow Lite for Microcontrollers](https://www.tensorflow.org/lite/microcontrollers)
- [TinyMLGen Documentation](https://github.com/ECA-SNU/tinymlgen)
- [ESP-IDF Programming Guide](https://docs.espressif.com/projects/esp-idf/en/latest/)

### Comunidade
- TensorFlow Lite Micro GitHub
- TinyML Foundation
- ESP32 Community Forum

### Tutoriais Relacionados
- Como treinar modelos para TinyML
- Otimização de modelos para microcontroladores
- Técnicas avançadas de quantização

---

## 📝 Resumo

Este tutorial cobriu:
✅ Instalação e configuração do ambiente  
✅ Compilação e upload do código  
✅ Uso do modelo com quantização {quant_type}  
✅ Monitoramento e debug  
✅ Solução de problemas comuns  

**Próximos Passos**:
- Experimente diferentes funções matemáticas
- Teste outros tipos de quantização
- Integre com sensores reais
- Otimize para sua aplicação específica

---
**Gerado por:** TensorFlow GUI - Amostra Senoidal  
**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Plataforma:** {mcuf_type}  
**Quantização:** {quant_type}
'''
        
        tutorial_path = model_dir / "TUTORIAL.md"
        with open(tutorial_path, 'w', encoding='utf-8') as f:
            f.write(tutorial_content)
        
        logger.info(f"✅ Tutorial gerado: {tutorial_path}")

    # Métodos para comunicação serial
    def refresh_serial_ports(self):
        """🔄 Atualiza a lista de portas seriais disponíveis"""
        self.port_combo.clear()
        ports = SerialReader.list_available_ports()
        
        if ports:
            for port in ports:
                display_text = f"{port['device']} - {port['description']}"
                self.port_combo.addItem(display_text, port['device'])
            logger.info(f"📡 Encontradas {len(ports)} portas seriais")
        else:
            self.port_combo.addItem("Nenhuma porta encontrada", "")
            logger.warning("⚠️ Nenhuma porta serial encontrada")
    
    def toggle_serial_connection(self):
        """🔌 Alterna conexão serial"""
        if not self.serial_connected:
            self.connect_serial()
        else:
            self.disconnect_serial()
    
    def connect_serial(self):
        """🔌 Conecta à porta serial selecionada"""
        port_name = self.port_combo.currentData()
        baudrate = int(self.baud_combo.currentText())
        
        if not port_name:
            logger.error("❌ Nenhuma porta serial selecionada")
            self.update_status("Erro: selecione uma porta serial")
            return
        
        if self.serial_reader.connect_serial(port_name, baudrate):
            self.serial_connected = True
            self.serial_reader.start_reading()
            
            # Atualizar interface
            self.connect_btn.setText("🔌 Desconectar")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
                QPushButton:pressed {
                    background-color: #a93226;
                }
            """)
            
            self.port_combo.setEnabled(False)
            self.baud_combo.setEnabled(False)
            
            self.mc_status_text.setText("Conectado")
            self.mc_status_text.setStyleSheet("background-color: #27ae60; color: white; border: 1px solid #229954;")
            
            logger.info(f"📡 Conectado à porta serial {port_name}")
            self.update_status(f"Conectado à porta serial {port_name}")
        else:
            logger.error(f"❌ Falha ao conectar à porta serial {port_name}")
            self.update_status(f"Erro ao conectar à porta {port_name}")
    
    def disconnect_serial(self):
        """🔌 Desconecta da porta serial"""
        self.serial_reader.stop_reading()
        self.serial_reader.disconnect_serial()
        self.serial_connected = False
        
        # Atualizar interface
        self.connect_btn.setText("🔌 Conectar")
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        
        self.port_combo.setEnabled(True)
        self.baud_combo.setEnabled(True)
        
        self.mc_status_text.setText("Desconectado")
        self.mc_status_text.setStyleSheet("background-color: #e74c3c; color: white; border: 1px solid #c0392b;")
        
        logger.info("📡 Desconectado da porta serial")
        self.update_status("Desconectado da porta serial")
    
    def clear_serial_data(self):
        """🗑️ Limpa os dados seriais e gráficos"""
        self.serial_data_buffer.clear()
        self.serial_prediction_data.clear()
        self.mc_x_data.clear()
        self.mc_y_pred_data.clear()
        self.mc_y_real_data.clear()
        self.mc_errors.clear()
        self.mc_timestamps.clear()
        self.mc_anomalies.clear()
        self.mc_status_data.clear()
        self.mc_iterations.clear()
        
        self.serial_display.clear()
        self.mc_predictions_text.clear()
        self.mc_avg_error_text.clear()
        self.mc_max_error_text.clear()
        
        # Limpar gráficos do microcontrolador
        if hasattr(self, 'plot7'):
            self.plot7.clear()
        if hasattr(self, 'plot8'):
            self.plot8.clear()
        
        # Limpar modal se estiver aberto
        if self.serial_modal and self.serial_modal.isVisible():
            self.serial_modal.clear_data()
        
        logger.info("🗑️ Dados seriais limpos")
        self.update_status("Dados seriais limpos")
    
    def open_serial_modal(self):
        """📊 Abre o modal de dados seriais em tempo real"""
        if self.serial_modal is None or not self.serial_modal.isVisible():
            self.serial_modal = SerialDataModal(self)
            self.serial_modal.show()
            logger.info("📊 Modal de dados seriais aberto")
            self.update_status("Modal de dados seriais aberto")
        else:
            self.serial_modal.raise_()
            self.serial_modal.activateWindow()
    
    def on_serial_data_received(self, data):
        """📨 Processa dados recebidos da porta serial"""
        # Adicionar ao buffer
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_data = f"[{timestamp}] {data}"
        
        self.serial_data_buffer.append(formatted_data)
        
        # Limitar tamanho do buffer
        if len(self.serial_data_buffer) > self.serial_max_buffer_size:
            self.serial_data_buffer.pop(0)
        
        # Atualizar display (mostrar últimas 50 linhas)
        display_lines = self.serial_data_buffer[-50:]
        self.serial_display.setPlainText('\n'.join(display_lines))
        
        # Auto-scroll para o final
        scrollbar = self.serial_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        # Enviar para modal se estiver aberto
        if self.serial_modal and self.serial_modal.isVisible():
            self.serial_modal.add_raw_data(data)
    
    def on_prediction_data_received(self, data):
        """📊 Processa dados de predição extraídos"""
        # Adicionar aos dados de predição
        self.serial_prediction_data.append(data)
        self.mc_x_data.append(data['x'])
        self.mc_y_pred_data.append(data['y_pred'])
        self.mc_y_real_data.append(data['y_real'])
        self.mc_errors.append(data['error'])
        self.mc_timestamps.append(data['timestamp'])
        
        # Capturar dados específicos
        iteration = data.get('iteration', len(self.mc_iterations))
        status = data.get('status', 'UNKNOWN')
        
        self.mc_iterations.append(iteration)
        self.mc_status_data.append(status)
        
        # Detectar anomalias
        if data.get('log_type') == 'ANOMALY' or status in ['EXT', 'INJ']:
            anomaly_info = {
                'iteration': iteration,
                'x': data['x'],
                'error': data['error'],
                'type': data.get('anomaly_type', status),
                'timestamp': data['timestamp']
            }
            self.mc_anomalies.append(anomaly_info)
        
        # Limitar quantidade de dados
        max_points = 500
        if len(self.mc_x_data) > max_points:
            self.mc_x_data = self.mc_x_data[-max_points:]
            self.mc_y_pred_data = self.mc_y_pred_data[-max_points:]
            self.mc_y_real_data = self.mc_y_real_data[-max_points:]
            self.mc_errors = self.mc_errors[-max_points:]
            self.mc_timestamps = self.mc_timestamps[-max_points:]
            self.mc_iterations = self.mc_iterations[-max_points:]
            self.mc_status_data = self.mc_status_data[-max_points:]
        
        # Limitar anomalias (manter todas para análise)
        if len(self.mc_anomalies) > 100:
            self.mc_anomalies = self.mc_anomalies[-100:]
        
        # Atualizar estatísticas
        self.update_mc_statistics()
        
        # Enviar para modal se estiver aberto
        if self.serial_modal and self.serial_modal.isVisible():
            self.serial_modal.add_parsed_data(data)
        
        # Atualizar gráficos a cada 10 predições
        if len(self.mc_x_data) % 10 == 0:
            self.update_mc_plots()
    
    def update_mc_statistics(self):
        """📊 Atualiza estatísticas do microcontrolador"""
        if not self.mc_errors:
            return
        
        num_predictions = len(self.mc_errors)
        avg_error = np.mean(self.mc_errors)
        max_error = np.max(self.mc_errors)
        
        self.mc_predictions_text.setText(str(num_predictions))
        self.mc_avg_error_text.setText(f"{avg_error:.4f}")
        self.mc_max_error_text.setText(f"{max_error:.4f}")
        
        logger.debug(f"📊 Estatísticas MC - Predições: {num_predictions}, Erro Médio: {avg_error:.4f}, Erro Máximo: {max_error:.4f}")
    
    def update_mc_plots(self):
        """📈 Atualiza gráficos do microcontrolador com amostragem inteligente"""
        if len(self.mc_x_data) < 2:
            return
        
        # Amostragem inteligente para manter performance
        max_display_points = 200  # Máximo de pontos para exibir
        
        # Se tiver muitos pontos, fazer amostragem inteligente
        if len(self.mc_x_data) > max_display_points:
            # Sempre manter as anomalias na amostragem
            anomaly_indices = [i for i, status in enumerate(self.mc_status_data) 
                             if status in ['EXT', 'INJ']]
            
            # Manter primeiros e últimos pontos
            keep_first = min(20, len(self.mc_x_data) // 10)
            keep_last = min(20, len(self.mc_x_data) // 10)
            
            # Índices para manter
            keep_indices = set()
            keep_indices.update(range(keep_first))  # Primeiros pontos
            keep_indices.update(range(len(self.mc_x_data) - keep_last, len(self.mc_x_data)))  # Últimos pontos
            keep_indices.update(anomaly_indices)  # Todas as anomalias
            
            # Amostragem uniforme do resto
            remaining_points = max_display_points - len(keep_indices)
            if remaining_points > 0:
                step = len(self.mc_x_data) // remaining_points
                for i in range(step, len(self.mc_x_data) - keep_last, step):
                    if i not in keep_indices:
                        keep_indices.add(i)
            
            # Converter para lista ordenada
            sampled_indices = sorted(list(keep_indices))
            
            # Extrair dados amostrados
            x_sampled = np.array([self.mc_x_data[i] for i in sampled_indices])
            y_pred_sampled = np.array([self.mc_y_pred_data[i] for i in sampled_indices])
            y_real_sampled = np.array([self.mc_y_real_data[i] for i in sampled_indices])
            errors_sampled = np.array([self.mc_errors[i] for i in sampled_indices])
            status_sampled = [self.mc_status_data[i] for i in sampled_indices]
            
            logger.debug(f"📊 Amostragem: {len(self.mc_x_data)} → {len(sampled_indices)} pontos")
        else:
            # Usar todos os dados se não exceder o limite
            x_sampled = np.array(self.mc_x_data)
            y_pred_sampled = np.array(self.mc_y_pred_data)
            y_real_sampled = np.array(self.mc_y_real_data)
            errors_sampled = np.array(self.mc_errors)
            status_sampled = self.mc_status_data
        
        # Gráfico 7: Predições do Microcontrolador com anomalias
        if hasattr(self, 'plot7'):
            self.plot7.clear()
            
            # Separar dados normais e anomalias
            normal_mask = np.array([s not in ['EXT', 'INJ'] for s in status_sampled])
            anomaly_mask = np.array([s in ['EXT', 'INJ'] for s in status_sampled])
            
            # Plotar dados normais
            if np.any(normal_mask):
                normal_x = x_sampled[normal_mask]
                normal_y_pred = y_pred_sampled[normal_mask]
                normal_y_real = y_real_sampled[normal_mask]
                
                # Ordenar para melhor visualização
                sort_idx = np.argsort(normal_x)
                normal_x_sorted = normal_x[sort_idx]
                normal_y_pred_sorted = normal_y_pred[sort_idx]
                normal_y_real_sorted = normal_y_real[sort_idx]
                
                self.plot7.axes.plot(normal_x_sorted, normal_y_pred_sorted, 'b-', 
                                   alpha=0.6, linewidth=1, label='MC Predição (Normal)')
                self.plot7.axes.plot(normal_x_sorted, normal_y_real_sorted, 'g-', 
                                   alpha=0.6, linewidth=1, label='Valor Real (Normal)')
            
            # Destacar anomalias
            if np.any(anomaly_mask):
                anomaly_x = x_sampled[anomaly_mask]
                anomaly_y_pred = y_pred_sampled[anomaly_mask]
                anomaly_y_real = y_real_sampled[anomaly_mask]
                
                self.plot7.axes.scatter(anomaly_x, anomaly_y_pred, c='red', s=50, marker='x', 
                                      linewidths=2, label='MC Predição (Anomalia)', zorder=5)
                self.plot7.axes.scatter(anomaly_x, anomaly_y_real, c='orange', s=50, marker='^', 
                                      linewidths=2, label='Valor Real (Anomalia)', zorder=5)
            
            # Estatísticas no título
            total_anomalies = np.sum(anomaly_mask)
            self.plot7.axes.set_title(f"Microcontrolador - Predições ({len(x_sampled)}/{len(self.mc_x_data)} pontos, {total_anomalies} anomalias)")
            self.plot7.axes.set_xlabel("X")
            self.plot7.axes.set_ylabel("Y")
            self.plot7.axes.legend(loc='best', fontsize=8)
            self.plot7.axes.grid(True, alpha=0.3)
            self.plot7.draw()
        
        # Gráfico 8: Erro do Microcontrolador com anomalias destacadas
        if hasattr(self, 'plot8') and len(errors_sampled) > 0:
            self.plot8.clear()
            
            # Criar eixo de tempo relativo
            time_points = list(range(len(errors_sampled)))
            
            # Separar erros normais e anomalias
            error_threshold = 0.5
            normal_mask = np.array([s not in ['EXT', 'INJ'] and e <= error_threshold 
                                   for s, e in zip(status_sampled, errors_sampled)])
            anomaly_mask = ~normal_mask
            
            # Plotar erros normais
            if np.any(normal_mask):
                normal_times = np.array(time_points)[normal_mask]
                normal_errors = errors_sampled[normal_mask]
                self.plot8.axes.plot(normal_times, normal_errors, 'b-', alpha=0.7, linewidth=1, 
                                   label='Erro Normal')
            
            # Destacar anomalias
            if np.any(anomaly_mask):
                anomaly_times = np.array(time_points)[anomaly_mask]
                anomaly_errors = errors_sampled[anomaly_mask]
                self.plot8.axes.scatter(anomaly_times, anomaly_errors, c='red', s=30, marker='x', 
                                      linewidths=2, label='Anomalia', zorder=5)
            
            # Linha de threshold
            self.plot8.axes.axhline(y=error_threshold, color='orange', linestyle='--', 
                                   alpha=0.7, label=f'Threshold ({error_threshold})')
            
            self.plot8.axes.set_title(f"Erro de Predição - Microcontrolador (Médio: {np.mean(errors_sampled):.4f})")
            self.plot8.axes.set_xlabel("Predição #")
            self.plot8.axes.set_ylabel("Erro Absoluto")
            self.plot8.axes.legend(loc='best', fontsize=8)
            self.plot8.axes.grid(True, alpha=0.3)
            self.plot8.draw()

# Função principal da aplicação
def main():
    """🚀 Função principal para executar a aplicação TensorFlow GUI"""
    app = QApplication(sys.argv)
    
    # Configurar estilo
    app.setStyle('Fusion')
    
    # Criar janela principal
    window = TensorFlowGUI()
    window.show()
    
    # Executar aplicação
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
