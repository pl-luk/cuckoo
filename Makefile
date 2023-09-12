DESTDIR=/

install:
	mkdir -p $(DESTDIR)/usr/bin
	mkdir -p $(DESTDIR)/etc
	cp ./cuckoo $(DESTDIR)/usr/bin/cuckoo
	cp ./cuckoo.ini $(DESTDIR)/etc/cuckoo.ini

uninstall:

	rm $(DESTDIR)/usr/bin/cuckoo
	rm $(DESTDIR)/etc/cuckoo.ini
