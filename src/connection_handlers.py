import socket
import logging
import errno
import threading
from port_handler import create_server_socket, is_port_in_use, check_port_permissions

def handle_tcp_connection(port):
    """
    Obsługuje połączenia TCP na danym porcie
    """
    logger = logging.getLogger('NetworkPolicyServer')
    
    try:
        with create_server_socket(port, 'tcp') as server_socket:
            server_socket.listen(5)
            logger.info(f"Otwarto nasłuchiwanie na porcie TCP {port}")
            
            while True:
                try:
                    client_socket, addr = server_socket.accept()
                    logger.debug(f"Przyjęto połączenie TCP od {addr} na porcie {port}")
                    client_socket.close()
                except socket.error as e:
                    if e.errno != errno.EINTR:  # Ignoruj przerwania przez sygnały
                        logger.error(f"Błąd podczas obsługi połączenia TCP na porcie {port}: {e}")
                    break
    except PermissionError as e:
        logger.error(f"Port TCP {port}: {str(e)}")
    except Exception as e:
        logger.error(f"Port TCP {port}: {str(e)}")

def handle_udp_connection(port):
    """
    Obsługuje połączenia UDP na danym porcie
    """
    logger = logging.getLogger('NetworkPolicyServer')
    
    try:
        with create_server_socket(port, 'udp') as server_socket:
            logger.info(f"Otwarto nasłuchiwanie na porcie UDP {port}")
            
            while True:
                try:
                    data, addr = server_socket.recvfrom(1024)
                    if data.strip() == b"PING":
                        logger.debug(f"Otrzymano PING od {addr} na porcie {port}")
                        server_socket.sendto(b"PONG", addr)
                        logger.debug(f"Wysłano PONG do {addr} na porcie {port}")
                except socket.error as e:
                    if e.errno != errno.EINTR:
                        logger.error(f"Błąd podczas obsługi połączenia UDP na porcie {port}: {e}")
                    break
    except PermissionError as e:
        logger.error(f"Port UDP {port}: {str(e)}")
    except Exception as e:
        logger.error(f"Port UDP {port}: {str(e)}")

def start_server(port, protocol):
    """
    Uruchamia serwer na danym porcie i protokole
    """
    logger = logging.getLogger('NetworkPolicyServer')
    
    # Sprawdź uprawnienia i dostępność portu przed uruchomieniem wątku
    port_in_use, error_msg = is_port_in_use(port, protocol)
    if port_in_use:
        logger.error(f"{error_msg}")
        return None
        
    has_permission, permission_error = check_port_permissions(port)
    if not has_permission:
        logger.error(f"{permission_error}")
        return None

    if protocol.lower() == 'tcp':
        thread = threading.Thread(target=handle_tcp_connection, args=(port,))
    else:
        thread = threading.Thread(target=handle_udp_connection, args=(port,))
    
    thread.daemon = True
    thread.start()
    return thread