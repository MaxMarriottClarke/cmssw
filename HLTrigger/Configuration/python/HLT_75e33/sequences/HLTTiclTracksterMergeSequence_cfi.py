import FWCore.ParameterSet.Config as cms

from ..modules.hltTiclTrackstersMerge_cfi import *

HLTTiclTracksterMergeSequence = cms.Sequence(hltTiclTrackstersMerge)

from Configuration.ProcessModifiers.alpaka_cff import alpaka
alpaka.toModify(hltTiclTrackstersMerge, trackstersclue3d = cms.InputTag("hltHeterogeneousTracksterProducer"))
