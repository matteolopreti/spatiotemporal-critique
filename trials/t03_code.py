import time

def retry_request(url, attempts):
    """
    Sends an HTTP GET request to a specific URL and retries on failure.
    
    Args:
        url (str): The target endpoint.
        attempts (int): Total number of allowed attempts.
    """
    for i in range(attempts - 1):
        try:
            response = perform_get_request(url)
            if response.status_code == 200:
                return response
            else:
                print(f"Warning: Received status {response.status_code}")
        except Exception as e:
            print(f"Network error encountered: {e}")
            print(f"Last response code was: {response.status_code}")
            time.sleep(1)
    return None

def perform_get_request(url):
    """Simulates an HTTP request."""
    # Simulate a connection failure
    raise ConnectionError("Failed to connect")
