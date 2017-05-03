from time import sleep


ETCD_IMAGE = 'quay.io/coreos/etcd:v3.2.0-rc.0'


def run_docker_etcd(label='testingetcd'):
    import docker
    docker_client = docker.from_env(version='1.23')

    # Clean up possible other docker containers
    test_containers = docker_client.containers.list(
        all=True,
        filters={'label': label})
    for test_container in test_containers:
        test_container.stop()
        test_container.remove(v=True, force=True)

    # Create a new one
    container = docker_client.containers.run(
        name='my-etcd-1',
        image=ETCD_IMAGE,
        labels=[label],
        command=' '.join([
            '/usr/local/bin/etcd',
            '--name my-etcd-1',
            '--data-dir /etcd-data',
            '--listen-client-urls http://0.0.0.0:2379',
            '--advertise-client-urls http://0.0.0.0:2379',
            '--listen-peer-urls http://0.0.0.0:2380',
            '--initial-advertise-peer-urls http://0.0.0.0:2380',
            '--initial-cluster my-etcd-1=http://0.0.0.0:2380',
            '--initial-cluster-token my-etcd-token',
            '--initial-cluster-state new',
            '--auto-compaction-retention 1'
        ]),
        detach=True,
        ports={
            '2379/tcp': 2379
        },
        cap_add=['IPC_LOCK'],
        mem_limit='200m',
        privileged=True
    )
    ident = container.id
    count = 1

    opened = False
    host = ''

    print('starting etcd')
    while count < 30 and not opened:
        count += 1
        try:
            docker_client.containers.get(ident)
        except docker.errors.NotFound:
            continue
        sleep(1)
    print('postgresql etcd')
    return host


def cleanup_etcd_docker(label='testingetcd'):
    import docker
    docker_client = docker.from_env(version='1.23')
    # Clean up possible other docker containers
    test_containers = docker_client.containers.list(
        all=True,
        filters={'label': label})
    for test_container in test_containers:
        test_container.kill()
        test_container.remove(v=True, force=True)
