import requests

def check_deployment_status(url: str) -> bool:
    """
    Returns True if the deployed app is reachable (status code 200).
    """
    try:
        resp = requests.get(url, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False