from guillotina.commands import Command
from guillotina.content import load_cached_schema
from guillotina.documentation.generate import process_command_file


class APIGenCommand(Command):
    description = 'Generate APIDoc data'
    hide = True

    def get_parser(self):
        parser = super(APIGenCommand, self).get_parser()
        parser.add_argument('-i', '--input', nargs='?', help='Input filename')
        parser.add_argument('-e', '--endpoint', nargs='?',
                            default='http://localhost:8080', help='Guillotina Endpoint')
        parser.add_argument('-o', '--output', nargs='?',
                            default='./', help='Output path')
        return parser

    async def run(self, arguments, settings, app):
        load_cached_schema()
        process_command_file(
            arguments.input,
            arguments.endpoint,
            arguments.output
        )
