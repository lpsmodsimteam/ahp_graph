# https://hub.docker.com/_/centos?tab=tags
FROM centos:7

MAINTAINER LPSmodsim 

LABEL remarks="PyDL"

RUN yum -y install python3 \
                   centos-release-scl \
                   python3-pip \ 
                   python3-devel \
                   graphviz \
                   graphviz-devel \
                   libgraphviz-dev

RUN yum -y groupinstall 'Development Tools'

# required by orjson
RUN pip3 install --upgrade "pip>=20.3"

RUN pip3 install black  \
                 pygraphviz \
                 orjson
