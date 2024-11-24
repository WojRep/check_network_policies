import csv
import socket
import os
import psutil
import subprocess
import platform
import argparse
import sys
import logging
from datetime import datetime

def setup_logger(script_name):
    """
    Konfiguruje logger z zapisem do pliku według wzoru nazwa_data.log
    Plik: poziom DEBUG
    Konsola: poziom INFO
    """
    # Pobierz nazwę skryptu bez rozszerzenia
    base_name = os.path.splitext(os.path.basename(script_name))[0]
    
    # Utwórz nazwę pliku logu według wzoru nazwa_data.log
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = f"{base_name}_{timestamp}.log"
    
    # Konfiguracja głównego loggera
    logger = logging.getLogger('NetworkTester')
    logger.setLevel(logging.DEBUG)  # Główny logger musi być na poziomie DEBUG
    
    # Wyczyść istniejące handlery (gdyby jakieś były)
    logger.handlers.clear()
    
    # Handler do pliku - wszystkie logi (DEBUG i wyżej)
    file_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Handler do konsoli - tylko INFO i wyżej
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')  # Prostsza forma dla konsoli
    console_handler.setFormatter(console_formatter)
    
    # Dodaj handlery do loggera
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log rozpoczęcia sesji
    logger.debug(f"=== Rozpoczęcie nowej sesji logowania: {timestamp} ===")
    logger.debug(f"Plik logu: {log_filename}")
    
    return logger

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

def setup_argument_parser():
    parser = argparse.ArgumentParser(description='Network connection tester')
    parser.add_argument('--debug', action='store_true', help='Włącz tryb debugowania')
    parser.add_argument('--config', type=str, help='Ścieżka do pliku konfiguracyjnego CSV', 
                       default='network_policy.csv')
    return parser

def get_fqdn():
    """
    Ulepszona funkcja do pobierania FQDN z obsługą macOS
    """
    hostname = socket.gethostname()
    logger = logging.getLogger('NetworkTester')
    
    try:
        if platform.system() == "Darwin":  # macOS
            logger.debug("Wykryto system macOS - próba pobrania FQDN")
            try:
                fqdn = subprocess.check_output(["hostname", "-f"], 
                                            stderr=subprocess.DEVNULL,
                                            text=True).strip()
                if fqdn:
                    logger.debug(f"Pobrano FQDN za pomocą komendy 'hostname -f': {fqdn}")
                    return fqdn
            except:
                logger.debug("Nie udało się pobrać FQDN za pomocą 'hostname -f'")
                try:
                    fqdn = subprocess.check_output(["hostname"], 
                                                stderr=subprocess.DEVNULL,
                                                text=True).strip()
                    if fqdn:
                        logger.debug(f"Pobrano FQDN za pomocą komendy 'hostname': {fqdn}")
                        return fqdn
                except:
                    logger.debug("Nie udało się pobrać FQDN za pomocą 'hostname'")
                    pass
        
        fqdn = socket.getfqdn()
        logger.debug(f"Pobrano FQDN za pomocą socket.getfqdn(): {fqdn}")
        
        if fqdn == hostname or "in-addr.arpa" in fqdn:
            fqdn = f"{hostname}.local"
            logger.debug(f"Użyto domyślnej nazwy .local: {fqdn}")
            
    except Exception as e:
        logger.error(f"Błąd podczas pobierania FQDN: {e}")
        fqdn = f"{hostname}.local"
        logger.debug(f"Użyto domyślnej nazwy .local po błędzie: {fqdn}")
    
    return fqdn

def get_all_local_ips():
    local_ips = []
    for interface, snics in psutil.net_if_addrs().items():
        for snic in snics:
            if snic.family == socket.AF_INET:
                local_ips.append(snic.address)
    return local_ips

def resolve_hostname(hostname):
    """
    Próbuje rozwiązać nazwę hosta na adres IP
    """
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None

