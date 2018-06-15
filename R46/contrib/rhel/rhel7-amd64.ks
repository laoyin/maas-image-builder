#version=RHEL7
install
# Firewall configuration
firewall --enabled --service=ssh
# Use CDROM installation media
cdrom
repo --name="repo0" --baseurl=http://mirrors.kernel.org/centos/7/os/x86_64 --includepkgs=python-pygments,grub2-efi-modules,efibootmgr
repo --name="repo1" --baseurl=http://mirrors.kernel.org/centos/7/updates/x86_64 --includepkgs=python-pygments
repo --name="repo2" --baseurl=http://mirrors.kernel.org/centos/7/extras/x86_64
repo --name="repo3" --baseurl=http://archives.fedoraproject.org/pub/archive/fedora/linux/releases/20/Everything/x86_64/os/ --includepkgs=python-oauth,python-prettytable,cloud-init
# Root password
rootpw --iscrypted $6$c78cFcbEdD2FcfE1$W0v5nUb1j1T8E3szv01CoBWFnl1TEWpt43WSZqtVP5kNih6zLiixQWS1umh1bDGnzWIqkwCwjIR8lHr.W0ua21
# System authorization information
auth --useshadow --enablemd5
# System keyboard
keyboard us
# System language
lang en_US.UTF-8
# SELinux configuration
selinux --enforcing
# Installation logging level
logging --level=info
# Poweroff after installation
poweroff
# System services
services --disabled="avahi-daemon,iscsi,iscsid,firstboot,kdump" --enabled="network,sshd,rsyslog,tuned,chronyd"
# System timezone
timezone --isUtc America/New_York
# Network information
network  --bootproto=dhcp --device=eth0 --onboot=on
# System bootloader configuration
bootloader --append="console=ttyS0,115200n8 console=tty0" --location=mbr --driveorder="sda" --timeout=1
# Clear the Master Boot Record
zerombr
# Partition clearing information
clearpart --all
# Disk partitioning information
part / --fstype="ext4" --size=3072

%post

# make sure firstboot doesn't start
echo "RUN_FIRSTBOOT=NO" > /etc/sysconfig/firstboot

cat <<EOL >> /etc/rc.local
if [ ! -d /root/.ssh ] ; then
    mkdir -p /root/.ssh
    chmod 0700 /root/.ssh
    restorecon /root/.ssh
fi
EOL

cat <<EOL >> /etc/ssh/sshd_config
UseDNS no
PermitRootLogin without-password
EOL

# bz705572
ln -s /boot/grub/grub.conf /etc/grub.conf

# bz688608
sed -i 's|\(^PasswordAuthentication \)yes|\1no|' /etc/ssh/sshd_config

# allow sudo powers to cloud-user
echo -e 'cloud-user\tALL=(ALL)\tNOPASSWD: ALL' >> /etc/sudoers

#setup getty on ttyS0
echo "ttyS0" >> /etc/securetty
cat <<EOF > /etc/init/ttyS0.conf
start on stopped rc RUNLEVEL=[2345]
stop on starting runlevel [016]
respawn
instance /dev/ttyS0
exec /sbin/agetty /dev/ttyS0 115200 vt100-nav
EOF

# lock root password
passwd -d root
passwd -l root

# fix the cloud-init config, so its for rhel and not for fedora
sed -i 's/distro: fedora/distro: rhel/g' /etc/cloud/cloud.cfg
sed -i 's/name: fedora/name: cloud-user/g' /etc/cloud/cloud.cfg
sed -i 's/gecos: Fedora Cloud User/gecos: RHEL Cloud User/g' /etc/cloud/cloud.cfg

# fix dracut to create initramfs for a generic host
cat <<EOF > /etc/dracut.conf.d/maas.conf
hostonly="no"
show_modules="yes"
EOF
dracut --force

# delete the eth0 config
rm -rf /etc/sysconfig/network-scripts/ifcfg-eth0

# clean up installation logs"
yum clean all
rm -rf /var/log/yum.log
rm -rf /var/lib/yum/*
rm -rf /root/install.log
rm -rf /root/install.log.syslog
rm -rf /root/anaconda-ks.cfg
rm -rf /var/log/anaconda*
%end

%packages
@core
cloud-init
python-oauth
grub2-efi-modules
efibootmgr
# Don't install NetworkManager
-NetworkManager

%end
