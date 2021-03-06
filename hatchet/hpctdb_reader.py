##############################################################################
# Copyright (c) 2017, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# Written by Abhinav Bhatele <bhatele@llnl.gov>.
# LLNL-CODE-741008. All rights reserved.
#
# This file is part of Hatchet. For details, see:
# https://github.com/LLNL/hatchet
# Please also read the LICENSE file for the MIT License notice.
##############################################################################

import glob
import struct
import numpy as np

from ccnode import CCNode

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

src_file = 0


class HPCTDBReader:
    """
    Read in the various sections of an HPCToolkit experiment.xml file
    and metric-db files
    """

    def __init__(self, dir_name):
        self.dir_name = dir_name

        root = ET.parse(self.dir_name + '/experiment.xml').getroot()
        self.loadmodule_table = root.iter('LoadModuleTable').next()
        self.file_table = root.iter('FileTable').next()
        self.procedure_table = root.iter('ProcedureTable').next()
        self.callpath_profile = root.iter('SecCallPathProfileData').next()

        metricdb_files = glob.glob(self.dir_name + '/*.metric-db')
        self.num_pes = len(metricdb_files)

        metricdb = open(metricdb_files[0], "rb")
        tag = metricdb.read(18)
        version = metricdb.read(5)
        endian = metricdb.read(1)

        if endian == 'b':
            self.num_nodes = struct.unpack('>i', metricdb.read(4))[0]
            self.num_metrics = struct.unpack('>i', metricdb.read(4))[0]

        metricdb.close()

        self.metrics = np.empty([self.num_metrics,
                                 self.num_nodes,
                                 self.num_pes])
        self.metrics_min = np.empty([self.num_metrics, self.num_nodes])
        self.metrics_avg = np.empty([self.num_metrics, self.num_nodes])
        self.metrics_max = np.empty([self.num_metrics, self.num_nodes])

        self.load_modules = {}
        self.src_files = {}
        self.procedure_names = {}


    def fill_tables(self):
        # create dicts of load modules, src_files and procedure_names
        for loadm in (self.loadmodule_table).iter('LoadModule'):
            self.load_modules[loadm.get('i')] = loadm.get('n')

        for filename in (self.file_table).iter('File'):
            self.src_files[filename.get('i')] = filename.get('n')

        for procedure in (self.procedure_table).iter('Procedure'):
            self.procedure_names[procedure.get('i')] = procedure.get('n')

        return self.load_modules, self.src_files, self.procedure_names

    def read_metricdb(self):
        metricdb_files = glob.glob(self.dir_name + '/*.metric-db')

        # assumes that glob returns a sorted order
        for pe, filename in enumerate(metricdb_files):
            metricdb = open(filename, "rb")
            metricdb.seek(32)
            arr = np.fromfile(metricdb, dtype=np.dtype('>f8'),
                              count=self.num_nodes * self.num_metrics)
            # inclusive time
            metric1 = arr[0::2]
            # exclusive time
            metric2 = arr[1::2]
            for i in range(0, len(metric1)):
                self.metrics[0][i][pe] = metric1[i]
                self.metrics[1][i][pe] = metric2[i]
            metricdb.close()

        # Also calculate min, avg, max metrics for each node
        self.metrics_min = np.amin(self.metrics, axis=2)
        self.metrics_avg = np.mean(self.metrics, axis=2)
        self.metrics_max = np.amax(self.metrics, axis=2)

        return self.metrics

    def create_cctree(self):
        self.fill_tables()
        self.read_metricdb()

        # parse the ElementTree to generate a calling context tree
        root = self.callpath_profile.findall('PF')[0]
        nid = int(root.get('i'))

        metrics = np.empty([self.num_metrics, 3])
        for i in range(0, self.num_metrics):
            metrics[i][0] = self.metrics_min[i][nid-1]
            metrics[i][1] = self.metrics_avg[i][nid-1]
            metrics[i][2] = self.metrics_max[i][nid-1]

        cct_root = CCNode(nid, root.get('s'), root.get('l'), metrics, 'PF',
                          self.procedure_names[root.get('n')], root.get('lm'),
                          root.get('f'))

        # start tree construction at the root
        self.parse_xml_children(root, cct_root)
        return cct_root

    def parse_xml_children(self, xml_node, ccnode):
        """ Parses all children of an XML node.
        """
        for xml_child in xml_node.getchildren():
            if xml_child.tag != 'M':
                self.parse_xml_node(xml_child, ccnode)

    def parse_xml_node(self, xml_node, cc_parent):
        """ Parses an XML node and its children recursively.
        """
        nid = int(xml_node.get('i'))

        metrics = np.empty([self.num_metrics, 3])
        for i in range(0, self.num_metrics):
            metrics[i][0] = self.metrics_min[i][nid-1]
            metrics[i][1] = self.metrics_avg[i][nid-1]
            metrics[i][2] = self.metrics_max[i][nid-1]

        global src_file
        xml_tag = xml_node.tag

        if xml_tag == 'PF' or xml_tag == 'Pr':
            name = self.procedure_names[xml_node.get('n')]
            src_file = xml_node.get('f')
            ccnode = CCNode(nid, xml_node.get('s'), xml_node.get('l'), metrics,
                            xml_tag, name, xml_node.get('lm'), src_file)
        elif xml_tag == 'L':
            src_file = xml_node.get('f')
            line = xml_node.get('l')
            name = "Loop@" + (self.src_files[src_file]).rpartition('/')[2] + ":" + line
            ccnode = CCNode(nid, xml_node.get('s'), line, metrics, xml_tag,
                            _name=name, _src_file=src_file)
        # elif xml_tag == 'C':
            # ccnode = CCNode(nid, xml_node.get('s'), xml_node.get('l'),
            #                 metrics, xml_tag)
        elif xml_tag == 'S':
            ccnode = CCNode(nid, xml_node.get('s'), xml_node.get('l'), metrics,
                            xml_tag, _src_file=src_file)

        if xml_tag == 'C' or (xml_tag == 'Pr' and
                              self.procedure_names[xml_node.get('n')] == ""):
            # do not add a node to the tree
            self.parse_xml_children(xml_node, cc_parent)
        else:
            cc_parent.add_child(ccnode)
            self.parse_xml_children(xml_node, ccnode)
