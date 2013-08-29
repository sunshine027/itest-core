import random


class TestSuite(object):
    '''A set of test cases'''

    def __init__(self, tests=()):
        self._tests = set(tests)

    def __iter__(self):
        return iter(self._sorted(self._tests))

    @property
    def count(self):
        return sum([ test.count for test in self ])

    def add_test(self, test):
        if hasattr(test, '__iter__'):
            for t in test:
                self.add_test(t)
        else:
            self._tests.add(test)

    def add_tests(self, tests):
        for test in tests:
            self.add_test(test)

    def run(self, result, *args, **kw):
        for test in self:
            if result.should_stop:
                break
            test.run(result, *args, **kw)
        return result

    def _sorted(self, tests):
        tests2 = list(tests)
        random.shuffle(tests2)
        return tests2
