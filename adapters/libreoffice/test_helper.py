#!/usr/bin/env python3
import socket
import json

def check_helper_status():
    """Test connection to the helper script"""
    try:
        print("Testing connection to helper on localhost:8765...")
        
        # Create socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10)
        
        # Connect
        client_socket.connect(('localhost', 8765))
        print("Connected successfully!")
        
        # Send ping command
        command = {"action": "ping"}
        request_data = json.dumps(command).encode('utf-8')
        client_socket.send(request_data)
        print(f"Sent command: {command}")
        
        # Receive response
        response_data = client_socket.recv(16384).decode('utf-8')
        print(f"Received response: {response_data}")
        
        # Parse response
        response = json.loads(response_data)
        if response.get("status") == "success":
            print("Helper is working correctly!")
            return True
        else:
            print(f"Helper returned error: {response}")
            return False
            
    except ConnectionRefusedError:
        print("Connection refused - helper script is not running or not listening on port 8765")
        return False
    except socket.timeout:
        print("Connection timed out")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        try:
            client_socket.close()
        except:
            pass

if __name__ == "__main__":
    test_helper()