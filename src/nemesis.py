import sys
from clint.textui import puts, puts_err, colored, columns

import blockade.cli as cli
from blockade.errors import BlockadeError
from blockade.errors import InsufficientPermissionsError
from blockade.errors import NotInitializedError


class Nemesis():
    def __init__(self, nodes):
        self.nodes = nodes
        try:
            self.status()
        except NotInitializedError as ne:
            #    'No blockade exists in this context'
            for n in self.nodes:
                self._blockade_cmd(['add', n])
            self.status()

    def partition(self, nodes):
        '''assume nodes is an array'''
        self._blockade_cmd(['partition'] + nodes)

    def heal(self):
        self._blockade_cmd(['join'])

    def status(self):
        self._blockade_cmd(['status'])

    def _blockade_cmd(self, args=None):
        if sys.version_info >= (3, 2) and sys.version_info < (3, 3):
            puts_err(colored.red("\nFor Python 3, Flask requires Python >= 3.3\n"))
            sys.exit(1)

        parser = cli.setup_parser()
        opts = parser.parse_args(args=args)
        try:
            # don't bother pinging docker for a version command
            if opts.func != cli.cmd_version:
                cli.check_docker()

            opts.func(opts)
        except InsufficientPermissionsError as e:
            puts_err(colored.red("\nInsufficient permissions error:\n") + str(e) + "\n")
        except BlockadeError as e:
            puts_err(colored.red("\nError:\n") + str(e) + "\n")
            raise e
        except KeyboardInterrupt:
            puts_err(colored.red("Caught Ctrl-C. exiting!"))
        except:
            puts_err(
                colored.red("\nUnexpected error! This may be a Blockade bug.\n"))
            traceback.print_exc()
            raise Error()


if __name__ == '__main__':
    '''demo'''

    nodes = ['n%i' % n for n in range(1, 4)]
    nemesis = Nemesis(nodes)

    nemesis.status()
    try:
        nemesis.partition(['n1,n2', 'n3'])
        nemesis.status()
    finally:
        nemesis.heal()

    nemesis.status()
