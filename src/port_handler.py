import socket
import os
import platform
import logging
import errno
from contextlib import contextmanager
import threading

def check_port_permissions(port):
    """
    Sprawdza czy proces ma uprawnienia do otwarcia danego portu
    Uwzględnia różnice między Windows a Linux/Unix
    """
    logger = logging.getLogger('NetworkPolicyServer')
    
    if platform.system() == "Windows":
        # W Windows sprawdzamy tylko czy jesteśmy administratorem
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if not is_admin and port < 1024:
                return False, "Porty poniżej 1024 wymagają uprawnień administratora w Windows"
        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania uprawnień administratora Windows: {e}")
            return False, f"Nie można zweryfikować uprawnień: {str(e)}"
    else:
        # W Linux/Unix sprawdzamy EUID
        if port < 1024 and os.geteuid() != 0:
            return False, "Porty poniżej 1024 wymagają uprawnień root w systemach Linux/Unix"
    
    return True, None

def is_port_in_use(port, protocol='tcp'):
    """
    Sprawdza czy port jest już w użyciu
    Rozszerzone sprawdzanie dla Windows i Linux
    """
    logger = logging.getLogger('NetworkPolicyServer')
    try:
        if protocol.lower() == 'tcp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        sock.bind(('', port))
        sock.close()
        return False, None
    except PermissionError:
        error_msg = (f"Brak uprawnień do otwarcia portu {port} ({protocol.upper()}). "
                    f"System: {platform.system()}")
        if platform.system() == "Windows":
            error_msg += ". Uruchom program jako administrator"
        else:
            error_msg += ". Uruchom program z uprawnieniami root"
        return True, error_msg
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            return True, f"Port {port} ({protocol.upper()}) jest już w użyciu"
        elif e.errno == errno.EACCES:
            if platform.system() == "Windows":
                return True, f"Brak uprawnień do otwarcia portu {port} ({protocol.upper()}). Uruchom program jako administrator"
            else:
                return True, f"Brak uprawnień do otwarcia portu {port} ({protocol.upper()}). Uruchom program z uprawnieniami root"
        else:
            return True, f"Błąd podczas sprawdzania portu {port} ({protocol.upper()}): {str(e)}"

def parse_port_range(port_spec):
    """
    Parsuje specyfikację portu, zwraca listę portów
    Dodane sprawdzanie poprawności zakresu
    """
    try:
        if '-' in port_spec:
            start, end = map(int, port_spec.split('-'))
            if start < 0 or end > 65535:
                raise ValueError(f"Porty muszą być w zakresie 0-65535 (podano {start}-{end})")
            if start > end:
                raise ValueError(f"Nieprawidłowy zakres portów: {start}-{end}")
            return list(range(start, end + 1))
        else:
            port = int(port_spec)
            if port < 0 or port > 65535:
                raise ValueError(f"Port musi być w zakresie 0-65535 (podano {port})")
            return [port]
    except ValueError as e:
        raise ValueError(f"Nieprawidłowa specyfikacja portu '{port_spec}': {str(e)}")

@contextmanager
def create_server_socket(port, protocol='tcp'):
    """
    Context manager do tworzenia i zamykania socketu serwera
    Rozszerzone logowanie błędów
    """
    logger = logging.getLogger('NetworkPolicyServer')
    
    try:
        if protocol.lower() == 'tcp':
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Sprawdź uprawnienia przed próbą bindowania
        has_permission, permission_error = check_port_permissions(port)
        if not has_permission:
            error_msg = f"Port {port} ({protocol.upper()}): {permission_error}"
            logger.error(error_msg)
            if port < 1024:
                if platform.system() == "Windows":
                    logger.error(f"Aby otworzyć port {port}, uruchom program jako administrator Windows")
                else:
                    logger.error(f"Aby otworzyć port {port}, uruchom program z uprawnieniami root (sudo)")
            raise PermissionError(error_msg)
        
        try:
            sock.bind(('', port))
        except PermissionError:
            error_msg = f"Brak uprawnień do otwarcia portu {port} ({protocol.upper()})"
            if platform.system() == "Windows":
                error_msg += ". Uruchom program jako administrator Windows"
            else:
                error_msg += ". Uruchom program z uprawnieniami root (sudo)"
            logger.error(error_msg)
            raise PermissionError(error_msg)
        except OSError as e:
            if e.errno == errno.EACCES:
                error_msg = f"Brak uprawnień do otwarcia portu {port} ({protocol.upper()})"
                if platform.system() == "Windows":
                    error_msg += ". Uruchom program jako administrator Windows"
                else:
                    error_msg += ". Uruchom program z uprawnieniami root (sudo)"
                logger.error(error_msg)
                raise PermissionError(error_msg)
            elif e.errno == errno.EADDRINUSE:
                error_msg = f"Port {port} ({protocol.upper()}) jest już w użyciu"
                logger.error(error_msg)
                raise
            else:
                error_msg = f"Błąd podczas otwierania portu {port} ({protocol.upper()}): {str(e)}"
                logger.error(error_msg)
                raise
        
        yield sock
    
    except Exception as e:
        if not str(e):  # Jeśli wyjątek nie ma opisu
            error_msg = f"Nieznany błąd podczas tworzenia socketu dla portu {port} ({protocol.upper()})"
            logger.error(error_msg)
            raise Exception(error_msg)
        raise
    finally:
        try:
            sock.close()
        except:
            pass