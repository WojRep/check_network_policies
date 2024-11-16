import csv
import socket
import os
import psutil
import subprocess
import platform
import argparse
import sys

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
    
    try:
        if platform.system() == "Darwin":  # macOS
            try:
                fqdn = subprocess.check_output(["hostname", "-f"], 
                                            stderr=subprocess.DEVNULL,
                                            text=True).strip()
                if fqdn:
                    return fqdn
            except:
                try:
                    fqdn = subprocess.check_output(["hostname"], 
                                                stderr=subprocess.DEVNULL,
                                                text=True).strip()
                    if fqdn:
                        return fqdn
                except:
                    pass
        
        fqdn = socket.getfqdn()
        
        if fqdn == hostname or "in-addr.arpa" in fqdn:
            fqdn = f"{hostname}.local"
            
    except:
        fqdn = f"{hostname}.local"
    
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
    Sprawdza czy dany wpis powinien być testowany na podstawie lokalnego IP i FQDN
    """
    is_matching_ip = entry["src_ip"] in local_ips
    is_matching_fqdn = entry["src_fqdn"].lower() == local_fqdn.lower()
    return is_matching_ip or is_matching_fqdn

def test_connections(client_data, local_ips, local_fqdn):
    results = []
    success_count = 0
    failure_count = 0
    error_count = 0
    ignored_count = 0
    dns_warnings = []
    ignored_entries = []  # Lista na ignorowane wpisy
    
    for entry in client_data:
        # Weryfikacja DNS (tylko informacyjnie)
        dns_ok, dns_error = verify_dns_resolution(entry)
        if not dns_ok and dns_error:
            dns_warnings.append({
                "fqdn": entry["dst_fqdn"],
                "expected_ip": entry["dst_ip"],
                "error": dns_error
            })
        
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
            continue

        # Zawsze testujemy używając dst_ip, niezależnie od wyniku weryfikacji DNS
        try:
            protocol = entry["protocol"].upper()
            if protocol == "ICMP":
                print(f"[INFO] Testuję połączenie {protocol} z {entry['dst_ip']}")
                response = os.system(f"ping -c 1 {entry['dst_ip']} > /dev/null 2>&1")
                if response == 0:
                    results.append((entry["dst_ip"], "*", protocol, "SUCCESS"))
                    success_count += 1
                else:
                    results.append((entry["dst_ip"], "*", protocol, "FAILED"))
                    failure_count += 1
            else:
                print(f"[INFO] Testuję połączenie {protocol} z {entry['dst_ip']}:{entry['dst_port']}")
                if entry["dst_port"] == "*":
                    raise ValueError("Nie można użyć '*' jako portu dla TCP/UDP.")
                with socket.create_connection((entry["dst_ip"], int(entry["dst_port"])), timeout=5) as sock:
                    sock.sendall("PING".encode("utf-8"))
                    response = sock.recv(1024).decode("utf-8")
                    if response == "PONG":
                        results.append((entry["dst_ip"], entry["dst_port"], protocol, "SUCCESS"))
                        success_count += 1
                    else:
                        results.append((entry["dst_ip"], entry["dst_port"], protocol, "FAILED"))
                        failure_count += 1
        except socket.timeout:
            error_msg = "ERROR: Timed out"
            results.append((entry["dst_ip"], entry["dst_port"], protocol, error_msg))
            error_count += 1
        except ValueError as ve:
            error_msg = f"ERROR: {ve}"
            results.append((entry["dst_ip"], entry["dst_port"], protocol, error_msg))
            error_count += 1
        except Exception as e:
            error_msg = f"ERROR: {e}"
            results.append((entry["dst_ip"], entry["dst_port"], protocol, error_msg))
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
    print("\n[INFO] Wyniki testów:")
    # Wyświetlamy tylko wyniki testów (bez ignorowanych)
    for ip, port, protocol, status in results:
        if status != "IGNORED":  # Pokazujemy tylko nieignorowane wyniki
            status_color = {
                "SUCCESS": "\033[92m",  # Zielony
                "FAILED": "\033[91m",   # Czerwony
                "ERROR": "\033[93m",    # Żółty
            }.get(status.split(':')[0], "\033[0m")
            
            print(f"{ip}:{port} ({protocol}) -> {status_color}{status}\033[0m")
    
    print("\n[PODSUMOWANIE]")
    if stats['dns_warnings']:
        print(f"\n\033[93m\033[1m[Ostrzeżenia DNS: {len(stats['dns_warnings'])}]\033[0m")
        for warning in stats['dns_warnings']:
            print(f"- {warning['fqdn']}: {warning['error']}")
    
    print(f"\nUdane połączenia: {stats['success']}")
    print(f"Nieudane połączenia: {stats['failed']}")
    print(f"Błędy połączeń: {stats['errors']}")
    print(f"Zignorowane pozycje: {stats['ignored']}")
    print(f"Łącznie pozycji: {stats['success'] + stats['failed'] + stats['errors'] + stats['ignored']}")

    # W trybie debug pokazujemy szczegóły ignorowanych pozycji
    if debug and stats['ignored_entries']:
        print("\n\033[94m[DEBUG] Zignorowane pozycje:\033[0m")
        for entry in stats['ignored_entries']:
            print(f"- {entry['ip']}:{entry['port']} ({entry['protocol']}) "
                  f"[src_ip: {entry['src_ip']}, src_fqdn: {entry['src_fqdn']}]")

if __name__ == "__main__":
    try:
        # Parsowanie argumentów wiersza poleceń
        parser = setup_argument_parser()
        args = parser.parse_args()

        # Pobieranie informacji o hoście lokalnym
        local_fqdn = get_fqdn()
        local_ips = get_all_local_ips()

        # Wyświetlanie informacji o hoście
        print("[INFO] Uruchamiany program na hoście:")
        print(f"       FQDN: {local_fqdn}")
        print(f"       IP: {', '.join(local_ips)}")

        # Wczytywanie danych i testowanie połączeń
        print("[INFO] Wczytywanie danych klienta...")
        client_data = load_client_data(args.config)
        results, stats = test_connections(client_data, local_ips, local_fqdn)
        show_results(results, stats, args.debug)

    except KeyboardInterrupt:
        print("\n[INFO] Program zakończony przez użytkownika")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Wystąpił nieoczekiwany błąd: {str(e)}")
        if args.debug:
            import traceback
            print("\nSzczegóły błędu:")
            print(traceback.format_exc())
        sys.exit(1)