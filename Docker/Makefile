tag_ahp=ahp
tag_ahp_noTyping=ahp_notyping
tag_sst=sst12
tag_sst_noTyping=sst12_notyping

#
.PHONY: help clean 

help:
	@echo "make help"
	@echo "      this message"
	@echo "make docker_ahp"
	@echo "      build and run docker with AHP's master branch"
	@echo "make docker_ahp_build"
	@echo "make docker_ahp_live"
	@echo "      run docker /bin/bash"
	@echo " "
	@echo "make docker_ahp_noTyping"
	@echo "      build and run docker with AHP's noTyping branch"
	@echo "make docker_ahp_noTyping_build"
	@echo "make docker_ahp_noTyping_live"
	@echo "      run docker /bin/bash"
	@echo " "
	@echo "make docker_sst"
	@echo "      build and run docker SST 12 with AHP's master branch"
	@echo "make docker_sst_build"
	@echo "make docker_sst_live"
	@echo "      run docker /bin/bash"
	@echo " "
	@echo "make docker_sst_noTyping"
	@echo "      build and run docker SST 12 with AHP's noTyping branch"
	@echo "make docker_sst_noTyping_build"
	@echo "make docker_sst_noTyping_live"
	@echo "      run docker /bin/bash"


# master branch
docker_ahp: docker_ahp_build docker_ahp_live
docker_ahp_build:
	docker build -f Dockerfile_AHP_noTyping -t $(tag_ahp) .

docker_ahp_live:
	docker run -it -u `id -u`:`id -g` --rm -v`pwd`:/scratch -w/scratch $(tag_ahp) /bin/bash


# "noTyping" branch
docker_ahp_noTyping: docker_ahp_noTyping_build docker_ahp_noTyping_live
docker_ahp_noTyping_build:
	docker build -f Dockerfile_AHP_noTyping -t $(tag_ahp_noTyping) .

docker_ahp_noTyping_live:
	docker run -it -u `id -u`:`id -g` --rm -v`pwd`:/scratch -w/scratch $(tag_ahp_noTyping) /bin/bash


# SST 12 with master branch
docker_sst: docker_sst_build docker_sst_live
docker_sst_build:
	docker build -f Dockerfile_SST_12 -t $(tag_sst) . 

docker_sst_live:
	docker run -it -u `id -u`:`id -g` --rm -v`pwd`:/scratch -w/scratch $(tag_sst) /bin/bash


# SST 12 with noTyping branch
docker_sst_noTyping: docker_sst_noTyping_build docker_sst_noTyping_live
docker_sst_noTyping_build:
	docker build -f Dockerfile_SST_12 -t $(tag_sst_noTyping) . 

docker_sst_noTyping_live:
	docker run -it -u `id -u`:`id -g` --rm -v`pwd`:/scratch -w/scratch $(tag_sst_noTyping) /bin/bash

