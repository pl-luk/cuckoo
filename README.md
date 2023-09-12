# cuckoo
A tool to make managing linux installations on chromebooks easier.

## Functionality
### Key generation
If you want to resign your firmware and install linux on your chrome os device you will require custom keys (except you want to use developer mode). By specifying the keys you want to generate in the `/etc/cuckoo.ini` file cuckoo can automatically output the desired keys. This is achieved by executing `cuckoo -g` (or `sudo cuckoo -g` if the key directory is only writable by the root user). The default configuration file includes a key layout as described in https://github.com/pl-luk/linuxbook which is sufficient for resigning the firmware and running a custom kernel in secure mode.

### Partition layout generation
When installing a linux distribution to a chromebook the most tedious job is to create the disk layout with `cgpt` by configuring the layout in `/etc/cuckoo.ini` one can generate a `fdisk` layout file by executing `cuckoo -p DEVICE`. The `DEVICE` parameter has to be specified so that the partition sizes can be adjusted correctly.

### Kernel generation
With the `cuckoo -k` command kernel partition files can easily be created. To do that the kernel files need to be specified in `/etc/cuckoo.ini`. If an `update_path` was specified in `/etc/cuckoo.ini` the kernel partitions can easily be updated by using `cuckoo -u` after a kernel update.

## Configuration
A guide to configure cuckoo via the configuration file is found in the configuration file typically located at `/etc/cuckoo.ini`
