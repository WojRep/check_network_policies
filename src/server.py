import csv
import socket
import os
import platform
import argparse
import sys
import signal
import ctypes
from logger import setup_logger
from host_info import get_fqdn, get_all_local_ips, is_matching_entry
from port_handler import parse_port_range
from connection_handlers import start_server

def load_client_data(csv_file):
    """
    Wczytuje dane klienta z pliku CSV, obsługując zarówno ścieżkę względną jak i absolutną
    """
    try:
        # Najpierw próbujemy użyć podanej ścieżki bezpośrednio
        with open(csv_file, mode="r") as file:
            reader = csv.DictReader(file)
            return list(reader)
    except FileNotFoundError:
        try:
            # Jeśli nie znaleziono, próbujemy użyć ścieżki względnej do zasobów
            resource_path = get_resource_path(csv_file)
            with open(resource_path, mode="r") as file:
                reader = csv.DictReader(file)
                return list(reader)
        except FileNotFoundError:
            print(f"[ERROR] Nie można znaleźć pliku konfiguracyjnego: {csv_file}")
            print("[ERROR] Sprawdzono ścieżki:")
            print(f"        - {os.path.abspath(csv_file)}")
            print(f"        - {os.path.abspath(resource_path)}")
            sys.exit(1)

def setup_argument_parser():
    parser = argparse.ArgumentParser(description='Network connection tester server')
    parser.add_argument('--debug', action='store_true', help='Włącz tryb debugowania')
    parser.add_argument('--config', type=str, help='Ścieżka do pliku konfiguracyjnego CSV', 
                       default='network_policy.csv')
    return parser

def get_resource_path(relative_path):
    """
    Pobiera absolutną ścieżkę do zasobu, działając zarówno w trybie deweloperskim
    jak i w skompilowanej aplikacji PyInstallera
    """
    try:
        # PyInstaller tworzy folder tymczasowy i przechowuje ścieżkę w _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Jeśli nie jesteśmy w PyInstallerze, używamy bieżącego katalogu
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def main():
    # Sprawdź uprawnienia przy starcie
    is_admin = False
    if platform.system() == "Windows":
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    else:
        is_admin = os.geteuid() == 0
        
    # Parsowanie argumentów wiersza poleceń
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Inicjalizacja zmiennych globalnych
    hostname = socket.gethostname()
    local_fqdn = get_fqdn()
    local_ips = get_all_local_ips()
    
    # Konfiguracja loggera
    logger = setup_logger(hostname)
    
    # Wyświetlenie informacji o hoście i uprawnieniach
    logger.info("Informacje o serwerze:")
    logger.info(f"Hostname: {hostname}")
    logger.info(f"FQDN: {local_fqdn}")
    logger.info(f"Adresy IP: {', '.join(local_ips)}")
    logger.info(f"Uruchomiono z uprawnieniami administratora: {'Tak' if is_admin else 'Nie'}")
    
    if not is_admin:
        logger.warning("Program uruchomiony bez uprawnień administratora - porty poniżej 1024 będą niedostępne")
    
    # Wczytanie pliku konfiguracyjnego
    config = load_client_data(args.config)
    
    
    # Lista aktywnych wątków
    active_threads = []
    
    # Przetwarzanie konfiguracji
    for entry in config:
        # Sprawdzenie czy entry pasuje do hosta
        if not is_matching_entry(entry, local_ips, local_fqdn):
            logger.debug(f"Ignorowanie wpisu: {entry}")
            continue
        
        # Obsługa portów
        try:
            ports = parse_port_range(entry['dst_port'])
            protocol = entry['protocol'].lower()
            
            # Explicite sprawdzenie i odrzucenie ICMP
            if protocol == 'icmp':
                logger.warning(f"Protokół ICMP nie jest obsługiwany - wpis ignorowany")
                continue
            
            # Sprawdzenie czy protokół jest obsługiwany
            if protocol not in ['tcp', 'udp']:
                logger.warning(f"Nieobsługiwany protokół: {protocol}. Dozwolone tylko TCP i UDP.")
                continue
            
            for port in ports:
                thread = start_server(port, protocol)
                if thread:
                    active_threads.append(thread)
                    logger.info(f"Uruchomiono serwer {protocol.upper()} na porcie {port}")
        
        except Exception as e:
            logger.error(f"Błąd podczas konfiguracji portu: {e}")
    
    # Obsługa sygnału CTRL+C
    def signal_handler(signum, frame):
        logger.info("\nZatrzymywanie serwera...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Utrzymuj program uruchomiony
    logger.info("Serwer uruchomiony. Naciśnij CTRL+C aby zakończyć.")
    while True:
        try:
            signal.pause()
        except (KeyboardInterrupt, SystemExit):
            break

if __name__ == "__main__":
    main()