from lf_toolkit.io.tcp_listener import TCPListener


class TestTCPListenerAddressParsing:

    def test_default_address(self):
        listener = TCPListener(None)
        assert listener.host == "127.0.0.1"
        assert listener.port == 7321

    def test_custom_address(self):
        listener = TCPListener("0.0.0.0:9000")
        assert listener.host == "0.0.0.0"
        assert listener.port == 9000

    def test_ipv6_address(self):
        listener = TCPListener("::1:9000")
        assert listener.host == "::1"
        assert listener.port == 9000
