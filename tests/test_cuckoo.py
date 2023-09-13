import unittest
import importlib.machinery, importlib.util

from cryptography import x509
import io

# Complicated import with importlib because cuckoo has no .py extension and is in parent directory
loader = importlib.machinery.SourceFileLoader("cuckoo", "../cuckoo")
spec = importlib.util.spec_from_loader(loader.name, loader)
cuckoo = importlib.util.module_from_spec(spec)
loader.exec_module(cuckoo)

TEST_PRIMITIVES = [
        "./test_keys/temp/root_key",
        "./test_keys/temp/recovery_key",
        "./test_keys/temp/recovery_kernel_data_key",
        "./test_keys/temp/kernel_subkey",
        "./test_keys/temp/kernel_data_key",
        "./test_keys/temp/firmware_data_key",
        "./test_keys/temp/dev_firmware_data_key"
    ]

class TestCuckoo(unittest.TestCase):

    def test_dumpRSAPublicKey(self):

        for prim in TEST_PRIMITIVES:

            # Load the cert, throw it at dumpRSAPublicKey and
            # check if output matches the corresponding keyb
            with open(f"{prim}.crt", "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())

            with open(f"{prim}.keyb", "rb") as f:
                keyb = f.read()
    
            # We also need a BytesIO object because it's stupid to create another file
            keyb_test = io.BytesIO()
            cuckoo.dumpRSAPublicKey(cert.public_key(), keyb_test)

            self.assertEqual(keyb_test.getvalue(), keyb, f"Preprocessed RSA key {prim} does not match the generated one!")

            
