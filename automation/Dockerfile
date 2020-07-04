FROM gentoo/stage3-amd64:latest
RUN echo "MAKEOPTS=\"-j8\"" >> /etc/portage/make.conf
RUN echo "GENTOO_MIRRORS=\"https://mirrors.bfsu.edu.cn/gentoo\"" >> /etc/portage/make.conf
RUN mkdir -p /etc/portage/repos.conf
COPY gentoo.conf /etc/portage/repos.conf/
RUN emerge-webrsync
RUN emerge --verbose --update --deep --newuse @world
