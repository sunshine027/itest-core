# vim: set sw=4 ts=4 ai et:
import os
import cgi
import json
import datetime
from collections import defaultdict

from itest.conf import settings
from itest.utils import now

from mako.lookup import TemplateLookup

CWD = os.path.dirname(os.path.abspath(os.path.relpath(__file__)))
TEMPLATE_PATH = os.path.join(CWD, 'template')


class HTMLReport(object):

    def __init__(self, status):
        self.status = status

    def format(self, string, *args):
        trans = lambda i: cgi.escape(i) if isinstance(i, basestring) else i
        return string % tuple([trans(i) for i in args])

    def issue_link(self, issue):
        if issue[0].lower().startswith('c'):
            return "https://otctools.jf.intel.com/review/#/c/%s" % issue[1]

        return "https://otctools.jf.intel.com/pm/issues/%s" % issue[1]


    def _generate(self):
        '''Collect test results and generate a html report'''
        comp2issues = defaultdict(set)
        issue2cases = defaultdict(list)
        for case in self.status.cases:
            issue = case['issue']
            if issue:
                comp = case['component']
                for item in issue.items():
                    comp2issues[comp].add(item)
                    issue2cases[item].append(case)
        data = {'status': self.status,
                'comp2issues': comp2issues,
                'issue_link': self.issue_link,
                'issue2cases': issue2cases,
                'basename': os.path.basename,
                'settings': settings,
                }

        return self._render(data)

    def _render(self, data):
        data.update(settings.REPORT_CONTEXT)

        template_dirs = [TEMPLATE_PATH]
        fname = os.path.join(settings.ENV_PATH, settings.REPORT_TEMPLATE_FILE)
        if os.path.exists(fname):
            path = os.path.dirname(fname)
            template_dirs.insert(0, path)
            tpl = os.path.basename(fname)
        else:
            tpl = 'default.html'

        lookup = TemplateLookup(directories=template_dirs,
                                output_encoding='utf-8')
        template = lookup.get_template(tpl)
        return template.render(**data)

    def generate(self, silent=False):
        html = self._generate()
        fname = "%s/report.html" % self.status.start['log_path']
        with open(fname, "w") as f:
            f.write(html)

        if not silent:
            print
            print 'HTML report was generated at:', fname


class StatusInfo(object):

    def __init__(self):
        self.cases = []
        self.complete = False
        self.env = None
        self.components = None
        self.failed = None
        self.start = None
        self.cost = None
        self.done = None
        self.deps = None
        self.total = None
        self.comp2cases = None
        self.cost_seconds = None

    def update(self, item):
        getattr(self, 'do_'+item['type'])(item)

    def do_start(self, item):
        self.start = item
        self.env = self.start['env']
        self.deps = self.start['deps']

    def do_case(self, item):
        item['cost_time_str'] = datetime.timedelta(seconds=item['cost_time'])
        self.cases.append(item)

    def do_done(self, item):
        if self.complete:
            return
        self.complete = True
        self.done = item

    def calculate(self):
        self.cal_cost()
        self.cal_cases()

    def cal_cost(self):
        stime = datetime.datetime.strptime(self.start['start_time'],
                                           '%Y-%m-%d %H:%M:%S')
        if self.complete:
            etime = datetime.datetime.strptime(self.done['end_time'],
                                               '%Y-%m-%d %H:%M:%S')
        else:
            etime = datetime.datetime.now()

        td = etime - stime
        if hasattr(td, 'total_seconds'): # new in py2.7
            total = td.total_seconds()
        else:
            total = td.seconds + td.days * 24 * 3600

        self.cost_seconds = int(total)
        self.cost = str(datetime.timedelta(seconds=self.cost_seconds))

    def cal_cases(self):
        components = {}
        comp2cases = {}
        failed = []
        for case in self.cases:
            comp = case['component']
            if comp not in components:
                components[comp] = {'pass': 0,
                                    'failed': 0,
                                    }
                comp2cases[comp] = []

            comp2cases[comp].append(case)
            cnt = components[comp]

            if case['exit_code'] == 0:
                cnt['pass'] += 1
                case['is_pass'] = True
            else:
                cnt['failed'] += 1
                failed.append(case)
                case['is_pass'] = False

        total = {'pass': 0,
                 'failed': 0,
                 }
        for cnt in components.values():
            for k, v in cnt.iteritems():
                total[k] += v
            cnt['total'] = sum(cnt.values())
        total['total'] = sum(total.values())

        self.total = total
        self.components = components
        self.comp2cases = comp2cases
        self.failed = failed


class StatusFile(object):
    '''Status and stat info of running tests'''

    def __init__(self, fname):
        self.fname = fname

    def log(self, data):
        msg = '|'.join([now(), json.dumps(data)]) + os.linesep
        with open(self.fname, 'a') as fp:
            fp.write(msg)

    def load(self):
        info = StatusInfo()
        with open(self.fname) as fp:
            for line in fp:
                _, data = line.split('|', 1)
                info.update(json.loads(data))
        info.calculate()
        return info
