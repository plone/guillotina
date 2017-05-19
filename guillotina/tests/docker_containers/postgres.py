from guillotina.tests.docker_containers.base import BaseImage

import psycopg2


class Postgresql(BaseImage):
    label = 'postgresql'
    image = 'postgres:9.6'
    to_port = from_port = 5432
    image_options = BaseImage.image_options.copy()
    image_options.update(dict(
        environment={
            'POSTGRES_PASSWORD': '',
            'POSTGRES_DB': 'guillotina',
            'POSTGRES_USER': 'postgres'
        }
    ))

    def check(self, host):
        try:
            conn = psycopg2.connect("dbname=guillotina user=postgres host=%s port=5432" % host)  # noqa
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            cur.fetchone()
            cur.close()
            conn.close()
            return True
        except: # noqa
            conn = None
            cur = None
        return False


image = Postgresql()
