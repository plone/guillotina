from guillotina.commands import Command

import guillotina
import os
import sys


class CreateCommand(Command):
    description = 'Guillotina server runner'

    def make_app(self, settings):
        """
        We don't need an application object for this command...
        """

    def get_parser(self):
        parser = super(CreateCommand, self).get_parser()
        parser.add_argument('command',
                            help='`create` position command argument')
        parser.add_argument('--template', required=True,
                            help='Template to use to generate project',
                            choices=set(['application', 'configuration']))
        parser.add_argument('-w', '--overwrite', action='store_true',
                            dest='overwrite', help='Overwrite')
        parser.add_argument('-n', '--no-input', action='store_true',
                            dest='no_input', help='No input')
        parser.add_argument('-o', '--output', default='./',
                            dest='output', help='Output directory')
        return parser

    def run_cookie_cutter(self, arguments, tmpl_dir):
        try:
            from cookiecutter.main import cookiecutter
        except ImportError:
            sys.stderr.write(
                'You must have cookiecutter installed in order for the '
                'pcreate command to work.\n Use `pip install cookiecutter` '
                'to install cookiecutter.\n'
            )
            return 1
        cookiecutter(
            tmpl_dir,
            no_input=arguments.no_input,
            overwrite_if_exists=arguments.overwrite,
            output_dir=arguments.output)

    def run(self, arguments, settings, app):

        if not arguments.template:
            sys.stderr.write('You must provide a template to use.')
            return 1

        _dir = os.path.dirname(os.path.realpath(guillotina.__file__))
        cutter_dir = os.path.join(_dir, "cookiecutter")
        tmpl_dir = os.path.join(cutter_dir, arguments.template)

        if arguments.template in ('configuration', ):
            # special case where we are just copying a file over
            # right now, cookiecutter does not support this use-case
            file_path = os.path.join(tmpl_dir, 'file.tmpl')
            new_path = input('path [config.yaml]:') or 'config.yaml'
            # can eventually do some replacement here...
            with open(new_path, 'w') as new_fi:
                with open(file_path) as tmpl_fi:
                    new_fi.write(tmpl_fi.read())
        else:
            self.run_cookie_cutter(arguments, tmpl_dir)
