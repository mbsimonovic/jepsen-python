#!/usr/bin/env bash

REPO='deb https://apt.dockerproject.org/repo ubuntu-xenial main'

# update & upgrade
sudo apt-get update
sudo apt-get -y upgrade
# enable ssh
sudo apt-get install openssh-server
# optionally login from your laptop now

sudo apt-get -y install python-pip python-virtualenv python-dev
python --version
# Python 2.7.12
lsb_release -a
#No LSB modules are available.
#Distributor ID: Ubuntu
#Description: Ubuntu 16.04.1 LTS
#Release: 16.04
#Codename: xenial
uname -a
#Linux osboxes 4.4.0-53-generic #74-Ubuntu SMP Fri Dec 2 15:59:10 UTC 2016 x86_64 x86_64 x86_64 GNU/Linux
#
# install docker https://docs.docker.com/engine/installation/linux/ubuntulinux/
sudo apt-get install apt-transport-https ca-certificates
sudo apt-key adv \
               --keyserver hkp://ha.pool.sks-keyservers.net:80 \
               --recv-keys 58118E89F3A912897C070ADBF76221572C52609D

echo "$REPO" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y linux-image-extra-$(uname -r) linux-image-extra-virtual
sudo apt-get install -y docker-engine
sudo service docker start

#For your db nodes, you'll need some (I use five) ubuntu boxes (I run ubuntu
# xenial). By default they're named n1, n2, n3, n4, and n5.

git clone https://github.com/mbsimonovic/jepsen-python
cd jepsen-python
git submodule init && git submodule update
(cd blockade && pip install -r requirements.txt)
sudo docker-compose up