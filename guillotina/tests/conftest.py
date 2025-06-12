from pytest_docker_fixtures import images


images.configure(
    name="cockroach",
    image="cockroachdb/cockroach",
    version="v24.3.0",
    options={"command": "start-single-node --insecure"},
)

images.configure(
    name="redis",
    image="redis",
    version="7.2.5",
    options={"cap_add": ["IPC_LOCK"], "mem_limit": "200m"},
)

# images.configure("postgresql", version="10.9")
images.configure(
    "postgresql",
    version="15.2",
    env={
        "POSTGRES_PASSWORD": "postgres",
        "POSTGRES_DB": "guillotina",
        "POSTGRES_USER": "postgres",
    },
)


pytest_plugins = ["guillotina.tests.fixtures", "pytest_docker_fixtures"]
