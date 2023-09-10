#!/usr/bin/python3

import argparse
import os
import shutil
import sys
import datetime
import subprocess
import math

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

# relevant guids
guids = {'kernel': 'FE3A2A5D-4F32-41A7-B725-ACCC3285A309',
         'rootfs': '3CB8E202-3B7E-47DD-8A3C-7FF2A13CFCEC',
         'firmware': 'CAB6E88E-ABF3-4102-A07A-D4BB9BE3C1D3',
         'future': '2E0A753D-9E48-43B0-8337-B15192CB1B5E',
         'minios': '09845860-705F-4BB5-B16C-8A8A099CAF52',
         'hibernate': '3F0F8318-F146-4E6B-8222-C28C8F02E0D5',
         'basicdata': 'EBD0A0A2-B9E5-4433-87C0-68B6B72699C7',
         'dm-crypt': '7FFEC5C9-2D00-49B7-8941-3EA10A5586B7',
         'luks': 'CA7D7CCB-63ED-4C53-861C-1742536059CC',
         'efi': 'C12A7328-F81F-11D2-BA4B-00A0C93EC93B'}


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

def gen_kernel_files(key_dir, parts):

    for partition in parts:

        p_type = parts[partition]["type"]

        # Process only kernel partitions
        if p_type == 'kernel' or p_type == guids['kernel']:
            
            print(f">>> Generating kernel file for {partition}...")
            
            p_size = int(parts[partition]["size"])
            k_bZ = parts[partition]["bzImage"]
            k_conf = parts[partition]["config"]
            k_signp = parts[partition]["signprivate"]
            k_keybl = parts[partition]["keyblock"]

            # Make sure bzImage exists
            k_bZ = os.path.abspath(k_bZ)

            if os.path.exists(k_bZ):
                print(f">>> Found bZImage at {k_bZ} with config: {k_conf}")
            else:
                print(f">>> Could not find bZImage at {k_bZ}. Exiting...")
                return

            print(f">>> Scanning keys in {key_dir}...")
            
            # Make sure keys are there
            k_signp = os.path.abspath(os.path.join(key_dir, k_signp))
            k_signp += ".vbprivk"
            k_keybl = os.path.abspath(os.path.join(key_dir, k_keybl))
            k_keybl += ".keyblock"

            if os.path.exists(k_signp):
                print(f">>> Found private key at {k_signp}")
            else:
                print(f">>> Could not find private key at {k_signp}. Exiting...")
                return

            if os.path.exists(k_keybl):
                print(f">>> Found keyblock at {k_keybl}")
            else:
                print(f">>> Could not find keyblock at {k_keybl}. Exiting...")
                return

            olddir = os.getcwd()
            os.chdir(KERNEL_PACKAGE_DIR)

            print(f">>> Generating bootloader stub...", end='')
            out = subprocess.run(["dd", "if=/dev/zero", "of=bootloader.bin", "bs=1K", "count=1"], capture_output = True)
            
            if out.returncode == 0:
                print(" done.")
            else:
                print(" error:")
                print(f">>> {out.stderr.decode('utf-8')}")
                print(">>> Exiting...")
                return

            with open("config.txt", "w") as f:
                f.write(k_conf)

            print(f">>> Generating kernel image...", end='')

            # for some reason subprocess does not work here?
            os.system(f"futility vbutil_kernel --pack {partition} --keyblock {k_keybl} --signprivate {k_signp} --version 1 --vmlinuz {k_bZ} --bootloader bootloader.bin --config config.txt")

            print(f">>> Truncating {partition} to {p_size * 512} bytes")
    
            # truncate to size
            subprocess.run(["truncate", "-s", str(p_size * 512), partition])

            print(f">>> Copying {partition} to {olddir}")

            shutil.move(os.path.abspath(partition), os.path.join(olddir, partition))

def update_kernel_files(key_dir, parts):

    os.chdir(KERNEL_PACKAGE_DIR)
    gen_kernel_files(key_dir, parts)

    for partition in parts:

        p_type = parts[partition]["type"]

        # Process only kernel partitions
        if p_type == 'kernel' or p_type == guids['kernel']:

            k_update = parts[partition]["update_path"]

            print(f">>> Writing {partition} to {k_update}...")

            out = subprocess.run(["dd", f"if={partition}", f"of={k_update}"], capture_output = True)
            
            if out.returncode == 0:
                print(" done.")
            else:
                print(" error:")
                print(f">>> {out.stderr.decode('utf-8')}")
                print(">>> Exiting...")
                return
    

