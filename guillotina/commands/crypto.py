from guillotina.commands import Command
from jwcrypto import jwk

import logging


logger = logging.getLogger("guillotina")


class CryptoCommand(Command):
    description = """Generate jwk keys"""

    def get_parser(self):
        parser = super().get_parser()
        parser.add_argument("--key-size", type=int, default=256, dest="key_size", help="Key size")
        parser.add_argument("--key-type", default="oct", dest="key_type", help="Key type")
        return parser

    async def run(self, arguments, settings, app):
        key = jwk.JWK.generate(kty=arguments.key_type, size=arguments.key_size)
        print(key.export())
