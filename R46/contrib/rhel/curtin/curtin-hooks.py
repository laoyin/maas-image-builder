#!/usr/bin/env python

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

import os
import re
import sys
import shutil

sys.path.append('/curtin')
from curtin import (
    block,
    net,
    util,
    )

"""
RedHat Enterprise Linux 7

Currently Support:

- Legacy boot
- UEFI boot
- DHCP of BOOTIF

Not Supported:

- Multiple network configration
- IPv6
"""

FSTAB_PREPEND = """\
#
# /etc/fstab
# Created by MAAS fast-path installer.
#
# Accessible filesystems, by reference, are maintained under '/dev/disk'
# See man pages fstab(5), findfs(8), mount(8) and/or blkid(8) for more info
#
"""

FSTAB_UEFI = """\
LABEL=uefi-boot /boot/efi vfat defaults 0 0
"""

GRUB_PREPEND = """\
# Set by MAAS fast-path installer.
GRUB_TIMEOUT=0
GRUB_TERMINAL_OUTPUT=console
GRUB_DISABLE_OS_PROBER=true
"""


def get_block_devices(target):
    """Returns list of block devices for the given target."""
    devs = block.get_devices_for_mp(target)
    blockdevs = set()
    for maybepart in devs:
        (blockdev, part) = block.get_blockdev_for_partition(maybepart)
        blockdevs.add(blockdev)
    return list(blockdevs)


def get_root_info(target):
    """Returns the root partitions information."""
    rootpath = block.get_devices_for_mp(target)[0]
    rootdev = os.path.basename(rootpath)
    blocks = block._lsblock()
    return blocks[rootdev]


def get_uefi_partition():
    """Return the UEFI partition."""
    for _, value in block._lsblock().items():
        if value['LABEL'] == 'uefi-boot':
            return value
    return None


def read_file(path):
    """Returns content of a file."""
    with open(path, 'r', encoding='utf-8') as stream:
        return stream.read()

def load_config(path):
    import json
    """Loads the curtin config."""
    with open(path, 'r') as stream:
        return json.load(stream)


def write_fstab(target, curtin_fstab):
    """Writes the new fstab, using the fstab provided
    from curtin."""
    fstab_path = os.path.join(target, 'etc', 'fstab')
    fstab_data = read_file(curtin_fstab)
    with open(fstab_path, 'w') as stream:
        stream.write(FSTAB_PREPEND)
        stream.write(fstab_data)
        if util.is_uefi_bootable():
            stream.write(FSTAB_UEFI)


def strip_kernel_params(params, strip_params=[]):
    """Removes un-needed kernel parameters."""
    new_params = []
    for param in params:
        remove = False
        for strip in strip_params:
             if param.startswith(strip):
                 remove = True
                 break
        if remove is False:
            new_params.append(param)
    return new_params


def get_extra_kernel_parameters():
    """Extracts the extra kernel commands from /proc/cmdline
    that should be placed onto the host.

    Any command following the '--' entry should be placed
    onto the host.
    """
    cmdline = read_file('/proc/cmdline')
    cmdline = cmdline.split()
    if '--' not in cmdline:
        return []
    idx = cmdline.index('--') + 1
    if idx >= len(cmdline) + 1:
        return []
    return strip_kernel_params(
        cmdline[idx:],
        strip_params=['initrd=', 'BOOT_IMAGE=', 'BOOTIF='])


def update_grub_default(target, extra=[]):
    """Updates /etc/default/grub with the correct options."""
    grub_default_path = os.path.join(target, 'etc', 'default', 'grub')
    extra.append("fsck.mode=skip")
    extra.append("rootfstype=ext4")
    kernel_cmdline = ' '.join(extra)
    # fsck.mode=skip, change the default
    with open(grub_default_path, 'a') as stream:
        stream.write(GRUB_PREPEND)
        stream.write('GRUB_CMDLINE_LINUX=\"%s\"\n' % kernel_cmdline)
        # stream.write('GRUB_CMDLINE_LINUX_DEFAULT=\"%s\"\n' % kernel_cmdline)


def grub2_install(target, root):
    """Installs grub2 to the root."""
    with util.RunInChroot(target) as in_chroot:
        in_chroot(['grub2-install', '--recheck', root])


