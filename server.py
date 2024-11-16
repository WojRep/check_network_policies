import csv
import socket
import threading
import psutil

# Funkcja do nasłuchiwania na określonym porcie
def listen_on_port(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((ip, port))
        sock.listen(1)
        print(f"[INFO] Nasłuchuję na {ip}:{port}")

        while True:
            conn, addr = sock.accept()
            data = conn.recv(1024).decode("utf-8")
            if data == "PING":
                print(f"[INFO] Otrzymano PING od {addr}. Wysyłam PONG.")
                conn.sendall("PONG".encode("utf-8"))
            conn.close()
    except OSError as e:
        print(f"[ERROR] Port {port} jest zajęty. Szczegóły: {e}")
        proc_info = [
            p.info for p in psutil.process_iter(attrs=["pid", "name"]) if port in p.info.get("pid", [])
        ]
        print(f"[INFO] Proces zajmujący port: {proc_info}")
    except Exception as e:
        print(f"[ERROR] Błąd: {e}")

# Funkcja do uruchomienia serwera dla wybranych danych
def run_server(server_data):
    threads = []
    for entry in server_data:
        thread = threading.Thread(target=listen_on_port, args=(entry["src_ip"], int(entry["dsc_port"])))
        thread.start()
        threads.append(thread)
    for t in threads:
        t.join()

# Funkcja do odczytu danych serwera
def load_server_data(csv_file, host_ip):
    server_data = []
    with open(csv_file, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["dsc_ip"] == host_ip or row["dsc_fqdn"] == socket.getfqdn():
                server_data.append(row)
    return server_data

if __name__ == "__main__":
    print("[INFO] Uruchamianie serwera...")
    host_ip = socket.gethostbyname(socket.gethostname())
    server_data = load_server_data("network_policy.csv", host_ip)

    if server_data:
        print("[INFO] Uruchamiam serwer dla danych:")
        for entry in server_data:
            print(entry)
        run_server(server_data)
    else:
        print("[INFO] Brak pasujących danych serwera w politykach.")
