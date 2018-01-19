mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))


run-postgres:
	docker run --rm -e POSTGRES_DB=guillotina -e POSTGRES_USER=guillotina -p 127.0.0.1:5432:5432 --name postgres postgres:10.1


run-cockroachdb:
	docker pull cockroachdb/cockroach:v1.1.3
	docker run -p 127.0.0.1:26257:26257 -p 127.0.0.1:9080:8080 --rm cockroachdb/cockroach:v1.1.3 start --insecure


create-cockroachdb:
	./bin/python _cockroachdb-createdb.py
