from guillotina.tests.docker_containers.base import BaseImage

import random


image_name = 'test-etcd-{}'.format(random.randint(0, 1000))


class ETCD(BaseImage):
    name = 'etcd'
    image = 'quay.io/coreos/etcd:v3.2.0-rc.0'
    port = 2379

    def get_image_options(self):
        image_options = super().get_image_options()
        image_options.update(dict(
            mem_limit='200m',
            name=image_name,
            command=' '.join([
                '/usr/local/bin/etcd',
                '--name {}'.format(image_name),
                '--data-dir /etcd-data',
                '--listen-client-urls http://0.0.0.0:2379',
                '--advertise-client-urls http://0.0.0.0:2379',
                '--listen-peer-urls http://0.0.0.0:2380',
                '--initial-advertise-peer-urls http://0.0.0.0:2380',
                '--initial-cluster {}=http://0.0.0.0:2380'.format(image_name),
                '--initial-cluster-token my-etcd-token',
                '--initial-cluster-state new',
                '--auto-compaction-retention 1'
            ])
        ))
        return image_options


image = ETCD()
