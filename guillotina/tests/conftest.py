from pytest_docker_fixtures import images


images.configure("cockroach", "cockroachdb/cockroach", "v2.1.6")


images.configure("postgresql", version="10.9")


pytest_plugins = ["guillotina.tests.fixtures", "pytest_docker_fixtures"]
