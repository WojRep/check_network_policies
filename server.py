import csv
import socket
import threading
import tkinter as tk
from tkinter import messagebox
import psutil  # Do wykrywania procesów na zajętych portach

# Funkcja do nasłuchiwania na określonym porcie
def listen_on_port(ip, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((ip, port))
        sock.listen(1)
        print(f"Nasłuchuję na {ip}:{port}")

        while True:
            conn, addr = sock.accept()
            data = conn.recv(1024).decode("utf-8")
            if data == "PING":
                print(f"Otrzymano PING od {addr}. Wysyłam PONG.")
                conn.sendall("PONG".encode("utf-8"))
            conn.close()
    except OSError as e:
        proc_info = [p.info for p in psutil.process_iter(attrs=["pid", "name"]) if port in p.info.get("pid", "")]
        print(f"Port {port} jest zajęty przez {proc_info}.")
    except Exception as e:
        print(f"Błąd: {e}")

# Funkcja do uruchomienia serwera dla wybranych danych
def run_server(server_data):
    threads = []
    for entry in server_data:
        threading.Thread(target=listen_on_port, args=(entry["src_ip"], int(entry["dsc_port"]))).start()

# Funkcja do odczytu danych serwera
def load_server_data(csv_file, host_ip):
    server_data = []
    with open(csv_file, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["dsc_ip"] == host_ip or row["dsc_fqdn"] == socket.getfqdn():
                server_data.append(row)
    return server_data

# Okno GUI dla serwera
def create_gui():
    window = tk.Tk()
    window.title("Server")
    tk.Label(window, text="Running server").pack()
    tk.Button(window, text="Exit", command=window.destroy).pack()
    window.mainloop()

if __name__ == "__main__":
    host_ip = socket.gethostbyname(socket.gethostname())
    server_data = load_server_data("network_policy.csv", host_ip)

    if server_data:
        print("Uruchamiam serwer dla danych:")
        for entry in server_data:
            print(entry)
        threading.Thread(target=run_server, args=(server_data,)).start()
        create_gui()
    else:
        print("Brak pasujących danych serwera w politykach.")
