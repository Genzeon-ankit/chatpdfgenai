from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import logging 
import os

def save_key_to_file(key, filename="encryption_key.key"):
    with open(filename, "wb") as key_file:
        key_file.write(key)

def load_key_from_file(filename="encryption_key.key"):
    with open(filename, "rb") as key_file:
        return key_file.read()

# Generate key only if it doesn't exist
if not os.path.exists("encryption_key.key"):
    key = get_random_bytes(32)
    save_key_to_file(key)
else:
    key = load_key_from_file()

def encrypt_file_aes(file_path, key):
    cipher = AES.new(key, AES.MODE_GCM)
    with open(file_path, 'rb') as file:
        plaintext = file.read()
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    with open(file_path + '.enc', 'wb') as file_enc:
        for x in (cipher.nonce, tag, ciphertext):
            file_enc.write(x)

def decrypt_file_aes(encrypted_file_path, key):
    with open(encrypted_file_path, 'rb') as file_enc:
        nonce, tag, ciphertext = [file_enc.read(x) for x in (16, 16, -1)]
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        try:
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext
        except ValueError:
            logging.error("An error occurred during decryption: MAC check failed")
            return None
