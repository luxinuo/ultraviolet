#==============================================================#
# File      :   Makefile
# Desc      :   crystaldb shortcuts
# Ctime     :   2019-04-13
# Mtime     :   2023-07-29
# Path      :   Makefile
# Author    :   CrystalDB LLC
# License   :   CrystalDB ELA
#==============================================================#
# crystaldb version & default develop & testing el version
VERSION?=v2.2.0
EL_VER=9

# local name
SRC_PKG=crystaldb-$(VERSION).tgz
APP_PKG=crystaldb-app-$(VERSION).tgz
REPO_PKG=crystaldb-pkg-$(VERSION).el${EL_VER}.x86_64.tgz
DOCKER_PKG=crystaldb-docker-$(VERSION).tgz
EL7_PKG=crystaldb-pkg-$(VERSION).el7.x86_64.tgz
EL8_PKG=crystaldb-pkg-$(VERSION).el8.x86_64.tgz
EL9_PKG=crystaldb-pkg-$(VERSION).el9.x86_64.tgz

###############################################################
#                      1. Quick Start                         #
###############################################################
# run with nopass SUDO user (or root) on CentOS 7.x node
default: tip
tip:
	@echo "# Run on Linux x86_64 EL7-9 node with sudo & ssh access"
	@echo "./configure     # pre-check and templating config"
	@echo "./install.yml   # install crystaldb on current node"


# serve a local docs with docsify or python http
doc:
	docs/serve

#-------------------------------------------------------------#
# there are 3 steps launching crystaldb:
all: bootstrap configure install

# (1). BOOTSTRAP  crystaldb pkg & util preparedness
bootstrap:
	./boostrap

# (2). CONFIGURE  crystaldb in interactive mode
config:
	./configure

# (3). INSTALL    crystaldb on current node
install:
	./install.yml
###############################################################



###############################################################
#                        OUTLINE                              #
###############################################################
#  (1). Quick-Start   :   shortcuts for launching crystaldb (above)
#  (2). Download      :   shortcuts for downloading resources
#  (3). Configure     :   shortcuts for configure crystaldb
#  (4). Install       :   shortcuts for running playbooks
#  (5). Sandbox       :   shortcuts for mange sandbox vm nodes
#  (6). Testing       :   shortcuts for testing features
#  (7). Develop       :   shortcuts for dev purpose
#  (8). Release       :   shortcuts for release and publish
#  (9). Misc          :   shortcuts for miscellaneous tasks
###############################################################



###############################################################
#                      2. Download                            #
###############################################################
# There are two things needs to be downloaded:
#    crystaldb.tgz    :   source code
#    pkg.tgz       :   offline rpm packages (build under 7.9)
#
# get latest stable version to ~/crystaldb
src:
	curl -SL https://github.com/Vonng/crystaldb/releases/download/${VERSION}/${SRC_PKG} -o ~/crystaldb.tgz

# download pkg.tgz to /tmp/pkg.tgz
pkg:
	curl -SL https://github.com/Vonng/crystaldb/releases/download/${VERSION}/${REPO_PKG} -o /tmp/pkg.tgz
###############################################################



###############################################################
#                      3. Configure                           #
###############################################################
# there are several things needs to be checked before install
# use ./configure or `make config` to run interactive wizard
# it will install ansible (from offline rpm repo if available)

# common interactive configuration procedure
c: config
###############################################################



###############################################################
#                      4. Install                             #
###############################################################
# crystaldb is installed via ansible-playbook

# install crystaldb on meta nodes
csi:
	./csi.yml

# rebuild repo
repo:
	./csi.yml --tags=repo

# write upstream repo to /etc/yum.repos.d
repo-upstream:
	./csi.yml --tags=repo_upstream

# download repo packages
repo-build:
	sudo rm -rf /www/crystaldb/repo_complete
	./csi.yml --tags=repo_upstream,repo_build

# init prometheus
prometheus:
	./csi.yml --tags=prometheus

# init grafana
grafana:
	./csi.yml --tags=grafana

# init loki
loki:
	./csi.yml --tags=loki -e loki_clean=true

# init docker
docker:
	./docker.yml

###############################################################




