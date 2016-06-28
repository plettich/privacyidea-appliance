info:
	@echo "make clean        - remove all automatically created files"
	@echo "make epydoc       - create the API documentation"
	@echo "make doc-man      - create the documentation as man-page"
	@echo "make doc-html     - create the documentation as html"
	@echo "make pypi         - upload package to pypi"
	@echo "make debianzie    - prepare the debian build environment in DEBUILD"
	@echo "make builddeb     - build .deb file locally on ubuntu 14.04LTS!"
	@echo "make venvdeb      - build .deb file, that contains the whole setup in a virtualenv."
	@echo "make translate    - translate WebUI"
	@echo "                    This is to be used with debian Wheezy"
	@echo "make ppa-dev      - upload to launchpad development repo"
	
#VERSION=1.3~dev5
VERSION=2.0~dev4
SERIES="trusty precise vivid"
LOCAL_SERIES=`lsb_release -a | grep Codename | cut -f2`
SRCDIRS=authappliance
SRCFILES=setup.py Makefile Changelog LICENSE requirements.txt

clean:
	find . -name \*.pyc -exec rm {} \;
	rm -fr build/
	rm -fr dist/
	rm -fr DEBUILD
	rm -fr RHBUILD
	rm -fr cover
	rm -f .coverage

debianize:
	make clean
	mkdir -p DEBUILD/pi-appliance.org/debian
	cp -r ${SRCDIRS} ${SRCFILES} DEBUILD/pi-appliance.org || true
	# We need to touch this, so that our config files 
	# are written to /etc
	touch DEBUILD/pi-appliance.org/PRIVACYIDEA_PACKAGE
	cp LICENSE DEBUILD/pi-appliance.org/debian/copyright
	(cd DEBUILD; tar -zcf pi-appliance_${VERSION}.orig.tar.gz --exclude=pi-appliance.org/debian pi-appliance.org)


builddeb:
	make debianize
	################## Renew the changelog
	cp -r debian/* DEBUILD/pi-appliance.org/debian/
	sed -e s/"trusty) trusty; urgency"/"$(LOCAL_SERIES)) $(LOCAL_SERIES); urgency"/g debian/changelog > DEBUILD/pi-appliance.org/debian/changelog
	################# Build
	(cd DEBUILD/pi-appliance.org; debuild --no-lintian)

ppa:
	cp debian/changelog DEBUILD/pi-appliance.org/debian/
	sed -e s/"trusty) trusty; urgency"/"$(series)) $(series); urgency"/g debian/changelog > DEBUILD/pi-appliance.org/debian/changelog
	################# Build
	(cd DEBUILD/pi-appliance.org; debuild -sa -S)
	 ################ Upload to launchpad:
	dput ppa:privacyidea/appliance DEBUILD/pi-appliance_${VERSION}*_source.changes

ppa-dev:
	################### Check for the series
	@echo "You need to specify a parameter series like $(SERIES)"
	echo $(SERIES) | grep $(series)
	################## Renew the changelog
	cp debian/changelog DEBUILD/pi-appliance.org/debian/
	sed -e s/"trusty) trusty; urgency"/"$(series)) $(series); urgency"/g debian/changelog > DEBUILD/pi-appliance.org/debian/changelog
	################# Build
	(cd DEBUILD/pi-appliance.org; debuild -sa -S)
	################ Upload to launchpad:
	dput ppa:privacyidea/appliance-dev DEBUILD/pi-appliance_${VERSION}*_source.changes
