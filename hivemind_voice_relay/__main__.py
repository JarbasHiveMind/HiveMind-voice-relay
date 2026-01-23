import click
from ovos_utils import wait_for_exit_signal
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import init_service_logger, LOG

from hivemind_bus_client import HiveMessageBusClient
from hivemind_bus_client.identity import NodeIdentity
from hivemind_voice_relay.service import HiveMindVoiceRelay


# TODO - add a flag to use FakeBus instead of real websocket
@click.command(help="connect to HiveMind Sound Server")
@click.option("--host", help="hivemind host", type=str, default="")
@click.option("--key", help="Access Key", type=str, default="")
@click.option("--password", help="Password for key derivation", type=str, default="")
@click.option("--port", help="HiveMind port number", type=int, required=False)
@click.option("--selfsigned", help="accept self signed certificates", is_flag=True)
@click.option("--siteid", help="location identifier for message.context", type=str, default="")
def connect(host, key, password, port, selfsigned, siteid):
    """
    Start and run the HiveMind Voice Relay service using provided or stored node identity.
    
    This function initializes logging, resolves missing credentials from the local NodeIdentity, validates and normalizes the host and port, connects to the HiveMind message bus, starts the voice relay service in a daemon thread, optionally starts PHAL if available, and blocks until an exit signal is received; on exit it stops the relay and shuts down PHAL if started.
    
    Parameters:
        host (str): WebSocket URL or hostname of the HiveMind master (scheme will be prefixed if missing).
        key (str): Access key for the node; if omitted the value from NodeIdentity is used.
        password (str): Password for the node; if omitted the value from NodeIdentity is used.
        port (int): Port to connect to; if omitted the value from NodeIdentity or 5678 is used.
        selfsigned (bool): Allow connecting to a server with a self-signed TLS certificate when True.
        siteid (str): Site identifier to register with the bus; if omitted the value from NodeIdentity or "unknown" is used.
    
    Raises:
        RuntimeError: If key, password, or host are not available from arguments or NodeIdentity.
    """
    init_service_logger("HiveMind-voice-relay")

    identity = NodeIdentity()
    password = password or identity.password
    key = key or identity.access_key
    siteid = siteid or identity.site_id or "unknown"
    host = host or identity.default_master
    port = port or identity.default_port or 5678

    if not key or not password or not host:
        raise RuntimeError("NodeIdentity not set, please pass key/password/host or "
                           "call 'hivemind-client set-identity'")

    if not host.startswith("ws://") and not host.startswith("wss://"):
        host = "ws://" + host

    if not host.startswith("ws"):
        LOG.error("Invalid host, please specify a protocol")
        LOG.error(f"ws://{host} or wss://{host}")
        exit(1)

    # connect to hivemind
    bus = HiveMessageBusClient(key=key,
                               password=password,
                               port=port,
                               host=host,
                               useragent="VoiceRelayV1.0.0",
                               self_signed=selfsigned)
    bus.connect(site_id=siteid)

    # STT listener thread
    service = HiveMindVoiceRelay(bus=bus)
    service.daemon = True
    service.start()

    try:
        from ovos_PHAL.service import PHAL
        phal = PHAL(bus=bus)
        phal.start()
    except ImportError:
        print("PHAL is not available")
        phal = None

    wait_for_exit_signal()

    service.stop()
    if phal:
        phal.shutdown()


if __name__ == '__main__':
    connect()