###############################################################
#                       5. Sandbox                            #
###############################################################
# shortcuts to pull up vm nodes with vagrant on your own MacOS
# DO NOT RUN THESE SHORTCUTS ON YOUR META NODE!!!
# These shortcuts are running on your HOST machine which run
# crystaldb sandbox via virtualbox managed by vagrant.
#=============================================================#
# to setup vagrant sandbox env on your MacOS host:
#
#  Prepare
#  (1). make deps    (once) Install MacOS deps with homebrew
#  (2). make dns     (once) Write static DNS
#  (3). make start   (once) Pull-up vm nodes and setup ssh access
#  (4). make demo           Boot meta node same as Quick-Start
#=============================================================#

#------------------------------#
# 1. deps (macos)
#------------------------------#
# install macos sandbox software dependencies
deps:
	/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
	brew install vagrant virtualbox ansible

#------------------------------#
# 2. dns
#------------------------------#
# write static dns records (sudo password required) (only run on first time)
dns:
	sudo vagrant/dns

#------------------------------#
# 3. start
#------------------------------#
# start will pull-up node and write ssh-config
# it may take a while to download centos/7 box for the first time
start: up ssh      # 1-node version
ssh:               # add node ssh config to your ~/.ssh/config
	vagrant/ssh

#------------------------------#
# 4. demo
#------------------------------#
# launch one-node demo
demo: demo-prepare
	ssh meta "cd ~ && curl -fsSLO https://github.com/Vonng/crystaldb/releases/download/${VERSION}/${SRC_PKG} -o ~/crystaldb.tgz && tar -xf crystaldb.tgz"
	ssh meta 'cd ~/crystaldb; ./bootstrap -y'
	ssh meta 'cd ~/crystaldb; ./configure --ip 10.10.10.10 --non-interactive -m demo'
	ssh meta 'cd ~/crystaldb; ./install.yml'

#------------------------------#
# vagrant vm management
#------------------------------#
# default node (meta)
up:
	cd vagrant && vagrant up
dw:
	cd vagrant && vagrant halt
del:
	cd vagrant && vagrant destroy -f
nuke:
	cd vagrant && ./nuke
new: del up
clean: del
#------------------------------#
# extra nodes: node-{1,2,3}
up-test:
	cd vagrant && vagrant up node-1 node-2 node-3
dw-test:
	cd vagrant && vagrant halt node-1 node-2 node-3
del-test:
	cd vagrant && vagrant destroy -f node-1 node-2 node-3
new-test: del-test up-test
#------------------------------#
# status
st: status
status:
	cd vagrant && vagrant status
suspend:
	cd vagrant && vagrant suspend
resume:
	cd vagrant && vagrant resume
#------------------------------#
# vagrant templates:
v1:
	vagrant/switch meta
v4:
	vagrant/switch full
v7:
	vagrant/switch el7
v8:
	vagrant/switch el8
v9:
	vagrant/switch el9
vb:
	vagrant/switch build
vp:
	vagrant/switch prod
vm:
	vagrant/switch minio
vc:
	vagrant/switch citus
vnew: new ssh copy-pkg use-pkg copy-src use-src

###############################################################



###############################################################
#                       6. Testing                            #
###############################################################
# Convenient shortcuts for add traffic to sandbox pgsql clusters
#  ri  test-ri   :  init pgbench on meta or pg-test cluster
#  rw  test-rw   :  read-write pgbench traffic on meta or pg-test
#  ro  test-ro   :  read-only pgbench traffic on meta or pg-test
#  rc  test-rc   :  clean-up pgbench tables on meta or pg-test
#  test-rw2 & test-ro2 : heavy load version of test-rw, test-ro
#  test-rb{1,2,3} : reboot node 1,2,3
#=============================================================#
# meta cmdb bench
ri:
	pgbench -is10 postgres://dbuser_meta:DBUser.Meta@meta:5433/meta
rc:
	psql -AXtw postgres://dbuser_meta:DBUser.Meta@meta:5433/meta -c 'DROP TABLE IF EXISTS pgbench_accounts, pgbench_branches, pgbench_history, pgbench_tellers;'
rw:
	while true; do pgbench -nv -P1 -c4 --rate=64 -T10 postgres://dbuser_meta:DBUser.Meta@meta:5433/meta; done