def verify_dns_resolution(entry):
    """
    Sprawdza czy dst_fqdn rozwiązuje się na dst_ip
    Zwraca krotę (bool, str) gdzie:
    - bool to czy weryfikacja się powiodła
    - str to opis błędu (jeśli wystąpił)
    """
    if not entry["dst_fqdn"]:
        return True, None
        
    resolved_ip = resolve_hostname(entry["dst_fqdn"])
    if resolved_ip is None:
        warning = f"Nie można rozwiązać nazwy {entry['dst_fqdn']}"
        print(f"\033[93m\033[1m[WARNING] {warning}\033[0m")
        return False, warning
    
    if resolved_ip != entry["dst_ip"]:
        warning = f"{entry['dst_fqdn']} rozwiązuje się na {resolved_ip}, oczekiwano {entry['dst_ip']}"
        print(f"\033[93m\033[1m[WARNING] Niezgodność DNS: {warning}\033[0m")
        return False, warning
    
    return True, None

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

def should_test_connection(entry, local_ips, local_fqdn):
    """
    Sprawdza czy dany wpis powinien być testowany na podstawie lokalnego IP i FQDN.
    Obsługuje wildcard '*', pustą wartość i 'none' w src_ip i src_fqdn.
    """
    logger = logging.getLogger('NetworkTester')
    
    # Normalizacja wartości src_ip i src_fqdn
    src_ip = str(entry.get("src_ip", "")).strip().lower()
    src_fqdn = str(entry.get("src_fqdn", "")).strip().lower()
    
    # Lista wartości traktowanych jako wildcard
    wildcard_values = ["*", "", "none", "null", None]
    
    # Sprawdzanie czy którekolwiek pole jest wildcardem
    is_ip_wildcard = src_ip in wildcard_values
    is_fqdn_wildcard = src_fqdn in wildcard_values
    
    if is_ip_wildcard or is_fqdn_wildcard:
        if is_ip_wildcard:
            logger.debug(f"Znaleziono wildcard w src_ip: '{src_ip}'")
        if is_fqdn_wildcard:
            logger.debug(f"Znaleziono wildcard w src_fqdn: '{src_fqdn}'")
        return True
    
    # Sprawdzanie dokładnego dopasowania IP
    is_matching_ip = src_ip in local_ips
    # Sprawdzanie dokładnego dopasowania FQDN (bez uwzględniania wielkości liter)
    is_matching_fqdn = src_fqdn == local_fqdn.lower()
    
    if is_matching_ip:
        logger.debug(f"Dopasowano IP: {src_ip}")
    if is_matching_fqdn:
        logger.debug(f"Dopasowano FQDN: {src_fqdn}")
    
    return is_matching_ip or is_matching_fqdn

def test_tcp_connection(ip, port, timeout=5):
    """
    Testuje połączenie TCP
    """
    logger = logging.getLogger('NetworkTester')
    try:
        with socket.create_connection((ip, int(port)), timeout=timeout) as sock:
            logger.debug(f"Nawiązano połączenie TCP z {ip}:{port}")
            return True, None
    except Exception as e:
        return False, f"NOK -> {str(e)}"

def test_udp_connection(ip, port, timeout=1):
    """
    Testuje połączenie UDP wysyłając PING i oczekując na PONG
    """
    logger = logging.getLogger('NetworkTester')
    try:
        # Utworzenie gniazda UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        # Próba wysłania danych
        logger.debug(f"Wysyłanie PING UDP do {ip}:{port}")
        sock.sendto(b"PING", (ip, int(port)))
        
        # Oczekiwanie na odpowiedź PONG
        try:
            data, addr = sock.recvfrom(1024)
            if data.strip() == b"PONG":
                logger.debug(f"Otrzymano PONG od {ip}:{port}")
                return True, None
            else:
                logger.debug(f"Otrzymano nieprawidłową odpowiedź od {ip}:{port}: {data}")
                return False, "Otrzymano nieprawidłową odpowiedź"
        except socket.timeout:
            logger.debug(f"Timeout podczas oczekiwania na PONG od {ip}:{port}")
            return False, "NOK -> Brak odpowiedzi PONG w czasie 1 sekundy"
    except Exception as e:
        return False, str(e)
    finally:
        sock.close()

def test_ping(ip):
    """
    Testuje połączenie ICMP (ping) w sposób kompatybilny z Windows i Linux
    """
    logger = logging.getLogger('NetworkTester')
    
    # Określenie parametrów ping w zależności od systemu
    if platform.system().lower() == "windows":
        command = f"ping -n 1 -w 1000 {ip} > nul 2>&1"  # Windows: -n liczba pakietów, -w timeout w ms
        logger.debug(f"Używam komendy ping dla Windows: {command}")
    else:
        command = f"ping -c 1 -W 1 {ip} > /dev/null 2>&1"  # Linux/Unix: -c liczba pakietów, -W timeout w s
        logger.debug(f"Używam komendy ping dla Linux/Unix: {command}")
    
    response = os.system(command)
    logger.debug(f"Wynik polecenia ping dla {ip}: {response}")
    
    return response == 0

