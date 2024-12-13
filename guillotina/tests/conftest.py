from pytest_docker_fixtures import images


images.configure(
    name="cockroach",
    image="cockroachdb/cockroach",
    version="v24.3.0",
    options={"command": "start-single-node --insecure"},
)

images.configure("postgresql", version="10.9")


pytest_plugins = ["guillotina.tests.fixtures", "pytest_docker_fixtures"]
