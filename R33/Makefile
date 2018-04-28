all: check

# Install all packages required for MAAS image builder development & operation
# on the system. This may prompt for a password.
install-dependencies:
	sudo DEBIAN_FRONTEND=noninteractive apt-get -y \
		--no-install-recommends install $(shell sort -u \
			$(addprefix required-packages/,base build dev))

check:
	@tox

package_export: VER = $(shell dpkg-parsechangelog -ldebian/changelog | sed -rne 's,^Version: ([^-]+).*,\1,p')
package_export: TARBALL = maas-image-builder_$(VER).orig.tar.gz
package_export:
	@$(RM) -f build/$(TARBALL)
	@mkdir -p build
	@bzr export --root=maas-image-builder-$(VER).orig build/$(TARBALL) $(CURDIR)

package: package_export
	bzr bd --result-dir=build --build-dir=build

source_package: package_export
	bzr bd --result-dir=build --build-dir=build -S

.PHONY: check install-dependencies