def parse_port_range(port_spec):
    """
    Parsuje specyfikację portu, zwraca listę portów
    """
    if '-' in port_spec:
        start, end = map(int, port_spec.split('-'))
        if start > end:
            raise ValueError(f"Nieprawidłowy zakres portów: {start}-{end}")
        return list(range(start, end + 1))
    else:
        return [int(port_spec)]


def test_connections(client_data, local_ips, local_fqdn, debug=False):
    logger = logging.getLogger('NetworkTester')
    results = []
    success_count = 0
    failure_count = 0
    error_count = 0
    ignored_count = 0
    dns_warnings = []
    ignored_entries = []

    for entry in client_data:
        # Weryfikacja DNS (tylko informacyjnie)
        dns_ok, dns_error = verify_dns_resolution(entry)
        if not dns_ok and dns_error:
            dns_warnings.append({
                "fqdn": entry["dst_fqdn"],
                "expected_ip": entry["dst_ip"],
                "error": dns_error
            })
            logger.debug(f"Ostrzeżenie DNS dla {entry['dst_fqdn']}: {dns_error}")
        
        # Sprawdzamy czy powinniśmy testować to połączenie
        if not should_test_connection(entry, local_ips, local_fqdn):
            ignored_entries.append({
                "ip": entry["dst_ip"],
                "port": entry["dst_port"],
                "protocol": entry["protocol"].upper(),
                "src_ip": entry["src_ip"],
                "src_fqdn": entry["src_fqdn"]
            })
            ignored_count += 1
            ignored_msg = (
                f"IGNORED: Połączenie zignorowane - nie pasuje do lokalnego hosta\n"
                f"         Docelowe: {entry['dst_ip']}:{entry['dst_port']} ({entry['protocol'].upper()})\n"
                f"         Źródłowe: IP={entry['src_ip']}, FQDN={entry['src_fqdn']}\n"
                f"         Lokalne: IP={', '.join(local_ips)}, FQDN={local_fqdn}"
            )
            logger.debug(ignored_msg)
            if debug:
                print(f"\033[93m{ignored_msg}\033[0m")
            continue

        # Testowanie połączenia
        try:
            protocol = entry["protocol"].upper()
            
            if protocol == "ICMP":
                logger.info(f"Testuję połączenie {protocol} z {entry['dst_ip']}")
                if test_ping(entry["dst_ip"]):
                    results.append((entry["dst_ip"], "*", protocol, "SUCCESS"))
                    logger.debug(f"SUCCESS: ICMP ping do {entry['dst_ip']} udany")
                    success_count += 1
                else:
                    results.append((entry["dst_ip"], "*", protocol, "FAILED"))
                    logger.debug(f"FAILED: ICMP ping do {entry['dst_ip']} nieudany")
                    failure_count += 1
            
            elif protocol in ["TCP", "UDP"]:
                if entry["dst_port"] == "*":
                    raise ValueError("Nie można użyć '*' jako portu dla TCP/UDP.")
                
                # Parsowanie zakresu portów
                ports = parse_port_range(entry["dst_port"])
                
                for port in ports:
                    logger.info(f"Testuję połączenie {protocol} z {entry['dst_ip']}:{port}")
                    
                    if protocol == "TCP":
                        success, error = test_tcp_connection(entry["dst_ip"], port)
                    else:  # UDP
                        success, error = test_udp_connection(entry["dst_ip"], port)
                    
                    if success:
                        results.append((entry["dst_ip"], str(port), protocol, "SUCCESS"))
                        logger.debug(f"SUCCESS: Połączenie {protocol} z {entry['dst_ip']}:{port} udane")
                        success_count += 1
                    else:
                        error_msg = f"ERROR: {error}" if error else "FAILED"
                        results.append((entry["dst_ip"], str(port), protocol, error_msg))
                        logger.debug(f"FAILED: Połączenie {protocol} z {entry['dst_ip']}:{port} nieudane - {error}")
                        failure_count += 1
            
            else:
                error_msg = f"ERROR: Nieobsługiwany protokół: {protocol}"
                results.append((entry["dst_ip"], entry["dst_port"], protocol, error_msg))
                logger.error(error_msg)
                error_count += 1

        except Exception as e:
            error_msg = f"ERROR: {str(e)}"
            results.append((entry["dst_ip"], entry["dst_port"], protocol, error_msg))
            logger.debug(f"ERROR: Nieoczekiwany błąd podczas łączenia z {entry['dst_ip']}:{entry['dst_port']} ({protocol}): {e}")
            error_count += 1

    return results, {
        "success": success_count, 
        "failed": failure_count, 
        "errors": error_count,
        "ignored": ignored_count,
        "dns_warnings": dns_warnings,
        "ignored_entries": ignored_entries
    }

    