def grub2_mkconfig(target):
    """Writes the new grub2 config."""
    with util.RunInChroot(target) as in_chroot:
        in_chroot(['grub2-mkconfig', '-o', '/boot/grub2/grub.cfg'])


def install_efi(target, uefi_path):
    """Install the EFI data from /boot into efi partition."""
    # Create temp mount point for uefi partition.
    tmp_efi = os.path.join(target, 'boot', 'efi_part')
    os.mkdir(tmp_efi)
    util.subp(['mount', uefi_path, tmp_efi])

    # Copy the data over.
    try:
        efi_path = os.path.join(target, 'boot', 'efi')
        if os.path.exists(os.path.join(tmp_efi, 'EFI')):
            shutil.rmtree(os.path.join(tmp_efi, 'EFI'))
        # bug  does not have a dir  EFI
        #No such file or directory: '/tmp/tmpab9g_us0/target/boot/efi/EFI'
        #os.mkdir(os.path.join(tmp_efi, 'EFI'))
        if os.path.exists(os.path.join(efi_path, 'EFI')):
            shutil.copytree(
                os.path.join(efi_path, 'EFI'),
                os.path.join(tmp_efi, 'EFI'))
        else:
            shutil.copytree(
                os.path.join(target, "yxp"),
                os.path.join(tmp_efi, 'EFI'))
    finally:
        # Clean up tmp mount
        util.subp(['umount', tmp_efi])
        os.rmdir(tmp_efi)

    # Mount and do grub install
    mount_flag = True
    try:
        util.subp(['mount', uefi_path, efi_path])
    except Exception as e:
        try:
            util.subp(['umount', efi_path])
            util.subp(['mount', uefi_path, efi_path])
        except Exception as e:
            mount_flag = False
            print(e)
            print("cant not mount %s" %uefi_path)

    #  check the  EFI directory
    if not check_efi_dir(target):
        shutil.copytree(
            os.path.join(target, "yxp"),
            os.path.join(efi_path, 'EFI'))
        print("check why dont have the file")

    try:
        with util.RunInChroot(target) as in_chroot:
            in_chroot([
                'grub2-install', '--target=x86_64-efi',
                '--efi-directory', '/boot/efi',
                '--recheck'])
    finally:
        if mount_flag:
            util.subp(['umount', efi_path])


def set_autorelabel(target):
    """Creates file /.autorelabel.

    This is used by SELinux to relabel all of the
    files on the filesystem to have the correct
    security context. Without this SSH login will
    fail.
    """
    path = os.path.join(target, '.autorelabel')
    open(path, 'a').close()


def get_boot_mac():
    """Return the mac address of the booting interface."""
    cmdline = read_file('/proc/cmdline')
    cmdline = cmdline.split()
    try:
        bootif = [
            option
            for option in cmdline
            if option.startswith('BOOTIF')
            ][0]
    except IndexError:
        return None
    _, mac = bootif.split('=')
    mac = mac.split('-')[1:]
    return ':'.join(mac)


def get_interface_names():
    """Return a dictionary mapping mac addresses to interface names."""
    sys_path = "/sys/class/net"
    ifaces = {}
    for iname in os.listdir(sys_path):
        mac = read_file(os.path.join(sys_path, iname, "address"))
        mac = mac.strip().lower()
        ifaces[mac] = iname
    return ifaces


def get_ipv4_config(iface, data):
    """Returns the contents of the interface file for ipv4."""
    config = [
        'TYPE="Ethernet"',
        'NM_CONTROLLED="no"',
        'USERCTL="yes"',
        ]
    if 'hwaddress' in data:
        config.append('HWADDR="%s"' % data['hwaddress'])
    else:
        config.append('DEVICE="%s"' % iface)
    if data['auto']:
        config.append('ONBOOT="yes"')
    else:
        config.append('ONBOOT="no"')

    method = data['method']
    if method == 'dhcp':
        config.append('BOOTPROTO="dhcp"')
        config.append('PEERDNS="yes"')
        config.append('PERSISTENT_DHCLIENT="1"')
        if 'hostname' in data:
            config.append('DHCP_HOSTNAME="%s"' % data['hostname'])
    elif method == 'static':
        config.append('BOOTPROTO="static"')
        config.append('IPADDR="%s"' % data['address'])
        config.append('NETMASK="%s"' % data['netmask'])
        if 'broadcast' in data:
            config.append('BROADCAST="%s"' % data['broadcast'])
        if 'gateway' in data:
            config.append('GATEWAY="%s"' % data['gateway'])
    elif method == 'manual':
        config.append('BOOTPROTO="none"')
    return '\n'.join(config)


