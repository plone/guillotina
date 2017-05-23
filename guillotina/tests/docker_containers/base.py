from time import sleep

import docker
import os


COCKROACH_IMAGE = 'cockroachdb/cockroach:v1.0'


class BaseImage:

    docker_version = '1.23'
    label = 'foobar'
    image = None
    to_port = from_port = None
    image_options = dict(
        cap_add=['IPC_LOCK'],
        mem_limit='1g',
        environment={},
        privileged=True)

    def check(self, host):
        return True

    def run(self):
        docker_client = docker.from_env(version=self.docker_version)

        # Clean up possible other docker containers
        test_containers = docker_client.containers.list(
            all=True,
            filters={'label': self.label})
        for test_container in test_containers:
            test_container.stop()
            test_container.remove(v=True, force=True)

        # Create a new one
        container = docker_client.containers.run(
            image=self.image,
            labels=[self.label],
            detach=True,
            ports={
                f'{self.to_port}/tcp': self.from_port
            },
            **self.image_options
        )
        ident = container.id
        count = 1

        container_obj = docker_client.containers.get(ident)

        opened = False
        host = ''

        print(f'starting {self.label}')
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
                opened = self.check(host)
        print(f'{self.label} started')
        return host

    def stop(self):
        docker_client = docker.from_env(version=self.docker_version)
        # Clean up possible other docker containers
        test_containers = docker_client.containers.list(
            all=True,
            filters={'label': self.label})
        for test_container in test_containers:
            test_container.kill()
            test_container.remove(v=True, force=True)
