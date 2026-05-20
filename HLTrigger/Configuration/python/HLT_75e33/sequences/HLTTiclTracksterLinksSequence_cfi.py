import FWCore.ParameterSet.Config as cms

from ..modules.hltTiclTracksterLinks_cfi import *

HLTTiclTracksterLinksSequence = cms.Sequence(hltTiclTracksterLinks)

from Configuration.ProcessModifiers.alpaka_cff import alpaka
alpaka.toModify(hltTiclTracksterLinks, tracksters_collections = cms.VInputTag("hltHeterogeneousTracksterProducer", "hltTiclTrackstersRecovery"))
