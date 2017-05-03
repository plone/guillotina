from time import sleep

import os


POSTGRESQL_IMAGE = 'postgres:9.6'


def run_docker_postgresql(label='testingaiopg'):
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
        image=POSTGRESQL_IMAGE,
        labels=[label],
        detach=True,
        ports={
            '5432/tcp': 5432
        },
        cap_add=['IPC_LOCK'],
        mem_limit='1g',
        environment={
            'POSTGRES_PASSWORD': '',
            'POSTGRES_DB': 'guillotina',
            'POSTGRES_USER': 'postgres'
        },
        privileged=True
    )
    ident = container.id
    count = 1

    container_obj = docker_client.containers.get(ident)

    opened = False
    host = ''

    print('starting postgresql')
    while count < 30 and not opened:
        count += 1
        try:
            container_obj = docker_client.containers.get(ident)
        except docker.errors.NotFound:
            continue
        sleep(1)
        if container_obj.attrs['NetworkSettings']['IPAddress'] != '':
            if os.environ.get('TESTING', '') == 'jenkins':
                host = container_obj.attrs['NetworkSettings']['IPAddress']
            else:
                host = 'localhost'

        if host != '':
            try:
                conn = psycopg2.connect("dbname=guillotina user=postgres host=%s port=5432" % host)  # noqa
                cur = conn.cursor()
                cur.execute("SELECT 1;")
                cur.fetchone()
                cur.close()
                conn.close()
                opened = True
            except: # noqa
                conn = None
                cur = None
    print('postgresql started')
    return host


def cleanup_postgres_docker(label='testingaiopg'):
    import docker
    docker_client = docker.from_env(version='1.23')
    # Clean up possible other docker containers
    test_containers = docker_client.containers.list(
        all=True,
        filters={'label': label})
    for test_container in test_containers:
        test_container.kill()
        test_container.remove(v=True, force=True)
