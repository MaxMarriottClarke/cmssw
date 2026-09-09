import FWCore.ParameterSet.Config as cms

from ..modules.hltFilteredLayerClustersCLUE3DHigh_cfi import *
from ..modules.hltTiclSeedingGlobal_cfi import *
from ..modules.hltTiclTrackstersCLUE3DHigh_cfi import *

HLTTiclTrackstersCLUE3DHighStepSequence = cms.Sequence(hltFilteredLayerClustersCLUE3DHigh+hltTiclSeedingGlobal+hltTiclTrackstersCLUE3DHigh)

# NB: ticl_dev cannot be combined with ticl_barrel. The CLUEstering assignment only
# covers the HGCal device collections, while ticl_barrel appends barrel layer clusters
# to the merged collection; the job then fails in the assignment producer on the mask size.
from Configuration.ProcessModifiers.ticl_dev_cff import ticl_dev
from ..modules.hltTiclTrackstersCLUEsteringAssignment_cfi import *

ticl_dev.toReplaceWith(HLTTiclTrackstersCLUE3DHighStepSequence,
                       cms.Sequence(hltFilteredLayerClustersCLUE3DHigh+hltTiclSeedingGlobal+hltTiclTrackstersCLUEsteringAssignment+hltTiclTrackstersCLUE3DHigh))
