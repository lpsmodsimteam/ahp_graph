"""Class to simplify testing."""


class test():
    """Class to format test output."""

    FAIL = '\033[0;31mFAIL\033[0m'
    PASS = '\033[0;32mPASS\033[0m'
    verbose = False

    def __init__(self, name: str) -> None:
        """Init a test with a name."""
        self.name = f"\033[0;34m{name}\033[0m"
        self.fail = False
        if self.verbose:
            print(f'\t{self.name}:')

    def test(self, test: bool, string: str) -> None:
        """Print the results of the test."""
        if test:
            if self.verbose:
                print(f'\t\t{self.PASS} - {string}')
        else:
            self.fail = True
            if self.verbose:
                print(f'\t\t{self.FAIL} - {string}')

    def finish(self) -> bool:
        """Print final test results and return any failures."""
        if self.fail:
            print(f'\t{self.name} - {self.FAIL}')
        else:
            print(f'\t{self.name} - {self.PASS}')
        return self.fail
