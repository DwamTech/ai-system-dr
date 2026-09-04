import os
import sys

def print_status(msg, status="INFO"):
    print(f"[{status}] {msg}")

print_status("Starting diagnostics...", "INFO")

# 1. Check Imports
print_status("Checking imports...", "INFO")
try:
    import PyPDF2
    print_status("PyPDF2 available", "OK")
except ImportError as e:
    print_status(f"PyPDF2 missing: {e}", "ERROR")

try:
    from langchain_community.vectorstores import OpenSearchVectorSearch
    print_status("langchain OpenSearch available", "OK")
except ImportError as e:
    print_status(f"langchain OpenSearch missing: {e}", "ERROR")

# 2. Check OpenSearch Connection
print_status("Checking OpenSearch connection...", "INFO")
try:
    from opensearchpy import OpenSearch
    host = 'localhost'
    port = 9200
    auth = ('admin', 'admin') # Default for many setups, might need adjustment based on user's setup
    
    # Try http first
    try:
        # Check standard port and docker-mapped port
        for check_port in [9200, 9201]:
            try:
                print_status(f"Attempting to connect to OpenSearch on port {check_port}...", "INFO")
                client = OpenSearch(
                    hosts=[{'host': host, 'port': check_port}],
                    http_compress=True,
                    http_auth=auth,
                    use_ssl=False,
                    verify_certs=False,
                    ssl_assert_hostname=False,
                    ssl_show_warn=False,
                    timeout=5
                )
                info = client.info()
                print_status(f"OpenSearch Connection Successful on port {check_port}: {info['version']['number']}", "OK")
                
                # Check indices
                indices = client.cat.indices(format="json")
                print_status(f"Found {len(indices)} indices", "INFO")
                for idx in indices:
                    print_status(f"Index: {idx['index']} - Docs: {idx['docs.count']}", "INFO")
                break
            except Exception as e:
                print_status(f"Connection to port {check_port} failed: {e}", "WARNING")
            
    except Exception as e:
        print_status(f"OpenSearch Connection Critical Failure: {e}", "ERROR")

except ImportError:
    print_status("opensearchpy not installed, cannot test direct connection easily", "WARNING")

# 3. Check Ollama
print_status("Checking Ollama connection...", "INFO")
import requests
for check_port in [11434, 11435]:
    try:
        print_status(f"Attempting to connect to Ollama on port {check_port}...", "INFO")
        response = requests.get(f"http://localhost:{check_port}")
        if response.status_code == 200:
            print_status(f"Ollama is running on port {check_port}", "OK")
            break
        else:
            print_status(f"Ollama on port {check_port} returned status {response.status_code}", "WARNING")
    except Exception as e:
        print_status(f"Ollama connection to port {check_port} failed: {e}", "WARNING")

print_status("Diagnostics complete.", "INFO")
