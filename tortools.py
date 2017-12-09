import requests
from stem import Signal
from stem.control import Controller

tor_password = 'hellotor12345'


def get_tor_session():
    session = requests.session()
    # Tor uses the 9050 port as the default socks port
    session.proxies = {'http': 'socks5://127.0.0.1:9050',
                       'https': 'socks5://127.0.0.1:9050'}
    return session


def change_tor_ip():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password=tor_password)
        controller.signal(Signal.NEWNYM)


if __name__ == '__main__':
    session = get_tor_session()
    print(requests.get("http://httpbin.org/ip").text)
    print(session.get("http://httpbin.org/ip").text)
    change_tor_ip()
    session = get_tor_session()
    print(session.get("http://httpbin.org/ip").text)
