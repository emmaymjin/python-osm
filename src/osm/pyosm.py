#!/usr/bin/python
#
# Original version by Rory McCann (http://blog.technomancy.org/)
# Modifications by Christoph Lupprich (http://www.stopbeingcarbon.com)
#
import xml.sax
import numpy
import logging
log = logging.getLogger("pyosm")


#################### CLASSES
class Node(object):
    __slot__ = ['id', 'lat', 'lon','__attrs', '__tags']
    ATTRIBUTES = set(['id', 'timestamp', 'uid', 'user', 'visible', 'version', 'lat', 'lon', 'changeset'])

    def __init__(self, attrs, tags=None, load_tags=True, load_attrs=True):
        self.id = int(attrs.pop('id'))
        self.lon = float(attrs.pop('lon'))
        self.lat = float(attrs.pop('lat'))
        if load_attrs:
            self.__attrs = attrs
        else:
            self.__attrs = None
        if load_tags:
            self.__tags = tags
        else:
            self.__tags = None

    def __getattr__(self, name):
        if name in self.ATTRIBUTES:
            return self.__attrs[name]
        elif name == 'tags':
            return self.__tags

    def __cmp__(self, other):
        cmp_ref = cmp(self.tags.get('ref',''), other.tags.get('ref',''))
        if cmp_ref:
            return cmp_ref
        cmp_name = cmp(self.tags.get('name',''), other.tags.get('name',''))
        if cmp_name:
            return cmp_name
        return cmp(self.id, other.id)

    def attributes(self):
        d = {'id': repr(self.id),
             'lat': repr(self.lat),
             'lon': repr(self.lon)}
        if self.__attrs:
            d.update(self.__attrs)
        return d

    def __repr__(self):
        return "Node(attrs=%r, tags=%r)" % (self.attributes(), self.__tags)


class Way(object):
    __slot__ = ['id', '__attrs','__tags','__nodes', 'osm_parent']
    ATTRIBUTES = set(['id', 'timestamp', 'uid', 'user', 'visible', 'version', 'changeset'])

    def __init__(self, attrs, tags=None, nodes=None, osm_parent=None, load_tags=True, load_attrs=True, load_nodes=True):
        self.id = int(attrs.pop('id'))
        self.osm_parent = osm_parent
        if load_nodes:
            self.__nodes = numpy.asarray(nodes, dtype='int32')
        else:
            self.__nodes = None
        if load_attrs:
            self.__attrs = attrs
        else:
            self.__attrs = None
        if load_tags:
            self.__tags = tags
        else:
            self.__tags = None

    def __getattr__(self, name):
        if name == 'nodes':
            return self.osm_parent.get_nodes(self.__nodes)
        elif name == 'nodeids':
            return list(self.__nodes)
        elif name == 'tags':
            return self.__tags
        elif name in self.ATTRIBUTES:
            return self.__attrs[name]

    def __cmp__(self, other):
        cmp_ref = cmp(self.tags.get('ref',''), other.tags.get('ref',''))
        if cmp_ref:
            return cmp_ref
        cmp_name = cmp(self.tags.get('name',''), other.tags.get('name',''))
        if cmp_name:
            return cmp_name
        return cmp(self.id, other.id)

    def attributes(self):
        d = {'id': repr(self.id)}
        if self.__attrs:
            d.update(self.__attrs)
        return d

    def __repr__(self):
        return "Way(attrs=%r, tags=%r, nodes=%r)" % (self.attributes(), self.__tags, list(self.__nodes))