ro:
	while true; do pgbench -nv -P1 -c8 --rate=256 --select-only -T10 postgres://dbuser_meta:DBUser.Meta@meta:5434/meta; done
rh:
	ssh meta 'sudo -iu postgres /opt/CrystalDB/bin/pg-heartbeat'
# pg-test cluster benchmark
test-ri:
	pgbench -is10  postgres://test:test@pg-test:5436/test
test-rc:
	psql -AXtw postgres://test:test@pg-test:5433/test -c 'DROP TABLE IF EXISTS pgbench_accounts, pgbench_branches, pgbench_history, pgbench_tellers;'
# pgbench small read-write / read-only traffic (rw=64TPS, ro=512QPS)
test-rw:
	while true; do pgbench -nv -P1 -c4 --rate=32 -T10 postgres://test:test@pg-test:5433/test; done
test-ro:
	while true; do pgbench -nv -P1 -c8 --select-only --rate=256 -T10 postgres://test:test@pg-test:5434/test; done
# pgbench read-write / read-only traffic (maximum speed)
test-rw2:
	while true; do pgbench -nv -P1 -c16 -T10 postgres://test:test@pg-test:5433/test; done
test-ro2:
	while true; do pgbench -nv -P1 -c64 -T10 --select-only postgres://test:test@pg-test:5434/test; done
test-rh:
	ssh node-1 'sudo -iu postgres /opt/CrystalDB/bin/pg-heartbeat'
#------------------------------#
# show patroni status for pg-test cluster
test-st:
	ssh -t node-1 "sudo -iu postgres patronictl -c /opt/CrystalDB/bin/patroni.yml list -W"
# reboot node 1,2,3
test-rb1:
	ssh -t node-1 "sudo reboot"
test-rb2:
	ssh -t node-2 "sudo reboot"
test-rb3:
	ssh -t node-3 "sudo reboot"
###############################################################




###############################################################
#                       7. Develop                            #
###############################################################
#  other shortcuts for development
#=============================================================#

#------------------------------#
# grafana dashboard management
#------------------------------#
di: dashboard-init                    # init grafana dashboards
dashboard-init:
	cd files/grafana/ && ./grafana.py init

dd: dashboard-dump                    # dump grafana dashboards
dashboard-dump:
	cd files/grafana/ && ./grafana.py dump

dc: dashboard-clean                   # cleanup grafana dashboards
dashboard-clean:
	cd files/grafana/ && ./grafana.py clean

du: dashboard-clean dashboard-init    # update grafana dashboards

#------------------------------#
# copy source & packages
#------------------------------#
# copy latest pro source code
copy: copy-src copy-pkg use-src use-pkg
cc: release copy-src copy-pkg use-src use-pkg

# copy crystaldb source code
copy-src:
	scp "dist/${VERSION}/${SRC_PKG}" meta:~/crystaldb.tgz
copy-pkg:
	scp dist/${VERSION}/${REPO_PKG} meta:/tmp/pkg.tgz
copy-el7:
	scp dist/${VERSION}/${EL7_PKG} meta:/tmp/pkg.tgz
copy-el8:
	scp dist/${VERSION}/${EL8_PKG} meta:/tmp/pkg.tgz
copy-el9:
	scp dist/${VERSION}/${EL9_PKG} meta:/tmp/pkg.tgz
copy-app:
	scp dist/${VERSION}/${APP_PKG} meta:~/app.tgz
	ssh -t meta 'rm -rf ~/app; tar -xf app.tgz; rm -rf app.tgz'
copy-docker:
	scp -r dist/docker meta:/tmp/
load-docker:
	ssh meta 'cat /tmp/docker.tgz | gzip -d -c - | docker load'
copy-all: copy-src copy-pkg

# extract packages
use-src:
	ssh -t meta 'rm -rf ~/crystaldb; tar -xf crystaldb.tgz; rm -rf crystaldb.tgz'
use-pkg:
	ssh meta "sudo mkdir -p /www; sudo tar -xf /tmp/pkg.tgz -C /www"
use-all: use-src use-pkg

# load config into cmdb
cmdb:
	bin/inventory_load
	bin/inventory_cmdb

#------------------------------#
# push / pull
#------------------------------#
push:
	rsync -avz ./ sv:~/crystaldb/ --delete --exclude-from 'vagrant/Vagrantfile'
