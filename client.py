import csv
import socket
import tkinter as tk

# Funkcja do wczytania danych klienta
def load_client_data(csv_file):
    client_data = []
    with open(csv_file, mode="r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            client_data.append(row)
    return client_data

# Funkcja do testowania połączeń
def test_connections(client_data):
    results = []
    for entry in client_data:
        try:
            with socket.create_connection((entry["dsc_ip"], int(entry["dsc_port"])), timeout=5) as sock:
                sock.sendall("PING".encode("utf-8"))
                response = sock.recv(1024).decode("utf-8")
                if response == "PONG":
                    results.append((entry["dsc_ip"], entry["dsc_port"], "SUCCESS"))
                else:
                    results.append((entry["dsc_ip"], entry["dsc_port"], "FAILED"))
        except Exception as e:
            results.append((entry["dsc_ip"], entry["dsc_port"], f"ERROR: {e}"))
    return results

# Okno GUI dla klienta
def show_results(results):
    window = tk.Tk()
    window.title("Client Results")
    for ip, port, status in results:
        tk.Label(window, text=f"{ip}:{port} -> {status}").pack()
    tk.Button(window, text="Exit", command=window.destroy).pack()
    window.mainloop()

if __name__ == "__main__":
    client_data = load_client_data("network_policy.csv")
    results = test_connections(client_data)
    show_results(results)