def create_device_layout(device, parts):

    # Get size of device
    (ex, out) = subprocess.getstatusoutput(f"blockdev --getsz {device[0]}") 

    # If exit code is not zero we have to display the error message and exit
    if ex:
        print(f">>> Error on finding size of device {device[0]}:")
        print(out)
        return

    # If out can be converted to int we can continue, else print out and exit
    sz = 0
    try:
        sz = int(out)
    except ValueError:
        print(f">>> Error on finding size of device {device[0]}:")
        print(out)
        return

    print("label: gpt\nunit: sectors\nsector-size: 512")

    # starting position and end position
    # => we need to leave space for the partition headers in front and at the end
    # also we need to align every partition to 2048 sectors (1Mib) => start is at 2048 sectors
    # end is at size - 34 because the end of the gpt is always 34 sectors long
    start = 2048 
    end = sz - 34

    # then we create a one block large state partition wich is needed for chromebooks to boot from the device
    print(f"start={start}, size=2048, type={guids['basicdata']}, name=STATE")

    start = start + 2048 

    for partition in parts:

        p_type = parts[partition]["type"]
        p_size = int(parts[partition]["size"])

        # if we have a shorthand for a guid convert that to the long format
        # else: use whatever input we got and pray that sfdisk understands it
        if p_type in guids:
            p_type = guids[p_type]

        # partition sizes should not be zero
        if p_size == 0:
            print(f">>> Error: size of partition {partition} should not equal 0")
            return

        # If size is negative just use the remaining space
        if p_size < 0:
            p_size = end - start

        # Also we need to check if the partition is too large
        if start + p_size > end:
            print(f">>> Error: No space left on device")
            return

        print(f"start={start}, size={p_size}, type={p_type}, name={partition}", end='')

        # Handle kernel partition attributes
        if p_type == guids["kernel"]:
            priority = int(parts[partition]["priority"])
            successfull = bool(int(parts[partition]["successfull"]))
            tries = int(parts[partition]["tries"])

            # Make sure that priority and tries are between 0 and 15
            if priority < 0 and priority > 15:
                print("")
                print(f">>> Error: priority flag for partition {partition} must be between 0 and 15")
                return

            if tries < 0 and tries > 15:
                print("")
                print(f">>> Error: tries flag for partition {partition} must be between 0 and 15")
                return
            
            # If priority is 0, tries is 0 and successfull is 0 we don't need to append anything
            if priority != 0 or tries != 0 or successfull:

                s = ", attrs=\"GUID:"

                # we need to create a bit mask as described in https://chromium.googlesource.com/chromiumos/docs/+/head/disk_format.md#selecting-the-kernel
                
                # before creating the bitmask we must change the endianess
                # of both priority and tries (required by gpt)

                # since have to set 9 bits shift priority by 5
                bit_mask = int('{:04b}'.format(priority)[::-1], 2) << 5

                # the next 4 bits are the tries bits => shift tries by 1 and or the result to the bit_mask
                bit_mask |= int('{:04b}'.format(tries)[::-1], 2) << 1

                # finally OR the successfull flag
                bit_mask |= successfull

                # loop from 48 to 56 and add correct bit numbers to s
                j = 0b100000000 
                for i in range(48, 57):

                    if bit_mask & j:
                        s += f"{i},"

                    j >>= 1

                # Remove remaining , and print resulting string
                s = s[:-1]

                print(f"{s}\"", end='')
        print("")

        # update start for next partition
        start = start + p_size
    
        # check if start is 1Mib aligned
        if start % 2048 != 0:

            # new start is at the next multiple of 2048
            # 1. integer divide start by 2048 to get the quantity of fully occupied 2048 chunks
            # 2. add 1 so that we get the next entirely unoccupied chung
            # 3. multiply with 2048 to get the result in sectors
            start = ((start // 2048) + 1) * 2048
        

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
    parser.add_argument('-p', '--device-layout', metavar = 'DEVICE', nargs = 1, action = 'store', help = f"Generate layout file for formatting the specified device (i.e. /dev/sda) based on {KERNELTOOL_CONFIG}")
    parser.add_argument('-k', '--kernel', action = 'store_true', help = f'Generate the kernel files specified in {KERNELTOOL_CONFIG}')
    parser.add_argument('-u', '--update-kernels', action = 'store_true', help = f'(Re)Generate kernel files and write to partition specified in update_path tag')

    args = parser.parse_args()

    if args.generate_keys:
        
        gen_keys(os.path.abspath(config['VERIFIED_BOOT']['key_dir']), 
                 config['VERIFIED_BOOT']['KEYS'],
                 config['VERIFIED_BOOT']['KEYBLOCKS'])

    elif args.device_layout:

        create_device_layout(args.device_layout,
                             config['PARTITIONS'])

    elif args.kernel:

        gen_kernel_files(os.path.abspath(config['VERIFIED_BOOT']['key_dir']), config['PARTITIONS'])

    elif args.update_kernels:

        update_kernel_files(os.path.abspath(config['VERIFIED_BOOT']['key_dir']), config['PARTITIONS'])
