#!/usr/bin/python3

import argparse
import os
import shutil
import sys
import datetime
import subprocess

from configobj import ConfigObj

# Config file path
KERNELTOOL_CONFIG = './cuckoo.ini'

# Directory where we want to package kernels
KERNEL_PACKAGE_DIR = '/tmp'

# Location to generate the kernel files

# Algorithm id table
alg_ids = {'RSA1024 SHA1': 0,
           'RSA1024 SHA256': 1,
           'RSA1024 SHA512': 2,
           'RSA2048 SHA1': 3,
           'RSA2048 SHA256': 4,
           'RSA2048 SHA512': 5,
           'RSA4096 SHA1': 6,
           'RSA4096 SHA256': 7,
           'RSA4096 SHA512': 8,
           'RSA8192 SHA1': 9,
           'RSA8192 SHA256': 10,
           'RSA8192 SHA512': 11}

# Function to generate keys
def gen_keys(key_dir, keys, keyblocks):

    # make keydir if not existing
    if not os.path.exists(key_dir):
        os.mkdir(key_dir)
        
    os.chdir(key_dir)

    # make dir for key intermediates
    if not os.path.exists('temp'):
        os.mkdir('temp')

    os.chdir('temp')

    for key in keys:


        # Generate RSA keypair
        print(f">>> Generating RSA keypair: {key}.pem")
        subprocess.run(["openssl", "genrsa", "-F4", "-out", f"{key}.pem", f"{keys[key]['RSA_length']}"], check = True)

        # Generate cert
        print(f">>> Generating certificate: {key}.crt")
        subprocess.run(["openssl", "req", "-batch", "-new", "-x509", "-key", f"{key}.pem", "-out", f"{key}.crt"], check = True)

        # Generate pre-processed RSA public_key
        with open(f"{key}.keyb", "wb") as f:
            subprocess.run(["dumpRSAPublicKey", "-cert", f"{key}.crt"], stdout = f, check = True)

        # "calculate" algorithm id for key packing
        alg = alg_ids[f"RSA{keys[key]['RSA_length']} {keys[key]['hash_alg']}"]

        # generate public key
        print(f">>> Packing public key: {key}.vbpubk")
        subprocess.run(["futility", "vbutil_key", "--pack", f"{key}.vbpubk", "--key", f"{key}.keyb", "--version", "1", "--algorithm", f"{alg}"], check = True)

        # generate private key
        print(f">>> Packing private key: {key}.vbprivk")
        subprocess.run(["futility", "vbutil_key", "--pack", f"{key}.vbprivk", "--key", f"{key}.pem", "--algorithm", f"{alg}"], stderr = subprocess.DEVNULL, check = True)

        # move all pubk and privk files to the keys dir
        shutil.move(f"{key}.vbpubk", '../')
        shutil.move(f"{key}.vbprivk", '../')

    os.chdir('../')

    # Generate keyblocks
    for keyblock in keyblocks:
        print(f">>> Generating keyblock: {keyblock}.keyblock")
        subprocess.run(["futility", "vbutil_keyblock", "--pack", f"{keyblock}.keyblock", "--flags", f"{keyblocks[keyblock]['flags']}", "--datapubkey",
                        f"{keyblocks[keyblock]['datapubkey']}.vbpubk", "--signprivate", f"{keyblocks[keyblock]['signprivate']}.vbprivk"], check = True)

    def gen_kernel_files(key_dir, kernels):
        pass



if __name__ == '__main__':

    # Handle configuration
    config = ConfigObj(KERNELTOOL_CONFIG)

    if not os.path.exists(KERNELTOOL_CONFIG):
        
        # Create default config
        pass

    # Handle argparse
    parser = argparse.ArgumentParser(prog = "cuckoo",
                                     description = "A tool to make managing linux installations on chromebooks easier")

    parser.add_argument('-g', '--generate-keys', action = 'store_true', help = f'Generate keys based on {KERNELTOOL_CONFIG}')

    args = parser.parse_args()

    if args.generate_keys:
        
        gen_keys(config['VERIFIED_BOOT']['key_dir'], 
                 config['VERIFIED_BOOT']['KEYS'],
                 config['VERIFIED_BOOT']['KEYBLOCKS'])

