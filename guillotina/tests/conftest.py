from pytest_docker_fixtures import images


images.configure("cockroach", "cockroachdb/cockroach", "v2.1.6")


images.configure("postgresql", version="10.9")

images.configure(
    "elasticsearch",
    "docker.elastic.co/elasticsearch/elasticsearch",
    "7.8.0",
    max_wait_s=90,
    env={
        "xpack.security.enabled": None,  # unset
        "discovery.type": "single-node",
        "http.host": "0.0.0.0",
        "transport.host": "127.0.0.1",
    },
)


pytest_plugins = [
    "guillotina.tests.fixtures",
    "pytest_docker_fixtures",
    "guillotina_elasticsearch.tests.fixtures",
]