pull:
	rsync -avz sv:~/crystaldb/ ./ --exclude-from 'vagrant/Vagrantfile' --exclude-from 'vagrant/.vagrant'

###############################################################



###############################################################
#                       8. Release                            #
###############################################################
# make crystaldb release (source code tarball)
r: release
release:
	bin/release ${VERSION}

rr: remote-release
remote-release: release copy-src use-src
	ssh meta "cd crystaldb; make release"
	scp meta:~/crystaldb/dist/${VERSION}/${SRC_PKG} dist/${VERSION}/${SRC_PKG}

# release offline packages with build environment
rp: release-package
release-package: release-el7 release-el8 release-el9
release-el7:
	scp bin/cache build-el7:/tmp/cache; ssh build-el7 "sudo bash /tmp/cache"; scp build-el7:/tmp/pkg.tgz dist/${VERSION}/crystaldb-pkg-${VERSION}.el7.x86_64.tgz
release-el8:
	scp bin/cache build-el8:/tmp/cache; ssh build-el8 "sudo bash /tmp/cache"; scp build-el8:/tmp/pkg.tgz dist/${VERSION}/crystaldb-pkg-${VERSION}.el8.x86_64.tgz
release-el9:
	scp bin/cache build-el9:/tmp/cache; ssh build-el9 "sudo bash /tmp/cache"; scp build-el9:/tmp/pkg.tgz dist/${VERSION}/crystaldb-pkg-${VERSION}.el9.x86_64.tgz


# validate offline packages with build environment
check: build-src build-repo build-boot
check-src:
	scp dist/${VERSION}/${SRC_PKG} build-el7:~/crystaldb.tgz ; ssh build-el7 "tar -xf crystaldb.tgz";
	scp dist/${VERSION}/${SRC_PKG} build-el8:~/crystaldb.tgz ; ssh build-el8 "tar -xf crystaldb.tgz";
	scp dist/${VERSION}/${SRC_PKG} build-el9:~/crystaldb.tgz ; ssh build-el9 "tar -xf crystaldb.tgz";
check-repo:
	scp dist/${VERSION}/crystaldb-pkg-${VERSION}.el7.x86_64.tgz build-el7:/tmp/pkg.tgz ; ssh build-el7 'sudo mkdir -p /www; sudo tar -xf /tmp/pkg.tgz -C /www'
	scp dist/${VERSION}/crystaldb-pkg-${VERSION}.el8.x86_64.tgz build-el8:/tmp/pkg.tgz ; ssh build-el8 'sudo mkdir -p /www; sudo tar -xf /tmp/pkg.tgz -C /www'
	scp dist/${VERSION}/crystaldb-pkg-${VERSION}.el9.x86_64.tgz build-el9:/tmp/pkg.tgz ; ssh build-el9 'sudo mkdir -p /www; sudo tar -xf /tmp/pkg.tgz -C /www'
check-boot:
	ssh build-el7 "cd crystaldb; ./bootstrap -n ; ./configure -m el7  -i 10.10.10.7 -n";
	ssh build-el8 "cd crystaldb; ./bootstrap -n ; ./configure -m el8  -i 10.10.10.8 -n";
	ssh build-el9 "cd crystaldb; ./bootstrap -n ; ./configure -m el9  -i 10.10.10.9 -n";



p: publish
publish:
	bin/publish ${VERSION}
###############################################################



###############################################################
#                     9. Environment                          #
###############################################################
meta:  del v1 new ssh copy-el9 use-pkg
	cp files/crystaldb/demo.yml crystaldb.yml
full: del v4 new ssh copy-el9 use-pkg
	cp files/crystaldb/demo.yml crystaldb.yml
citus: del vc new ssh copy-el9 use-pkg
	cp files/crystaldb/citus.yml crystaldb.yml
minio: del vm new ssh copy-el9 use-pkg
	cp files/crystaldb/citus.yml crystaldb.yml
el7: del v7 new ssh copy-el7 use-pkg
	cp files/crystaldb/test.yml crystaldb.yml
el8: del v8 new ssh copy-el8 use-pkg
	cp files/crystaldb/test.yml crystaldb.yml
el9: del v9 new ssh copy-el9 use-pkg
	cp files/crystaldb/test.yml crystaldb.yml