def show_results(results, stats, debug=False):
    logger = logging.getLogger('NetworkTester')
    logger.info("\n")
    logger.info('######################################################')
    logger.info("\n")    
    logger.info("REZULTAT TESTU POŁACZEŃ:")
    logger.info('------------------------')
    logger.info("\n")   
    # Wyświetlamy tylko wyniki testów (bez ignorowanych)
    for ip, port, protocol, status in results:
        if status != "IGNORED":
            # Formatowanie adresu zgodnie z protokołem
            if protocol == "ICMP":
                address = f"{ip}/ping"
            else:
                # Dla TCP i UDP używamy formatu ip:port/protokół
                protocol_suffix = protocol.lower()
                address = f"{ip}:{port}/{protocol_suffix}"
            
            # Status do logu
            if "SUCCESS" in status:
                logger.info(f"{address} -> OK")
            elif "FAILED" in status:
                logger.error(f"{address} -> NOK")
            else:  # ERROR cases
                error_msg = status.replace("ERROR: ", "")
                logger.error(f"{address} -> {error_msg}")
    
    logger.info("\nPODSUMOWANIE")
    if stats['dns_warnings']:
        logger.warning(f"Ostrzeżenia DNS: {len(stats['dns_warnings'])}")
        for warning in stats['dns_warnings']:
            logger.warning(f"- {warning['fqdn']}: {warning['error']}")
    
    summary = f"""
    Udane połączenia: {stats['success']}
    Nieudane połączenia: {stats['failed']}
    Błędy połączeń: {stats['errors']}
    Zignorowane pozycje: {stats['ignored']}
    Łącznie pozycji: {stats['success'] + stats['failed'] + stats['errors'] + stats['ignored']}
    """
    logger.info(summary)

    if debug and stats['ignored_entries']:
        logger.debug("Zignorowane pozycje:")
        for entry in stats['ignored_entries']:
            if entry['protocol'] == "ICMP":
                address = f"{entry['ip']}/ping"
            else:
                protocol_suffix = entry['protocol'].lower()
                address = f"{entry['ip']}:{entry['port']}/{protocol_suffix}"
            logger.debug(
                f"- {address} [src_ip: {entry['src_ip']}, src_fqdn: {entry['src_fqdn']}]"
            )

if __name__ == "__main__":
    try:
        # Inicjalizacja loggera
        logger = setup_logger(sys.argv[0])
        logger.info("Uruchamianie programu...")
        
        # Parsowanie argumentów wiersza poleceń
        parser = setup_argument_parser()
        args = parser.parse_args()
        logger.debug(f"Argumenty wiersza poleceń: {args}")

        # Pobieranie informacji o hoście lokalnym
        local_fqdn = get_fqdn()
        local_ips = get_all_local_ips()
        
        logger.info(f"Uruchamiany program na hoście:")
        logger.info(f"FQDN: {local_fqdn}")
        logger.info(f"IP: {', '.join(local_ips)}")

        # Wczytywanie danych i testowanie połączeń
        logger.info("Wczytywanie danych klienta...")
        client_data = load_client_data(args.config)
        # Przekazujemy parametr debug do funkcji test_connections
        results, stats = test_connections(client_data, local_ips, local_fqdn, args.debug)
        show_results(results, stats, args.debug)

    except KeyboardInterrupt:
        logger.info("Program zakończony przez użytkownika")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Wystąpił nieoczekiwany błąd: {str(e)}")
        if args.debug:
            import traceback
            logger.error("Szczegóły błędu:")
            logger.error(traceback.format_exc())
        sys.exit(1)
