from time import sleep

import docker
import os


class BaseImage:

    docker_version = '1.23'
    name = 'foobar'
    image = None
    port = None
    host = ''
    base_image_options = dict(
        cap_add=['IPC_LOCK'],
        mem_limit='1g',
        environment={},
        privileged=True,
        detach=True,
        publish_all_ports=True)

    def get_image_options(self):
        image_options = self.base_image_options.copy()
        return image_options

    def get_port(self):
        if os.environ.get('TESTING', '') == 'jenkins' or 'TRAVIS' in os.environ:
            return self.port
        for port in self.container_obj.attrs['NetworkSettings']['Ports'].keys():
            if port == '6543/tcp':
                continue
            return self.container_obj.attrs['NetworkSettings']['Ports'][port][0]['HostPort']

    def get_host(self):
        return self.container_obj.attrs['NetworkSettings']['IPAddress']

    def check(self):
        return True

    def run(self):
        docker_client = docker.from_env(version=self.docker_version)

        # Create a new one
        container = docker_client.containers.run(
            image=self.image,
            **self.get_image_options()
        )
        ident = container.id
        count = 1

        self.container_obj = docker_client.containers.get(ident)

        opened = False

        print(f'starting {self.name}')
        while count < 30 and not opened:
            if count > 0:
                sleep(1)
            count += 1
            try:
                self.container_obj = docker_client.containers.get(ident)
            except docker.errors.NotFound:
                print(f'Container not found for {self.name}')
                continue
            if self.container_obj.status == 'exited':
                logs = self.container_obj.logs()
                self.stop()
                raise Exception(f'Container failed to start {logs}')

            if self.container_obj.attrs['NetworkSettings']['IPAddress'] != '':
                if os.environ.get('TESTING', '') == 'jenkins':
                    self.host = self.container_obj.attrs['NetworkSettings']['IPAddress']
                else:
                    self.host = 'localhost'

            if self.host != '':
                opened = self.check()
        if not opened:
            logs = self.container_obj.logs()
            self.stop()
            raise Exception(f'Could not start {self.name}: {logs}')
        print(f'{self.name} started')
        return self.host, self.get_port()

    def stop(self):
        if self.container_obj is not None:
            try:
                self.container_obj.kill()
            except docker.errors.APIError:
                pass
            try:
                self.container_obj.remove(v=True, force=True)
            except docker.errors.APIError:
                pass
