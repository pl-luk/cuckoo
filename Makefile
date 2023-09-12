
install:
	cp ./cuckoo /usr/bin/cuckoo
	cp ./cuckoo.ini /etc/cuckoo.ini

uninstall:

	rm /usr/bin/cuckoo
	rm /etc/cuckoo.ini
