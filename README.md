# maas-image-builder

# maas 镜像制作

curtin，使用curtin hooks， 将load目标环境，修改打包的镜像
使用grub， 更新initramfs环境启动项， root环境启动，

可以在contrib中，可进行修改添加启动项信息，
curtin环境中 运行  grub2-mkconfig  -o /boot/grub2/grub.cfg



制作进行流程：
    相关类：VirtInstallBuilder、子类RHELBuilder

    子类将iso镜像文件，mount起来，将curtin hooks 文件、kickstart配置文件放置内部
    将文件目录使用mkisofs，重新制作成iso镜像文件。

    使用virt-install 命令将 iso镜像文件做成虚拟机， 虚拟磁盘等
    将磁盘导出，使用压缩命令制成 tar.gz


其中如果，rhel kickstart中，有些包无法下载，

    你可在上述源中，手动找到后，kickstart配置源中，将目标包加上，
    如：cloud-init 我之前一直无法找到，
    修改如下即可：
    repo --name="repo3" --baseurl=http://archives.fedoraproject.org/pub/archive/fedora/linux/releases/20/Everything/x86_64/os/ --includepkgs=python-oauth,python-prettytable,cloud-init
    或者将源全部替换成国内源

    如果在进行相关部署时，发现无法启动，可以修改配置文件，手动进入虚拟机查看相关信息，手动安装等



新的代码提交，修改了maas dhcp 分配的ip无法在。
