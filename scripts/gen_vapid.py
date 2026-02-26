
import base64
import os
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

def to_base64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

# Generate EC P-256 Key Pair
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# Serialize Private Key (Integer)
private_val = private_key.private_numbers().private_value
private_bytes = private_val.to_bytes(32, byteorder='big')

# Serialize Public Key (Uncompressed Point)
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

print("VAPID Keys Generated:")
print(f"Private Key: {to_base64url(private_bytes)}")
print(f"Public Key:  {to_base64url(public_bytes)}")
