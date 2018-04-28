# vi: ts=4 expandtab
# Upstream Author:
#
#     Canonical Ltd.
#
# Copyright:
#
#     (c) 2014-2017 Canonical Ltd.
#
# Licence:
#
# If you have an executed agreement with a Canonical group company which
# includes a licence to this software, your use of this software is governed
# by that agreement.  Otherwise, the following applies:
#
# Canonical Ltd. hereby grants to you a world-wide, non-exclusive,
# non-transferable, revocable, perpetual (unless revoked) licence, to (i) use
# this software in connection with Canonical's MAAS software to install Windows
# in non-production environments and (ii) to make a reasonable number of copies
# of this software for backup and installation purposes.  You may not: use,
# copy, modify, disassemble, decompile, reverse engineer, or distribute the
# software except as expressly permitted in this licence; permit access to the
# software to any third party other than those acting on your behalf; or use
# this software in connection with a production environment.
#
# CANONICAL LTD. MAKES THIS SOFTWARE AVAILABLE "AS-IS".  CANONICAL  LTD. MAKES
# NO REPRESENTATIONS OR WARRANTIES OF ANY KIND, WHETHER ORAL OR WRITTEN,
# WHETHER EXPRESS, IMPLIED, OR ARISING BY STATUTE, CUSTOM, COURSE OF DEALING
# OR TRADE USAGE, WITH RESPECT TO THIS SOFTWARE.  CANONICAL LTD. SPECIFICALLY
# DISCLAIMS ANY AND ALL IMPLIED WARRANTIES OR CONDITIONS OF TITLE, SATISFACTORY
# QUALITY, MERCHANTABILITY, SATISFACTORINESS, FITNESS FOR A PARTICULAR PURPOSE
# AND NON-INFRINGEMENT.
#
# IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW OR AGREED TO IN WRITING WILL
# CANONICAL LTD. OR ANY OF ITS AFFILIATES, BE LIABLE TO YOU FOR DAMAGES,
# INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING
# OUT OF THE USE OR INABILITY TO USE THIS SOFTWARE (INCLUDING BUT NOT LIMITED
# TO LOSS OF DATA OR DATA BEING RENDERED INACCURATE OR LOSSES SUSTAINED BY YOU
# OR THIRD PARTIES OR A FAILURE OF THE PROGRAM TO OPERATE WITH ANY OTHER
# PROGRAMS), EVEN IF SUCH HOLDER OR OTHER PARTY HAS BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGES.

"""Builder for CentOS."""

import os
import shutil

from mib.builders import BuildError, VirtInstallBuilder


class CentOSBuilder(VirtInstallBuilder):
    """Builds the CentOS image for both amd64 and i386. Uses virt-install
    to perform this installation process."""

    name = "centos"
    arches = ["i386", "amd64"]
    os_type = "linux"
    os_variant = "rhel5"
    disk_size = 5
    nic_model = "virtio"
    install_location = ""

    def full_name(self, params):
        return 'centos%s-%s' % (params.edition, params.arch)

    def populate_parser(self, parser):  # pylint: disable=no-self-use
        """Add parser options."""
        parser.add_argument(
            '--edition', default='7',
            help="CentOS edition to generate. (Default: 7)")

    def validate_params(self, params):  # pylint: disable=no-self-use
        """Validates the command line parameters."""
        if params.edition not in ['6', '7']:
            raise BuildError(
                "Unknown CentOS edition: %s." % params.edition)
        if params.edition == '7' and params.arch == 'i386':
            raise BuildError(
                "Cannot generate CentOS 7 for i386, as only amd64 is "
                "supported.")

    def modify_mount(self, mount_path):
        """Install the curtin directory into mount point."""
        path = None
        if self.edition == '6':
            path = self.get_contrib_path('centos6/curtin')
        elif self.edition == '7':
            path = self.get_contrib_path('centos7/curtin')
        if not os.path.exists(path):
            return
        opt_path = os.path.join(mount_path, 'curtin')
        shutil.copytree(path, opt_path)

    def build_image(self, params):
        self.validate_params(params)
        self.edition = (  # pylint: disable=attribute-defined-outside-init
            params.edition)
        if self.edition == '6':
            arch = params.arch
            if arch == 'i386':
                self.install_location = (
                    "http://mirror.centos.org/centos/6/os/i386")
                self.extra_arguments = (
                    "console=ttyS0 ks=file:/centos6-i386.ks text utf8")
                self.initrd_inject = self.get_contrib_path(
                    "centos6/centos6-i386.ks")
            elif arch == 'amd64':
                self.install_location = (
                    "http://mirror.centos.org/centos/6/os/x86_64")
                self.extra_arguments = (
                    "console=ttyS0 ks=file:/centos6-amd64.ks text utf8")
                self.initrd_inject = self.get_contrib_path(
                    "centos6/centos6-amd64.ks")
        elif self.edition == '7':
            self.install_location = (
                "http://mirror.centos.org/centos/7/os/x86_64")
            self.extra_arguments = (
                "console=ttyS0 inst.ks=file:/centos7-amd64.ks text "
                "inst.cmdline inst.headless")
            self.initrd_inject = self.get_contrib_path(
                "centos7/centos7-amd64.ks")
        super(CentOSBuilder, self).build_image(params)
