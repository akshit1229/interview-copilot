"""
Generates a self-signed SSL certificate for local HTTPS.
Run once: python generate_cert.py
Creates: cert.pem, key.pem
"""

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime
import ipaddress
import socket
import os

def get_local_ips():
    """Get all local IP addresses of this machine."""
    ips = ["127.0.0.1"]
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            addr = info[4][0]
            if ":" not in addr:  # IPv4 only
                if addr not in ips:
                    ips.append(addr)
    except Exception:
        pass
    return ips


def generate_cert(cert_path="cert.pem", key_path="key.pem"):
    local_ips = get_local_ips()
    print(f"Generating self-signed cert for IPs: {local_ips}")

    # Generate private key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Build certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ParakeetAI Local"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    # SAN: include all local IPs and localhost
    san_entries = [x509.DNSName("localhost")]
    for ip in local_ips:
        try:
            san_entries.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
        except Exception:
            pass

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=825))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    # Write cert
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # Write key
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))

    print(f"Created: {cert_path}, {key_path}")
    print()
    print("Your local IP addresses (use one on your phone):")
    for ip in local_ips:
        if ip != "127.0.0.1":
            print(f"  https://{ip}:8443")
    print()
    print("NOTE: Your phone browser will show a security warning.")
    print("Tap 'Advanced' -> 'Proceed anyway' to accept the self-signed cert.")


if __name__ == "__main__":
    generate_cert()
