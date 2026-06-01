import FWCore.ParameterSet.Config as cms

from ..modules.hltFilteredLayerClustersRecovery_cfi import *
from ..modules.hltTiclTrackstersRecovery_cfi import *

HLTTiclTrackstersRecoverySequence = cms.Sequence(hltFilteredLayerClustersRecovery+hltTiclTrackstersRecovery)

from Configuration.ProcessModifiers.alpaka_cff import alpaka
alpaka.toModify(hltFilteredLayerClustersRecovery, LayerClustersInputMask = cms.InputTag("hltHeterogeneousTracksterProducer"))
alpaka.toModify(hltTiclTrackstersRecovery, original_mask = cms.InputTag("hltHeterogeneousTracksterProducer"))
