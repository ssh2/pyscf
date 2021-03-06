#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

'''
Exact density fitting with Gaussian and planewaves
Ref:
'''

import numpy
from pyscf.pbc.df import df_jk
from pyscf.pbc.df import aft_jk

#
# Divide the Coulomb potential to two parts.  Computing short range part in
# real space, long range part in reciprocal space.
#

def density_fit(mf, auxbasis=None, gs=None, with_df=None):
    '''Generte density-fitting SCF object

    Args:
        auxbasis : str or basis dict
            Same format to the input attribute mol.basis.
            The default basis 'weigend+etb' means weigend-coulomb-fit basis
            for light elements and even-tempered basis for heavy elements.
        gs : tuple
            number of grids in each (+)direction
        with_df : MDF object
    '''
    from pyscf.pbc.df import mdf
    if with_df is None:
        if hasattr(mf, 'kpts'):
            kpts = mf.kpts
        else:
            kpts = numpy.reshape(mf.kpt, (1,3))

        with_df = mdf.MDF(mf.cell, kpts)
        with_df.max_memory = mf.max_memory
        with_df.stdout = mf.stdout
        with_df.verbose = mf.verbose
        with_df.auxbasis = auxbasis
        if gs is not None:
            with_df.gs = gs

    mf.with_df = with_df
    return mf


def get_j_kpts(mydf, dm_kpts, hermi=1, kpts=numpy.zeros((1,3)), kpts_band=None):
    if mydf._cderi is None or not mydf.has_kpts(kpts_band):
        mydf.build(kpts_band=kpts_band)
    vj_kpts = aft_jk.get_j_kpts(mydf, dm_kpts, hermi, kpts, kpts_band)
    vj_kpts += df_jk.get_j_kpts(mydf, dm_kpts, hermi, kpts, kpts_band)
    return vj_kpts


def get_k_kpts(mydf, dm_kpts, hermi=1, kpts=numpy.zeros((1,3)), kpts_band=None,
               exxdiv=None):
    if mydf._cderi is None or not mydf.has_kpts(kpts_band):
        mydf.build(kpts_band=kpts_band)
    vk_kpts = aft_jk.get_k_kpts(mydf, dm_kpts, hermi, kpts, kpts_band, exxdiv)
    vk_kpts += df_jk.get_k_kpts(mydf, dm_kpts, hermi, kpts, kpts_band, None)
    return vk_kpts


##################################################
#
# Single k-point
#
##################################################

def get_jk(mydf, dm, hermi=1, kpt=numpy.zeros(3),
           kpt_band=None, with_j=True, with_k=True, exxdiv=None):
    '''JK for given k-point'''
    vj = vk = None
    if kpt_band is not None and abs(kpt-kpt_band).sum() > 1e-9:
        kpt = numpy.reshape(kpt, (1,3))
        if with_k:
            vk = get_k_kpts(mydf, [dm], hermi, kpt, kpt_band, exxdiv)
        if with_j:
            vj = get_j_kpts(mydf, [dm], hermi, kpt, kpt_band)
        return vj, vk

    if mydf._cderi is None or not mydf.has_kpts(kpt_band):
        mydf.build(kpts_band=kpt_band)
    vj1, vk1 = df_jk.get_jk(mydf, dm, hermi, kpt, kpt_band, with_j, with_k, None)
    vj, vk = aft_jk.get_jk(mydf, dm, hermi, kpt, kpt_band, with_j, with_k, exxdiv)
    if with_j: vj += vj1
    if with_k: vk += vk1
    return vj, vk


if __name__ == '__main__':
    import pyscf.pbc.gto as pgto
    import pyscf.pbc.scf as pscf
    import pyscf.pbc.dft as pdft

    L = 5.
    n = 5
    cell = pgto.Cell()
    cell.a = numpy.diag([L,L,L])
    cell.gs = numpy.array([n,n,n])

    cell.atom = '''C    3.    2.       3.
                   C    1.    1.       1.'''
    #cell.basis = {'He': [[0, (1.0, 1.0)]]}
    #cell.basis = '631g'
    #cell.basis = {'He': [[0, (2.4, 1)], [1, (1.1, 1)]]}
    cell.basis = 'ccpvdz'
    cell.verbose = 0
    cell.build(0,0)
    cell.verbose = 5
    #print cell.nimgs
    #cell.nimgs = [4,4,4]

    mf = pscf.RHF(cell)
    auxbasis = 'weigend'
    mf = density_fit(mf, auxbasis)
    mf.with_df.gs = (5,) * 3
    dm = mf.get_init_guess()
    vj = get_jk(mf.with_df, dm, exxdiv=mf.exxdiv, with_k=False)[0]
    print(numpy.einsum('ij,ji->', vj, dm), 'ref=46.698951141791')
    vj, vk = get_jk(mf.with_df, dm, exxdiv=mf.exxdiv)
    print(numpy.einsum('ij,ji->', vj, dm), 'ref=46.698951141791')
    print(numpy.einsum('ij,ji->', vk, dm), 'ref=37.348980782463')

    kpts = cell.make_kpts([2]*3)[:4]
    from pyscf.pbc.df import MDF
    with_df = MDF(cell, kpts)
    with_df.auxbasis = 'weigend'
    with_df.gs = [5] * 3
    dms = numpy.array([dm]*len(kpts))
    vj, vk = with_df.get_jk(dms, exxdiv=mf.exxdiv, kpts=kpts)
    print(numpy.einsum('ij,ji->', vj[0], dms[0]), - 46.69784775484954)
    print(numpy.einsum('ij,ji->', vj[1], dms[1]), - 46.69815612398015)
    print(numpy.einsum('ij,ji->', vj[2], dms[2]), - 46.69526857884275)
    print(numpy.einsum('ij,ji->', vj[3], dms[3]), - 46.69571387135913)
    print(numpy.einsum('ij,ji->', vk[0], dms[0]), - 37.27054185436858)
    print(numpy.einsum('ij,ji->', vk[1], dms[1]), - 37.27081050772277)
    print(numpy.einsum('ij,ji->', vk[2], dms[2]), - 37.27081024429790)
    print(numpy.einsum('ij,ji->', vk[3], dms[3]), - 37.27090527533867)
