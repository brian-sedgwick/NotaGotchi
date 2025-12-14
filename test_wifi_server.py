#!/usr/bin/env python3
"""
Wi-Fi Server Test for NotaGotchi - TCP Server with mDNS

Tests TCP server functionality with mDNS service advertisement.
This device will:
1. Advertise as a NotaGotchi device via mDNS
2. Accept incoming TCP connections
3. Receive messages from clients

Usage:
    python3 test_wifi_server.py [device_name] [port]

Example:
    python3 test_wifi_server.py NotaGotchi_TestA 5555
"""

import socket
import threading
import json
import time
import sys
from typing import Dict, Any, List
import test_wifi_config as config

try:
    from zeroconf import Zeroconf, ServiceInfo
except ImportError:
    print("ERROR: zeroconf library not installed")
    print("Install with: pip3 install zeroconf")
    sys.exit(1)


class NotaGotchiServer:
    """TCP Server with mDNS advertisement for NotaGotchi"""

    def __init__(self, device_name: str, port: int = config.DEFAULT_PORT):
        self.device_name = device_name
        self.port = port
        self.running = False
        self.received_messages: List[Dict[str, Any]] = []

        # Device info
        self.device_info = {
            "device_name": device_name,
            "pet_name": "TestPet",
            "age_days": 1,
            "evolution_stage": 0,
            "online": True,
            "timestamp": time.time()
        }

        # Network components
        self.server_socket = None
        self.zeroconf = None
        self.service_info = None

    def start(self):
        """Start the TCP server and mDNS advertisement"""
        print(f"\n{'='*60}")
        print(f"Starting NotaGotchi Wi-Fi Server")
        print(f"{'='*60}")
        print(f"Device Name: {self.device_name}")
        print(f"Port: {self.port}")
        print(f"{'='*60}\n")

        try:
            # Create TCP server socket
            print("✅ Creating TCP server...")
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('', self.port))
            self.server_socket.listen(5)

            # Get local IP address
            local_ip = self._get_local_ip()
            print(f"   Listening on {local_ip}:{self.port}")

            # Setup mDNS advertisement
            print("\n✅ Setting up mDNS advertisement...")
            self.zeroconf = Zeroconf()

            # Create service info
            service_name = f"{self.device_name}.{config.SERVICE_TYPE}"

            # Prepare properties
            properties = {
                k.encode('utf-8'): v.encode('utf-8') if isinstance(v, str) else str(v).encode('utf-8')
                for k, v in config.SERVICE_PROPERTIES.items()
            }

            self.service_info = ServiceInfo(
                type_=config.SERVICE_TYPE,
                name=service_name,
                port=self.port,
                properties=properties,
                server=f"{self.device_name}.local."
            )

            # Register service
            print(f"   Advertising as: {service_name}")
            self.zeroconf.register_service(self.service_info)

            print(f"\n{'='*60}")
            print(f"✅ SERVER READY!")
            print(f"{'='*60}")
            print(f"💡 Other devices can now discover '{self.device_name}'")
            print(f"💡 Run test_wifi_discovery.py on another device to find this server")
            print(f"💡 Run test_wifi_client.py on another device to send messages")
            print(f"\nPress Ctrl+C to stop")
            print(f"{'='*60}\n")

            self.running = True

            # Accept connections
            while self.running:
                try:
                    # Set timeout so we can check self.running periodically
                    self.server_socket.settimeout(1.0)
                    client_socket, client_address = self.server_socket.accept()

                    print(f"\n🔌 New connection from {client_address[0]}:{client_address[1]}")

                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.timeout:
                    # Normal timeout, just check if we should continue
                    continue
                except OSError:
                    # Socket closed
                    break

        except KeyboardInterrupt:
            print("\n\nServer interrupted by user")
        except Exception as e:
            print(f"\n❌ Server error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()

    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """Handle a client connection"""
        try:
            # Receive data
            data = b""
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                data += chunk
                if len(data) >= config.MAX_MESSAGE_SIZE:
                    break

            if data:
                # Parse message
                message_str = data.decode(config.MESSAGE_ENCODING)
                message_data = json.loads(message_str)

                print(f"\n📨 Received message:")
                print(f"  From: {message_data.get('from_device_name', 'Unknown')}")
                print(f"  Pet: {message_data.get('from_pet_name', 'Unknown')}")
                print(f"  Content: {message_data.get('content', '')}")
                print(f"  Type: {message_data.get('content_type', 'text')}")
                print(f"  Timestamp: {time.strftime('%H:%M:%S', time.localtime(message_data.get('timestamp', 0)))}")

                # Store message
                self.received_messages.append({
                    "message": message_data,
                    "received_at": time.time(),
                    "from_address": client_address[0]
                })

                print(f"  Total messages received: {len(self.received_messages)}\n")

                # Send acknowledgment
                response = {
                    "status": "received",
                    "timestamp": time.time()
                }
                client_socket.sendall(json.dumps(response).encode(config.MESSAGE_ENCODING))

        except json.JSONDecodeError as e:
            print(f"❌ Error decoding message JSON: {e}")
        except Exception as e:
            print(f"❌ Error handling client: {e}")
        finally:
            client_socket.close()
            print(f"🔌 Connection closed from {client_address[0]}:{client_address[1]}")

    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            # Create a socket to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"

    def stop(self):
        """Stop the server and cleanup"""
        print("\n\nStopping server...")
        self.running = False

        try:
            # Unregister mDNS service
            if self.zeroconf and self.service_info:
                print("  - Unregistering mDNS service...")
                self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()

            # Close server socket
            if self.server_socket:
                print("  - Closing server socket...")
                self.server_socket.close()

            print("✅ Server stopped cleanly")

            if self.received_messages:
                print(f"\nServer Statistics:")
                print(f"  Device Name: {self.device_name}")
                print(f"  Messages Received: {len(self.received_messages)}")

        except Exception as e:
            print(f"⚠️  Error during cleanup: {e}")


def main():
    """Main entry point"""
    print(f"\n{'='*60}")
    print(f"NotaGotchi Wi-Fi Server Test")
    print(f"{'='*60}\n")

    # Get device name from command line or use default
    if len(sys.argv) > 1:
        device_name = sys.argv[1]
    else:
        device_name = config.TEST_DEVICE_A_NAME

    # Get port from command line or use default
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(f"❌ Invalid port: {sys.argv[2]}")
            print(f"Using default port: {config.DEFAULT_PORT}")
            port = config.DEFAULT_PORT
    else:
        port = config.DEFAULT_PORT

    # Create and start server
    server = NotaGotchiServer(device_name, port)
    server.start()


if __name__ == "__main__":
    main()
