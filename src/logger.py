import logging
from datetime import datetime
import os

def setup_logger(hostname):
    """
    Konfiguruje logger z zapisem do pliku według wzoru hostname_data.log
    """
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = f"{hostname}_{timestamp}.log"
    
    logger = logging.getLogger('NetworkPolicyServer')
    logger.setLevel(logging.DEBUG)
    
    # Wyczyść istniejące handlery
    logger.handlers.clear()
    
    # Handler do pliku - wszystkie logi (DEBUG i wyżej)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Handler do konsoli - tylko INFO i wyżej
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.debug(f"=== Rozpoczęcie nowej sesji logowania: {timestamp} ===")
    logger.debug(f"Plik logu: {log_filename}")
    
    return logger