def write_interface_config(target, iface, data):
    """Writes config for interface."""
    family = data['family']
    if family != "inet":
        # Only supporting ipv4 currently
        print(
            "WARN: unsupported family %s, "
            "failed to configure interface: %s" (family, iface))
        return
    config = get_ipv4_config(iface, data)
    path = os.path.join(
        target, 'etc', 'sysconfig', 'network-scripts', 'ifcfg-%s' % iface)
    with open(path, 'w') as stream:
        stream.write(config + '\n')


def get_address_gatway_message(network_config, iname):
    address_flag, gateway_flag = False, False
    address, gateway = None, None
    for config_line in network_config:
        if config_line.get('name', '') == iname:
            subnets = config_line['subnets']
            for sub  in subnets:
                gateway = sub['gateway']
                address = sub['address'].replace('/24', '')
                address_flag, gateway_flag = True, True

    if not min(address_flag, gateway_flag):
        raise  Exception("some bad thing happen, address:%s, gateway:%s"%(address, gateway))
    return address, gateway


def write_network_config(target, mac, network_config=None):
    """Write network configuration for the given MAC address."""
    # 为了满足 目前需求
    inames = get_interface_names()   # 获取网卡设备名称{"MAC address":"etho"}
    iname = inames[mac.lower()]
    if network_config is None:
        raise Exception("can not find network config, some bad thing happened")
    address, gateway = get_address_gatway_message(network_config, iname)
    write_interface_config(
        target, iname, {
            'family': 'inet',
            'hwaddress': mac.upper(),
            'auto': True,
            'method': 'static',
            'address': address,
            'gateway': gateway,
            'netmask': '255.255.255.0'
        })


def get_nertwork_config(curtin_config):
    return  curtin_config['network']['config']


def check_efi_dir(target):
    try:
        print(os.listdir(os.path.join(target, "boot", "efi")))
        print(os.path.exists(os.path.join(target, "boot", "efi", "EFI")))
        print("if exists EFI dir")
        if os.path.exists(os.path.join(target, "boot", "efi", "EFI")):
            print("check efi EFI dir")
            print(os.listdir(os.path.join(target, "boot", "efi", "EFI")))
            return True
        return False
    except Exception as e:
        print(e)
        return False

def tmp_dir_EFI_dir(target):
    """
    发现，targe EFI文件，一直会变化，镜像copytree时报错，no file or directory，
    先使用这种方式，看看是否可以解决此bug。
    :param target:
    :return:
    """
    if os.path.exists(os.path.join(target, "boot", "efi", "EFI")):
        EFI_path = os.path.join(target, "boot", "efi", "EFI")
        shutil.copytree(EFI_path, os.path.join(target, "yxp"))
        print("ok")
    else:
        print("no such file or directory")


def main():
    state = util.load_command_environment()
    target = state['target']
    print(target)
    tmp_dir_EFI_dir(target)
    print("target message")
    if target is None:
        print("Target was not provided in the environment.")
        sys.exit(1)
    fstab = state['fstab']
    if fstab is None:
        print("/etc/fstab output was not provided in the environment.")
        sys.exit(1)
    bootmac = get_boot_mac()
    if bootmac is None:
        print("Unable to determine boot interface.")
        sys.exit(1)
    devices = get_block_devices(target)
    if not devices:
        print("Unable to find block device for: %s" % target)
        sys.exit(1)

    write_fstab(target, fstab)
    update_grub_default(
        target, extra=get_extra_kernel_parameters())
    grub2_mkconfig(target)
    if util.is_uefi_bootable():
        uefi_part = get_uefi_partition()
        if uefi_part is None:
            print('Unable to determine UEFI parition.')
            sys.exit(1)
        print("分区信息")
        print(uefi_part)
        print("testing efi dir")
        install_efi(target, uefi_part['device_path'])
    else:
        for dev in devices:
            grub2_install(target, dev)

    curtin_config = load_config(state['config'])
    print(curtin_config)
    network_config = get_nertwork_config(curtin_config)
    print(network_config)
    set_autorelabel(target)
    write_network_config(target, bootmac, network_config)


if __name__ == "__main__":
    main()
