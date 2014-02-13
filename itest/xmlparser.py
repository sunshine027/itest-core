"""
Parser of XML format of case file
"""
import xml.etree.ElementTree as ET


class Parser(object):
    """
    The XML case parser
    """

    def parse(self, xmldoc):
        """
        Returns a dict represent a case
        """
        data = {}
        root = ET.fromstring(xmldoc)
        for child in root:
            method = '_on_' + child.tag
            if hasattr(self, method):
                value = getattr(self, method)(child)
                data[child.tag] = value
        return data

    def _text(self, element):
        """
        Returns stripped text of `element`
        """
        return element.text.strip() if element.text else ''

    _on_formatversion = _text
    _on_summary = _text
    _on_setup = _text
    _on_steps = _text
    _on_teardown = _text

    def _on_tracking(self, element):
        """
        Subelement can be a Gerrit `change` or a Redmine `ticket`.
        <tracking>
          <change>90125</change>
          <ticket>5150</ticket>
        </tracking>
        """
        return [(child.tag, self._text(child))
                for child in element
                if child.tag in ('change', 'ticket')]

    def _on_qa(self, element):
        """
        A seqence of <prompt> and <asnwer>.
        <qa>
          <prompt>Are you sure [N/y]?</prompt>
          <answer>y</answer>
        </qa>
        """
        data = []
        state = 0
        for node in element:
            if state == 0:
                if node.tag == 'prompt':
                    prompt = self._text(node)
                    state = 1
                else:
                    raise Exception("Case syntax error: expects <prompt> "
                                    "rather than %s" % node.tag)
            elif state == 1:
                if node.tag == 'answer':
                    answer = self._text(node)
                    data.append((prompt, answer))
                    state = 0
                else:
                    raise Exception("Case syntax error: expects <answer> "
                                    "rather than %s" % node.tag)
        if state == 1:
            raise Exception("Case syntax error: expects <answer> rather than "
                            "closing")
        return data

    def _on_conditions(self, element):
        """
        Platform white list and black list
        <conditions>
          <whitelist>
            <platform>OpenSuse-64bit</platform>
            <platform>Ubuntu12.04</platform>
          </whitelist>
          <blacklist>
            <platform>Fedora19-x86_64</platform>
          </blacklist>
        </conditions>
        """
        def _platforms(key):
            return [self._text(n)
                    for n in element.findall('./%s/platform' % key)]
        return {
            'whitelist': _platforms('whitelist'),
            'blacklist': _platforms('blacklist'),
            }

    def _on_fixtures(self, element):
        """
        <fixtures>
            <copy src="conf/a.conf" />
            <template src="conf/b.conf" target="newdir/c.conf" />
            <content target="c.conf">conf content</content>
        </fixtures>
        """
        return [{
                'type': i.tag,
                'src': i.get('src'),
                'target': i.get('target'),
                'text': self._text(i),
                } for i in element if i.tag in ('copy', 'template', 'content')]
