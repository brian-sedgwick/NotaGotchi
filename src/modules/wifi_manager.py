"""
WiFi Manager Module

Handles WiFi communication for NotaGotchi social features including:
- Background TCP server for receiving messages
- mDNS service discovery via avahi
- Message sending with acknowledgment
- Thread-safe callback system

Based on proven test code (test_wifi_*.py)
"""

import socket
import threading
import json
import time
import subprocess
from typing import Dict, List, Callable, Optional, Any
from . import config


class WiFiManager:
    """
    Manages WiFi communication for NotaGotchi

    Features:
    - Background TCP server (non-blocking)
    - mDNS service discovery
    - Message send/receive with acknowledgment
    - Thread-safe callback system
    """

    def __init__(self, device_name: str, port: int = None):
        """
        Initialize WiFi Manager

        Args:
            device_name: NotaGotchi device name (e.g., "notagotchi_Buddy")
            port: TCP port (default from config)
        """
        self.device_name = device_name
        self.port = port or config.WIFI_PORT

        # Server components
        self.server_socket = None
        self.server_thread = None
        self.running = False

        # mDNS via avahi-publish-service
        self.avahi_publish_process = None

        # Callbacks
        self.message_callbacks: List[Callable] = []
        self.callback_lock = threading.Lock()

        # Connection tracking
        self.active_connections = []
        self.connection_lock = threading.Lock()

    def start_server(self) -> bool:
        """
        Start background TCP server with mDNS advertising

        Returns:
            True if started successfully, False otherwise
        """
        if self.running:
            print("WiFi server already running")
            return True

        try:
            # Get local IP
            local_ip = self._get_local_ip()
            if not local_ip:
                print("❌ Could not determine local IP address")
                return False

            print(f"Starting WiFi server on {local_ip}:{self.port}")

            # Create TCP server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('', self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)  # Allow periodic checks

            # Setup mDNS advertising
            if not self._setup_mdns(local_ip):
                print("⚠️  mDNS setup failed, continuing without service advertisement")

            # Start server thread
            self.running = True
            self.server_thread = threading.Thread(
                target=self._server_loop,
                name="WiFiServerThread",
                daemon=True
            )
            self.server_thread.start()

            print(f"✅ WiFi server started: {self.device_name}")
            return True

        except Exception as e:
            print(f"❌ Failed to start WiFi server: {e}")
            self.running = False
            return False

    def stop_server(self):
        """Stop the WiFi server and cleanup"""
        if not self.running:
            return

        print("Stopping WiFi server...")
        self.running = False

        try:
            # Stop avahi-publish-service process
            if self.avahi_publish_process:
                self.avahi_publish_process.terminate()
                try:
                    self.avahi_publish_process.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    self.avahi_publish_process.kill()
                print("mDNS advertising stopped")

            # Close server socket
            if self.server_socket:
                self.server_socket.close()

            # Wait for thread to finish
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=2.0)

            print("✅ WiFi server stopped")

        except Exception as e:
            print(f"⚠️  Error during WiFi server shutdown: {e}")

    def discover_devices(self, duration: float = None) -> List[Dict[str, Any]]:
        """
        Discover NotaGotchi devices on network via avahi

        Args:
            duration: Scan duration in seconds (default from config)

        Returns:
            List of discovered devices with format:
            [{"name": "notagotchi_Buddy", "address": "192.168.0.100",
              "port": 5555, "properties": {...}}]
        """
        duration = duration or config.WIFI_DISCOVERY_TIMEOUT

        # Strip .local. suffix if present (avahi-browse works either way, but cleaner without)
        service_type = config.WIFI_SERVICE_TYPE.rstrip('.')
        if service_type.endswith('.local'):
            service_type = service_type[:-6]  # Remove '.local'

        # Run avahi-browse with parseable output
        cmd = [
            'avahi-browse',
            service_type,
            '-t',  # Terminate after dumping
            '-r',  # Resolve services
            '-p'   # Parseable output
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration
            )

            devices = {}

            # Parse avahi-browse output
            # Format: =;interface;protocol;name;type;domain;hostname;address;port;txt
            for line in result.stdout.split('\n'):
                if not line.startswith('='):
                    continue

                parts = line.split(';')
                if len(parts) < 10:
                    continue

                interface = parts[1]
                protocol = parts[2]  # IPv4 or IPv6
                name = parts[3]
                address = parts[7]
                port = parts[8]
                txt = parts[9] if len(parts) > 9 else ""

                # Only process IPv4 for now, skip localhost/loopback
                if address and port and protocol == 'IPv4' and address != '127.0.0.1':
                    device_info = {
                        'name': name,
                        'address': address,
                        'port': int(port),
                        'interface': interface,
                        'properties': {}
                    }

                    # Parse TXT records
                    if txt:
                        for item in txt.split():
                            if '=' in item:
                                k, v = item.split('=', 1)
                                device_info['properties'][k.strip('"')] = v.strip('"')

                    devices[name] = device_info

            return list(devices.values())

        except subprocess.TimeoutExpired:
            print(f"Discovery timeout after {duration} seconds")
            return []
        except FileNotFoundError:
            print("❌ avahi-browse not found. Install with: sudo apt-get install avahi-utils")
            return []
        except Exception as e:
            print(f"❌ Discovery error: {e}")
            return []

    def send_message(self, target_ip: str, target_port: int,
                    message_data: Dict[str, Any]) -> bool:
        """
        Send JSON message to target device with acknowledgment

        Args:
            target_ip: Target device IP address
            target_port: Target device port
            message_data: Message dictionary to send

        Returns:
            True if message sent and acknowledged, False otherwise
        """
        try:
            # Serialize message
            message_json = json.dumps(message_data)
            message_bytes = message_json.encode(config.MESSAGE_ENCODING)

            # Check size
            if len(message_bytes) > config.WIFI_MESSAGE_MAX_SIZE:
                print(f"❌ Message too large: {len(message_bytes)} bytes")
                return False

            # Connect to target
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(config.WIFI_CONNECTION_TIMEOUT)
            client_socket.connect((target_ip, target_port))

            # Send message
            client_socket.sendall(message_bytes)

            # Signal end of transmission (critical for server to process)
            client_socket.shutdown(socket.SHUT_WR)

            # Wait for acknowledgment
            response_data = client_socket.recv(1024)

            if response_data:
                response = json.loads(response_data.decode(config.MESSAGE_ENCODING))
                if response.get('status') == 'received':
                    client_socket.close()
                    return True

            client_socket.close()
            return False

        except socket.timeout:
            print(f"❌ Connection timeout to {target_ip}:{target_port}")
            return False
        except ConnectionRefusedError:
            print(f"❌ Connection refused by {target_ip}:{target_port}")
            return False
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False

    def register_callback(self, callback: Callable[[Dict, str], None]):
        """
        Register callback for incoming messages

        Callback signature: callback(message_data: dict, sender_ip: str)

        Args:
            callback: Function to call when message received
        """
        with self.callback_lock:
            self.message_callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """Remove a registered callback"""
        with self.callback_lock:
            if callback in self.message_callbacks:
                self.message_callbacks.remove(callback)

    def is_device_reachable(self, ip: str, port: int = None) -> bool:
        """
        Check if a device is reachable (quick connect test)

        Args:
            ip: Device IP address
            port: Device port (default: self.port)

        Returns:
            True if device responds, False otherwise
        """
        port = port or self.port

        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(2.0)  # Quick check
            result = test_socket.connect_ex((ip, port))
            test_socket.close()
            return result == 0
        except:
            return False

    # Private methods

    def _get_local_ip(self) -> Optional[str]:
        """Get local WiFi IP address"""
        try:
            # Method 1: Connect to external address to determine route
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            # Method 2: Try to get from wlan0
            try:
                result = subprocess.run(
                    ['ip', '-4', 'addr', 'show', 'wlan0'],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.split('\n'):
                    if 'inet ' in line:
                        ip = line.strip().split()[1].split('/')[0]
                        return ip
            except:
                pass

        return None

    def _setup_mdns(self, local_ip: str) -> bool:
        """
        Setup mDNS service advertisement via avahi-publish-service

        Uses avahi-daemon (system service) instead of python-zeroconf
        to avoid port 5353 conflicts.
        """
        try:
            # Build TXT record from service properties
            txt_records = []
            for key, value in config.SERVICE_PROPERTIES.items():
                txt_records.append(f"{key}={value}")

            # Strip .local. suffix if present (avahi-publish-service adds it automatically)
            service_type = config.WIFI_SERVICE_TYPE.rstrip('.')
            if service_type.endswith('.local'):
                service_type = service_type[:-6]  # Remove '.local'

            # avahi-publish-service command
            # Format: avahi-publish-service <name> <type> <port> [TXT records...]
            cmd = [
                'avahi-publish-service',
                self.device_name,  # Service name
                service_type,  # Service type (without .local.)
                str(self.port),  # Port
            ]

            # Add TXT records if any
            cmd.extend(txt_records)

            # Start avahi-publish-service as background process
            self.avahi_publish_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )

            # Give it a moment to start
            time.sleep(0.5)

            # Check if process is still running
            if self.avahi_publish_process.poll() is not None:
                # Process terminated - read error output
                _, stderr = self.avahi_publish_process.communicate()
                print(f"❌ avahi-publish-service failed:")
                if stderr:
                    print(f"   Error: {stderr.decode()}")
                return False

            print(f"✅ mDNS advertising: {self.device_name}")
            return True

        except FileNotFoundError:
            print("⚠️  avahi-publish-service not found. Install with: sudo apt-get install avahi-utils")
            return False
        except Exception as e:
            print(f"⚠️  mDNS setup error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _server_loop(self):
        """Background server loop (runs in thread)"""
        print("WiFi server thread started")

        while self.running:
            try:
                # Accept connections with timeout
                client_socket, client_address = self.server_socket.accept()

                # Handle in separate thread
                handler_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                handler_thread.start()

            except socket.timeout:
                # Normal timeout, check if should continue
                continue
            except OSError:
                # Socket closed
                break
            except Exception as e:
                if self.running:
                    print(f"Server error: {e}")

        print("WiFi server thread stopped")

    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """Handle incoming client connection"""
        sender_ip = client_address[0]

        try:
            # Receive data
            data = b""
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                data += chunk
                if len(data) >= config.WIFI_MESSAGE_MAX_SIZE:
                    break

            if data:
                # Parse message
                message_str = data.decode(config.MESSAGE_ENCODING)
                message_data = json.loads(message_str)

                # Send acknowledgment
                response = {
                    "status": "received",
                    "timestamp": time.time()
                }
                client_socket.sendall(
                    json.dumps(response).encode(config.MESSAGE_ENCODING)
                )

                # Invoke callbacks
                self._invoke_callbacks(message_data, sender_ip)

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON from {sender_ip}: {e}")
        except Exception as e:
            print(f"❌ Client handler error: {e}")
        finally:
            client_socket.close()

    def _invoke_callbacks(self, message_data: Dict, sender_ip: str):
        """Invoke all registered callbacks (thread-safe)"""
        with self.callback_lock:
            callbacks = self.message_callbacks.copy()

        for callback in callbacks:
            try:
                callback(message_data, sender_ip)
            except Exception as e:
                print(f"❌ Callback error: {e}")
