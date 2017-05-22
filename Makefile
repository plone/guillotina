mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))


run-postgres:
	docker run -e POSTGRES_DB=guillotina -e POSTGRES_USER=postgres -p 127.0.0.1:5432:5432 postgres:9.6

run-etcd:
	docker run --rm -p 2379:2379 \
    --name etcd-v3.2.0-rc.0 \
    quay.io/coreos/etcd:v3.2.0-rc.0 \
    /usr/local/bin/etcd \
    --name my-etcd-1 \
    --data-dir /etcd-data \
    --listen-client-urls http://0.0.0.0:2379 \
    --advertise-client-urls http://0.0.0.0:2379 \
    --listen-peer-urls http://0.0.0.0:2380 \
    --initial-advertise-peer-urls http://0.0.0.0:2380 \
    --initial-cluster my-etcd-1=http://0.0.0.0:2380 \
    --initial-cluster-token my-etcd-token \
    --initial-cluster-state new \
    --auto-compaction-retention 1


run-cockroachdb:
	docker pull cockroachdb/cockroach:v1.0
	docker run -p 127.0.0.1:26257:26257 -p 127.0.0.1:9080:8080 --rm cockroachdb/cockroach:v1.0 start --insecure


create-cockroachdb:
	./bin/py _cockroachdb-createdb.py
