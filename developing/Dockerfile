FROM gentoo/stage3-amd64:latest
RUN echo "MAKEOPTS=\"-j8\"" >> /etc/portage/make.conf
RUN echo "GENTOO_MIRRORS=\"https://mirrors.bfsu.edu.cn/gentoo\"" >> /etc/portage/make.conf
RUN mkdir -p /etc/portage/repos.conf
COPY gentoo.conf /etc/portage/repos.conf/
RUN emerge-webrsync
RUN emerge --verbose --update --deep --newuse @world

# python versions
RUN emerge --verbose --update --deep --newuse dev-lang/python:3.8
RUN emerge --verbose --update --deep --newuse dev-lang/python:3.7
RUN emerge --verbose --update --deep --newuse dev-lang/python:3.6
RUN echo "*/* PYTHON_TARGETS: python3_6 python3_7 python3_8" >> /etc/portage/package.use/fish

# some useful additions
RUN echo ">=dev-libs/libpcre2-10.34 pcre32" >> /etc/portage/package.use/fish
RUN emerge --verbose --update --deep --newuse app-shells/fish
RUN emerge --verbose --update --deep --newuse app-editors/vim
RUN emerge --verbose --update --deep --newuse dev-vcs/git
RUN emerge --verbose --update --deep --newuse app-portage/repoman

# setup local repo
RUN echo "[localrepo]" > /etc/portage/repos.conf/localrepo.conf
RUN echo "location = /var/db/repos/localrepo" >> /etc/portage/repos.conf/localrepo.conf
