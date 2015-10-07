#! /usr/bin/python
import os
import sys
import unittest
import logging

srcDir = os.path.abspath('../src/osm')
sys.path.insert(1, srcDir)
import pyosm

log = logging.getLogger(__name__)

class OSMXMLFileTests(unittest.TestCase):
    def setUp(self):
        self.osm_file = 'osmfiles/multipolygon1.osm'
        self.osm = pyosm.OSMXMLFile(self.osm_file)
    
    def tearDown(self):
        pass

    def test_osm_objects(self):
        self.osm.statistic()
        r = list(self.osm.relations.values())[-1]
        log.info('Single relation representation: %s', r)
        w = list(self.osm.ways.values())[-1]
        log.info('\nSingle way representation: %s', w)
        n = list(self.osm.nodes.values())[1]
        log.info('Single node representation: %s', n)
 
        log.info('Nodes of a Way: %s', w.nodes)
        log.info('Nodeids of a Way: %s', w.nodeids)

        log.info('Member Data of a Relation: %s', r.member_data)
        log.info('Members of a Relation: %s', r.members)
    
    def test_osm_itemgetter(self):
        log.info('relation item test:')
        r = list(self.osm.relations.values())[0] # get first relation
        for it in ['id','members','member_data','tags','bbox']:
            log.info('  %s=%s', it, r[it])
        log.info('way item test:')
        w = list(self.osm.ways.values())[0] # get first way
        for it in ['id','nodes','nodeids','tags','bbox']:
            log.info('  %s=%s', it, w[it])
        log.info('node item test:')
        n = list(self.osm.nodes.values())[0] # get first node
        for it in ['id','lat', 'lon','tags']:
            log.info('  %s=%s', it, n[it])
    
    def test_merge_write(self):
        osm2 = pyosm.OSMXMLFile(filename='osmfiles/josm_download.osm')
        log.info('osm2 stat befor merge')
        osm2.statistic()
        osm2.merge(self.osm)
        log.info('osm2 stat after merge')
        osm2.statistic()
        osm2.write('testoutput/result_merge_write.osm')
        
    def test_geometry(self):
        log.info('geometry tests:')
        w = list(self.osm.ways.values())[0] # get first way
        log.info('  distance way0: %f' % w.distance())
        log.info('  bbox way0: %s' % str(w.bbox()))
        r = list(self.osm.relations.values())[0] # get first relation        
        log.info('  distance rel0: %f' % r.distance())
        log.info('  bbox rel0: %s' % str(r.bbox()))
        germany = pyosm.OSMXMLFile('osmfiles/germany_borders.osm')
        rb = germany.relations[1111111]
        log.info('  border bbox %s' % str(rb.bbox()))
        log.info('  border bbox %s' % str(rb.bbox(recursive=True)))
        log.info('  border length %f' % rb.distance())
        log.info('  border length recursive %f' % rb.distance(recursive=True))
        log.info('  border length recursive %f' % rb.distance(recursive=True, roles=['outer','']))
        

if __name__ == '__main__':
    if not os.path.exists('testoutput'):
        os.mkdir('testoutput')
    logging.basicConfig(level=logging.INFO)
    unittest.main()