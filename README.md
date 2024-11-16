# Ogólny opis projektu

Dwa programy do sprawdzania otwartości polityk sieciowych:

    Serwer (server.py): Aplikacja weryfikująca implementację polityk sieciowych, nasłuchująca na określonych portach i odsyłająca odpowiedzi PONG.
    Klient (client.py): Aplikacja testująca, która inicjuje połączenia z serwerem i wysyła pakiety PING.

Programy obsługują polityki zapisane w pliku `network_policy.csv`. Serwer oraz klient realizują zadania zgodnie z opisanymi wymaganiami.

# Struktura pliku `network_policy.csv`

Kolumny w pliku CSV:
    src_ip: Adres IP źródła.
    src_fqdn: Pełna nazwa domenowa źródła.
    src_port: Port źródłowy (lub zakres portów).
    protocol: Protokół transmisji (TCP/UDP).
    dst_ip: Adres IP celu.
    dst_fqdn: Pełna nazwa domenowa celu.
    dst_port: Port docelowy.
    description: Opis połączenia.

Przykład pliku `network_policy.csv`:
```
src_ip,src_fqdn,src_port,protocol,dst_ip,dst_fqdn,dst_port,description
192.168.43.2,fre-34-ssd.dom.sd234.cust.com,*,tcp,192.168.44.54,fre-36.rsd.dom.sd234.cust.com,443,Komunikacja HTTPS
192.168.43.2,fre-34-ssd.dom.sd234.cust.com,*,tcp,192.168.44.54,fre-36.rsd.dom.sd234.cust.com,80,Komunikacja HTTP
192.168.43.2,fre-34-ssd.dom.sd234.cust.com,5060,udp,192.168.44.54,fre-36.rsd.dom.sd234.cust.com,5060,Komunikacja VoIP
192.168.43.2,fre-34-ssd.dom.sd234.cust.com,6000-8000,udp,192.168.44.54,fre-36.rsd.dom.sd234.cust.com,5999,Ruch UDP z losowym portem źródłowym
192.168.43.2,fre-34-ssd.dom.sd234.cust.com,*,icmp,192.168.44.54,fre-36.rsd.dom.sd234.cust.com,*,Dozwolony ruch ICMP (ping)
```

# Działanie programu

    Serwer (server.py):
        Otwiera porty dla polityk przypisanych do danego hosta.
        Odbiera pakiety PING i odpowiada PONG.
        Informuje o zajętości portów i wyświetla nazwę aplikacji oraz PID.

    Klient (client.py):
        Ładuje polityki z CSV.
        Nawiązuje połączenia do docelowych hostów i portów.
        Wyświetla wyniki testów w formie okna GUI.

# Wymagania

Python 3.6+
Biblioteki: psutil


# Uruchomienie

`pip install --upgrade pip`
`pip install -U pyinstaller`


Do stworzenia plików wykonywalnych można użyć PyInstaller:

    `pyinstaller --onefile server.py`
    `pyinstaller --onefile client.py --add-data "network_policy.csv;."`

```
# Tworzenie dla Linux/MacOS
pyinstaller --onefile client.py --add-data "network_policy.csv:."
# Tworzenie dla Windows x86
pyinstaller --onefile -w client.py --add-data "network_policy.csv:." --name client_x86.exe --distpath dist/x86
```
