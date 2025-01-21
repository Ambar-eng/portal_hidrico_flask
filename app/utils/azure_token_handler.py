import os
from azure.identity import ClientSecretCredential

def get_azure_token():
    client_id = os.getenv("CLIENT_ID")
    tenant_id = os.getenv("TENANT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    credential = ClientSecretCredential(
        client_id=client_id,
        client_secret=client_secret,
        tenant_id=tenant_id
    )
    
    token = credential.get_token("https://management.azure.com/.default")
    return token.token