class Relation(object):
    __slot__ = ['id', '__attrs','__tags','__members', 'osm_parent']
    ATTRIBUTES = set(['id', 'timestamp', 'uid', 'user', 'visible', 'version', 'changeset'])

    def __init__(self, attrs, tags=None, members=None, osm_parent=None, load_tags=True, load_attrs=True, load_members=True):
        self.id = int(attrs.pop('id'))
        self.osm_parent = osm_parent
        if load_members:
            self.__members = numpy.array(members, dtype=[('type','|S1'),('id','<i4'),('role',numpy.object_)])
        else:
            self.__members = None
        if load_attrs:
            self.__attrs = attrs
        else:
            self.__attrs = None
        if load_tags:
            self.__tags = tags
        else:
            self.__tags = None

    def __getattr__(self, name):
        if name == 'members':
            return self.osm_parent.get_members(self.__members)
        elif name == 'member_data':
            return list(self.__members)
        elif name == 'tags':
            return self.__tags
        elif name in self.ATTRIBUTES:
            return self.__attrs[name]

    def __cmp__(self, other):
        cmp_ref = cmp(self.tags.get('ref',''), other.tags.get('ref',''))
        if cmp_ref:
            return cmp_ref
        cmp_name = cmp(self.tags.get('name',''), other.tags.get('name',''))
        if cmp_name:
            return cmp_name
        return cmp(self.id, other.id)

    def attributes(self):
        d = {'id': repr(self.id)}
        if self.__attrs:
            d.update(self.__attrs)
        return d

    def __repr__(self):
        members = [(a,b,c) for a,b,c in self.__members]
        return "Relation(attrs=%r, tags=%r, members=%r)" % (self.attributes(), self.__tags, members)


class OSMXMLFile(object):
    def __init__(self, filename=None, content=None, options={}):
        self.filename = filename

        self.nodes = {}
        self.ways = {}
        self.relations = {}
        self.osmattrs = {'version':'0.6'}
        self.options = {'load_nodes': True,
                        'load_ways': True,
                        'load_relations': True,
                        'load_way_nodes': True,
                        'load_relation_members': True,
                        'filterfunc': False}
        self.options.update(options)
        if filename:
            self.__parse()
        elif content:
            self.__parse(content)
    
    def get_members(self, members):
        mlist = []
        for mtype, mid, mrole in members:
            if mtype == 'r':
                obj = self.realtions[mid]
            elif mtype == 'w':
                obj = self.ways[mid]
            else:
                obj = self.nodes[mid]
            mlist.append((obj, mrole))
        return mlist

    def get_nodes(self, nodes):
        return [ self.nodes[nid] for nid in nodes ]

    def __parse(self, content=None):
        """Parse the given XML file"""
        handler = OSMXMLFileParser(self)
        if content:
            xml.sax.parseString(content, handler)
        else:
            xml.sax.parse(self.filename, handler)

    def merge(self, osmxmlfile, update=True):
        for id, node in osmxmlfile.nodes.items():
            self.nodes[id] = node
        for id, way in osmxmlfile.ways.items():
            way.osm_parent = self
            self.ways[id] = way
        for id, relation in osmxmlfile.relations.items():
            relation.osm_parent = self
            self.relations[id] = relation

    def write(self, fileobj):
        if type(fileobj) == str:
            fileobj = open(fileobj, 'wt')
        handler = xml.sax.saxutils.XMLGenerator(fileobj, 'UTF-8')
        handler.startDocument()
        handler.startElement('osm', self.osmattrs)
        handler.characters('\n')

        for nodeid in sorted(self.nodes):
            node = self.nodes[nodeid]
            handler.startElement('node', node.attributes())
            for name, value in node.tags.items():
                handler.characters('  ')
                handler.startElement('tag', {'k': name, 'v': value})
                handler.endElement('tag')
                handler.characters('\n')
            handler.endElement('node')
            handler.characters('\n')

        for wayid in sorted(self.ways):
            way = self.ways[wayid]
            handler.startElement('way', way.attributes())
            handler.characters('\n')
            for node in way.nodes:
                handler.characters('  ')
                handler.startElement('nd', {'ref': str(node.id)})
                handler.endElement('nd')
                handler.characters('\n')
            for name, value in way.tags.items():
                handler.characters('  ')
                handler.startElement('tag', {'k': name, 'v': value})
                handler.endElement('tag')
                handler.characters('\n')
            handler.endElement('way')
            handler.characters('\n')
            
        for relationid in sorted(self.relations):
            relation = self.relations[relationid]
            handler.startElement('relation', relation.attributes())
            for mtype, mid, mrole in relation.member_data:
                obj_type = {'n': 'node', 'w': 'way', 'r': 'relation'}[mtype]
                handler.characters('  ')
                handler.startElement('member', {'type': obj_type, 'ref': str(mid), 'role': mrole})
                handler.endElement('member')
                handler.characters('\n')
            for name, value in relation.tags.items():
                handler.characters('  ')
                handler.startElement('tag', {'k': name, 'v': value})
                handler.endElement('tag')
                handler.characters('\n')
            handler.endElement('relation')
            handler.characters('\n')

        handler.endElement('osm')
        handler.endDocument()

    def statistic(self):
        """Print a short statistic about the osm object"""
        print("Filename: %s" % self.filename)
        print("  Nodes    : %i" % len(self.nodes))
        print("  Ways     : %i" % len(self.ways))
        print("  Relations: %i" % len(self.relations))


