# https://hub.docker.com/_/centos?tab=tags
FROM centos:7

MAINTAINER LPSmodsim 

LABEL remarks="PyDL"

RUN yum -y install python3

RUN yum -y install centos-release-scl

RUN yum -y install python3-pip

RUN yum -y groupinstall 'Development Tools'


RUN pip3 install black

