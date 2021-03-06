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

from hatchet import CCTree, HPCTDBReader

modules = ['cpi',
           '/collab/usr/global/tools/hpctoolkit/chaos_5_x86_64_ib/'
           'hpctoolkit-2017-03-16/lib/hpctoolkit/ext-libs/libmonitor.so.0.0.0',
           '/usr/local/tools/mvapich2-intel-debug-2.2/lib/libmpi.so.12.0.5',
           '/lib64/libc-2.12.so',
           '/usr/lib64/libpsm_infinipath.so.1.14']

src_files = ['./src/cpi.c',
             '<unknown file>',
             '/tmp/dpkg-mkdeb.gouoc49UG7/src/mvapich/src/build/../src/mpi/'
             'init/init.c',
             '/tmp/dpkg-mkdeb.gouoc49UG7/src/mvapich/src/build/../src/mpi/'
             'init/initthread.c',
             '/tmp/dpkg-mkdeb.gouoc49UG7/src/mvapich/src/build/../src/mpid/'
             'ch3/src/mpid_init.c',
             '/tmp/dpkg-mkdeb.gouoc49UG7/src/mvapich/src/build/../src/mpid/'
             'ch3/channels/psm/src/mpidi_calls.c',
             '/tmp/dpkg-mkdeb.gouoc49UG7/src/mvapich/src/build/../src/mpid/'
             'ch3/channels/psm/src/psm_entry.c',
             '/tmp/dpkg-mkdeb.gouoc49UG7/src/mvapich/src/build/../src/mpi/'
             'init/finalize.c',
             '/tmp/dpkg-mkdeb.gouoc49UG7/src/mvapich/src/build/../src/mpid/'
             'ch3/src/mpid_finalize.c',
             '/tmp/dpkg-mkdeb.gouoc49UG7/src/mvapich/src/build/../src/mpid/'
             'ch3/channels/psm/src/psm_exit.c',
             'interp.c',
             '<unknown file>']

procedures = ['main',
              '<program root>',
              'MPI_Init',
              'pthread_create',
              'MPI_Finalize',
              'PMPI_Init',
              'MPIR_Init_thread',
              'MPID_Init',
              'MPIDI_CH3_Init',
              'MPIDI_CH3_Finalize',
              'psm_doinit',
              'PMPI_Finalize',
              'MPID_Finalize',
              'psm_dofinalize',
              '__GI_sched_yield',
              '<unknown procedure>']


def test_cctree(calc_pi_hpct_db):
    """Sanity test a CCTree object wtih known data."""

    tree = CCTree(str(calc_pi_hpct_db), 'hpctoolkit')

    assert len(tree.load_modules) == 5
    assert len(tree.src_files) == 12
    assert len(tree.procedure_names) == 16
    assert all(lm in tree.load_modules.values() for lm in modules)
    assert all(sf in tree.src_files.values() for sf in src_files)
    assert all(pr in tree.procedure_names.values() for pr in procedures)

    # make sure every node has dummy data.
    for node in tree.traverse():
        for i in range(0, tree.num_metrics):
            for j in range(0, 3):
                assert node.metrics[i][j] >= 0.0


def test_read_calc_pi_database(calc_pi_hpct_db):
    """Sanity check the HPCT database reader by examining a known input."""
    dbr = HPCTDBReader(str(calc_pi_hpct_db))
    dbr.fill_tables()

    assert len(dbr.load_modules) == 5
    assert len(dbr.src_files) == 12
    assert len(dbr.procedure_names) == 16
    assert all(lm in dbr.load_modules.values() for lm in modules)
    assert all(sf in dbr.src_files.values() for sf in src_files)
    assert all(pr in dbr.procedure_names.values() for pr in procedures)
