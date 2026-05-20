import FWCore.ParameterSet.Config as cms

from ..modules.hltFilteredLayerClustersCLUE3DHigh_cfi import *
from ..modules.hltTiclSeedingGlobal_cfi import *
from ..modules.hltTiclTrackstersCLUE3DHigh_cfi import *

HLTTiclTrackstersCLUE3DHighStepSequence = cms.Sequence(hltFilteredLayerClustersCLUE3DHigh+hltTiclSeedingGlobal+hltTiclTrackstersCLUE3DHigh)

from Configuration.ProcessModifiers.alpaka_cff import alpaka
from ..modules.hltHeterogeneousTracksterProducer_cfi import hltHeterogeneousTracksterProducer
alpaka.toReplaceWith(HLTTiclTrackstersCLUE3DHighStepSequence, cms.Sequence(hltHeterogeneousTracksterProducer))
