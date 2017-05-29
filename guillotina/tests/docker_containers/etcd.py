from guillotina.tests.docker_containers.base import BaseImage


class ETCD(BaseImage):
    label = 'etcd'
    image = 'quay.io/coreos/etcd:v3.2.0-rc.0'
    to_port = from_port = 2379
    image_options = BaseImage.image_options.copy()
    image_options.update(dict(
        mem_limit='200m',
        command=' '.join([
            '/usr/local/bin/etcd',
            '--data-dir /etcd-data',
            '--listen-client-urls http://0.0.0.0:2379',
            '--advertise-client-urls http://0.0.0.0:2379',
            '--listen-peer-urls http://0.0.0.0:2380',
            '--initial-advertise-peer-urls http://0.0.0.0:2380',
            '--initial-cluster my-etcd-1=http://0.0.0.0:2380',
            '--initial-cluster-token my-etcd-token',
            '--initial-cluster-state new',
            '--auto-compaction-retention 1'
        ])
    ))


image = ETCD()
