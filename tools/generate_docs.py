# -*- encoding:utf-8 -*-
import os

import attr
from ruamel import yaml
from boltons.dictutils import OMD

TOOLS_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/templates/'

house = u"\u2302"
BULLET = '*'

@attr.s(frozen=True)
class TagEntry(object):
    tag = attr.ib()
    tag_type = attr.ib()
    title = attr.ib()
    desc = attr.ib(default='')
    subtags = attr.ib(default=None, repr=False)
    supertag = attr.ib(default=None, repr=False)
    fq_tag = attr.ib(default=None)


@attr.s(frozen=True)
class Project(object):
    name = attr.ib()
    desc = attr.ib(default='')
    tags = attr.ib(default=())
    urls = attr.ib(default=())

    @classmethod
    def from_dict(cls, d):
        kwargs = dict(d)
        for k in list(kwargs):
            cur_urls = ()
            if not k.endswith('_url'):
                continue
            cur_urls += ((k[:-4], kwargs.pop(k)),)
            kwargs['urls'] = cur_urls
        return cls(**kwargs)


def _unwrap_dict(d):
    if not len(d) == 1:
        raise ValueError('expected single-member dict')
    return list(d.items())[0]


class ProjectList(object):
    def __init__(self, project_list, tagsonomy):
        self.project_list = []
        self.tagsonomy = tagsonomy

        self.tag_registry = OMD()
        self.tag_alias_map = OMD()
        for tag in self.tagsonomy['topic']:
            self.register_tag('topic', tag)

        for project in project_list:
            self.project_list.append(Project.from_dict(project))

    @classmethod
    def from_path(cls, path):
        data = yaml.safe_load(open(path))
        return cls(data['projects'], data['tagsonomy'])

    def register_tag(self, tag_type, tag_entry, tag_path=None):
        if isinstance(tag_entry, str):
            tag, tag_entry = tag_entry, {}
        else:
            tag, tag_entry = _unwrap_dict(tag_entry)
            tag_entry = dict(tag_entry)
        tag_entry['tag'] = tag
        tag_entry['tag_type'] = tag_type

        if not tag_entry.get('title'):
            tag_entry["title"] = tag.replace('_', ' ').title()

        subtags = []
        for subtag_entry in tag_entry.pop('subtags', []):
            st = self.register_tag(tag_type, subtag_entry,
                                   tag_path=(tag,) if not tag_path else tag_path + (tag,))
            subtags.append(st)
        tag_entry['subtags'] = tuple(subtags)

        if not tag_path:
            ret = TagEntry(**tag_entry)
        else:
            fq_tag = '.'.join(tag_path + (tag,))
            ret = TagEntry(supertag=tag_path, fq_tag=fq_tag, **tag_entry)
            # also register the fq version
            self.tag_registry[fq_tag] = attr.evolve(ret, tag=fq_tag, fq_tag=None)

        self.tag_registry[tag] = ret
        return ret

    def get_projects_by_topic(self):
        ret = OMD()
        for tag, tag_entry in self.tag_registry.items():
            if tag_entry.tag_type != 'topic':
                continue
            ret[tag_entry] = []
            for project in self.project_list:
                if tag in project.tags:
                    ret[tag_entry].append(project)
        return ret


_URL_LABEL_MAP = {'wp': 'Wikipedia'}


def _format_url_name(name):
    return _URL_LABEL_MAP.get(name, name.title())



def format_tag_text(project_map, tag_entry):
    lines = []
    append = lines.append

    def _format_tag(project_map, tag_entry, level=2):
        append('%s <a id="tag-%s" href="#tag-%s">%s</a>' %
               ('#' * level, tag_entry.tag, tag_entry.tag, tag_entry.title))
        append('')
        if tag_entry.desc:
            append(tag_entry.desc)
            append('')
        if tag_entry.subtags:
            append('')
            for subtag_entry in tag_entry.subtags:
                _format_tag(project_map, subtag_entry, level=level + 1)
                # * **Meld** - ([Home](#)|[Repo](#)|[Docs](#)) Description of Meld `(gtk, linux)`
            append('%s <a id="tag-%s-other" href="#tag-%s-other">Other %s projects</a>' %
                   ('#' * (level + 1), tag_entry.tag, tag_entry.tag, tag_entry.title))

        for project in project_map[tag_entry]:
            tmpl = '  {bullet} **{name}** - ({links}) {desc}'
            links = '|'.join(['[%s](%s)' % (_format_url_name(name), url) for name, url in project.urls])

            line = tmpl.format(bullet=BULLET, name=project.name, links=links, desc=project.desc)
            if len(project.tags) > 1:
                line += ' `(%s)`' % ', '.join(sorted([t for t in project.tags if t != tag_entry.tag]))
            lines.append(line)

        append('')
        return '\n'.join(lines)

    return _format_tag(project_map, tag_entry)


def main():
    plist = ProjectList.from_path('projects.yaml')
    readme_tmpl = open(TEMPLATES_PATH + '/README.tmpl.md').read()

    topic_map = plist.get_projects_by_topic()

    parts = []
    for tag_entry in topic_map:
        if tag_entry.supertag:
            continue
        if not topic_map[tag_entry]:
            continue
        text = format_tag_text(topic_map, tag_entry)
        parts.append(text)
    projects_by_topic = '\n'.join(parts)

    readme = readme_tmpl.replace('[PROJECTS_BY_TOPIC]', projects_by_topic)

    # from pprint import pprint
    #pprint(plist.tag_registry.todict())
    #pprint(plist.get_projects_by_topic(), compact=True, width=120)
    print(readme)
    import pdb;pdb.set_trace()


if __name__ == '__main__':
    main()