prod: del vp new ssh
	cp files/crystaldb/prod.yml crystaldb.yml
	scp dist/${VERSION}/crystaldb-pkg-${VERSION}.el9.x86_64.tgz meta-1:/tmp/pkg.tgz ; ssh meta-1 'sudo mkdir -p /www; sudo tar -xf /tmp/pkg.tgz -C /www'
	scp dist/${VERSION}/crystaldb-pkg-${VERSION}.el9.x86_64.tgz meta-2:/tmp/pkg.tgz ; ssh meta-2 'sudo mkdir -p /www; sudo tar -xf /tmp/pkg.tgz -C /www'
build: del vb new ssh
	cp files/crystaldb/build.yml crystaldb.yml
build-check: build check
	cp files/crystaldb/build.yml crystaldb.yml

###############################################################



###############################################################
#                        Inventory                            #
###############################################################
.PHONY: default tip link doc all bootstrap config install \
        src pkg \
        c \
        csi pgsql repo repo-upstream repo-build prometheus grafana loki docker \
        deps dns start ssh demo \
        up dw del new clean up-test dw-test del-test new-test clean \
        st status suspend resume v1 v4 v7 v8 v9 vb vp vm vc vnew \
        ri rc rw ro rh rhc test-ri test-rw test-ro test-rw2 test-ro2 test-rc test-st test-rb1 test-rb2 test-rb3 \
        di dd dc du dashboard-init dashboard-dump dashboard-clean \
        copy copy-src copy-pkg copy-app copy-docker load-docker copy-all use-src use-pkg use-all cmdb \
        r release rr remote-release rp release-pkg release-el7 release-el8 release-el9 check check-src check-repo check-boot p publish \
        meta full citus minio build build-check el7 el8 el9 prod
###############################################################



###############################################################
#                 For Testing(Lucas)                          #
###############################################################
crys-v:
	ansible-vault view vault.yml
crys-ping:
	ansible all -m ping


###############################################################
#        inventory config method Testing(Lucas)               #
###############################################################
crys-ai:
	ansible-inventory all --graph

# Display the inventory structure and the cluster vars(useful)
crys-ai-vars:
	ansible-inventory --graph --ask-vault-pass --vars


###############################################################
#        Observation of playbook tasks(Lucas)               #
###############################################################
crys-list-tasks:
	ansible-playbook crys.yml --list-tasks --ask-vault-password


node-list-tasks:
	ansible-playbook node.yml --list-tasks --ask-vault-password

etcd-list-tasks:
	ansible-playbook etcd.yml --list-tasks --ask-vault-password

ces-list-tasks:
	ansible-playbook ces.yml --list-tasks --ask-vault-password


###############################################################
#                 For cmdb(Lucas)                             #
###############################################################
crys-conf:
	conf.py -c pg-crystal -i 77.77.77.77

crys-conf-rm:
	conf-rm.py -c pg-crystal -i 77.77.77.77



###############################################################
# python3.11 getting pip and advance toolkits(Lucas)          #
###############################################################

# Getting pip for python version 3.11
crys-py311-pip:
	python3.11 terraform/spec/get-pip.py --user

# Data Science toolkits
crys-ds:
	python3.11 -m pip install psycopg2-binary pandas numpy matplotlib seaborn

crys-utils:
	python3.11 -m pip install requests

crys-alchemy:
	python3.11 -m pip install SQLAlchemy
	sed "s/EnterpriseDB/EnterpriseDB|CrystalDB/g" /home/crys/.local/lib/python3.11/site-packages/sqlalchemy/dialects/postgresql/base.py > base_test.py
	cp base_test.py /home/crys/.local/lib/python3.11/site-packages/sqlalchemy/dialects/postgresql/base.py
	rm base_test.py

###############################################################
# 					Shard Demo       						  #
###############################################################
shard-demo-data:
	curl https://examples.citusdata.com/tutorial/companies.csv > files/data_src/companies.csv
	curl https://examples.citusdata.com/tutorial/campaigns.csv > files/data_src/campaigns.csv
	curl https://examples.citusdata.com/tutorial/ads.csv > files/data_src/ads.csv

shard-demo-script-show:
	cat files/data_src/shard_tbl_demo.sql

shard-conf:
	python3.11 bin/shard.py

