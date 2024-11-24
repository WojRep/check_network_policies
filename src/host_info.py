import socket
import psutil
import subprocess
import platform
import logging
from port_handler import check_port_permissions, parse_port_range

def get_fqdn():
    """
    Pobiera FQDN hosta z obsługą różnych systemów operacyjnych
    """
    hostname = socket.gethostname()
    logger = logging.getLogger('NetworkPolicyServer')
    
    try:
        if platform.system() == "Darwin":  # macOS
            try:
                fqdn = subprocess.check_output(["hostname", "-f"], 
                                            stderr=subprocess.DEVNULL,
                                            text=True).strip()
                if fqdn:
                    return fqdn
            except:
                pass
                
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
            
    except Exception as e:
        logger.error(f"Błąd podczas pobierania FQDN: {e}")
        fqdn = f"{hostname}.local"
    
    return fqdn

def get_all_local_ips():
    """
    Pobiera wszystkie lokalne adresy IP
    """
    local_ips = []
    for interface, snics in psutil.net_if_addrs().items():
        for snic in snics:
            if snic.family == socket.AF_INET:
                local_ips.append(snic.address)
    return local_ips

def is_matching_entry(entry, local_ips, local_fqdn):
    """
    Sprawdza czy wpis konfiguracyjny pasuje do lokalnego hosta
    i czy ma odpowiednie uprawnienia
    """
    logger = logging.getLogger('NetworkPolicyServer')
    
    # Sprawdzenie IP
    ip_match = entry['dst_ip'] in local_ips
    if not ip_match:
        logger.debug(f"Ignorowanie wpisu - niezgodne IP: {entry['dst_ip']}, lokalne IP: {local_ips}")
        return False
        
    # Jeśli jest dopasowanie IP, sprawdzamy FQDN tylko jeśli nie jest to wildcard/pusty/none
    if (entry['dst_fqdn'] and 
        entry['dst_fqdn'] not in ['*', 'none', 'null', ''] and 
        entry['dst_fqdn'].lower() != local_fqdn.lower()):
        # Logujemy to jako informację debugową, ale nie odrzucamy wpisu
        logger.debug(f"Ostrzeżenie: Niezgodne FQDN: {entry['dst_fqdn']} != {local_fqdn}")
    
    # Jeśli mamy dopasowanie IP, sprawdzamy uprawnienia dla portów
    try:
        ports = parse_port_range(entry['dst_port'])
        for port in ports:
            has_permission, permission_error = check_port_permissions(port)
            if not has_permission:
                logger.error(f"Brak uprawnień dla portu {port}: {permission_error}")
                return False
    except ValueError as e:
        logger.error(f"Błąd w specyfikacji portu {entry['dst_port']}: {e}")
        return False

    # Logujemy sukces
    logger.debug(f"Zaakceptowano wpis dla IP: {entry['dst_ip']}, port: {entry['dst_port']}, protokół: {entry['protocol']}")
    return True