class OSMXMLFileParser(xml.sax.ContentHandler):
    def __init__(self, containing_obj):
        self.containing_obj = containing_obj
        self.load_nodes = containing_obj.options['load_nodes']
        self.load_ways = containing_obj.options['load_ways']
        self.load_relations = containing_obj.options['load_relations']
        self.load_way_nodes = containing_obj.options['load_way_nodes']
        self.load_relation_members = containing_obj.options['load_relation_members']
        self.filterfunc = containing_obj.options['filterfunc']

        self.obj_attrs = None
        self.obj_tags = []
        self.way_nodes = []
        self.rel_members = []
        self.osm_attrs = None

    def startElement(self, name, attrs):
        if name == 'node':
            self.obj_attrs = dict(attrs)
            
        elif name == 'way':
            self.obj_attrs = dict(attrs)
            
        elif name == "relation":
            self.obj_attrs = dict(attrs)

        elif name == 'tag':
            self.obj_tags.append((attrs['k'], attrs['v']))
            
        elif name == "nd":
            self.way_nodes.append(attrs['ref'])
          
        elif name == "member":
            self.rel_members.append((attrs['type'][0],attrs['ref'],attrs['role']))
          
        elif name == "osm":
            self.osm_attrs = dict(attrs)

        elif name == "bound":
            pass

        else:
            log.warn("Don't know element %s", name)

    def endElement(self, name):
        if name == "node":
            if self.load_nodes:
                curr_node = Node(self.obj_attrs, dict(self.obj_tags))
                if self.filterfunc:
                    if self.filterfunc(curr_node):
                        self.containing_obj.nodes[curr_node.id] = curr_node
                else:
                    self.containing_obj.nodes[curr_node.id] = curr_node
            self.obj_attrs = None
            self.obj_tags = []
 
        elif name == "way":
            if self.load_ways:
                curr_way = Way(self.obj_attrs, dict(self.obj_tags), self.way_nodes, osm_parent=self.containing_obj)
                if self.filterfunc:
                    if self.filterfunc(curr_way):
                        self.containing_obj.ways[curr_way.id] = curr_way
                else:
                    self.containing_obj.ways[curr_way.id] = curr_way
            self.obj_attrs = None
            self.obj_tags = []
            self.way_nodes = []
        
        elif name == "relation":
            if self.load_relations:
                curr_rel = Relation(self.obj_attrs, dict(self.obj_tags), self.rel_members, osm_parent=self.containing_obj)
                if self.filterfunc:
                    if self.filterfunc(self.curr_relation):
                        self.containing_obj.relations[curr_rel.id] = curr_rel
                else:
                    self.containing_obj.relations[curr_rel.id] = curr_rel
            self.obj_attrs = None
            self.obj_tags = []
            self.rel_members = []

        elif name == "osm":
            self.containing_obj.osmattrs = self.osm_attrs
            self.curr_osmtags = None


#################### FUNCTIONS


#################### MAIN            
if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    for filename in sys.argv[1:]:
        osm = OSMXMLFile(filename)
        osm.statistic()