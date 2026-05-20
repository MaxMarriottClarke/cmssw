import FWCore.ParameterSet.Config as cms

from ..modules.hltFilteredLayerClustersRecoveryL1Seeded_cfi import *
from ..modules.hltTiclTrackstersRecoveryL1Seeded_cfi import *

HLTTiclTrackstersRecoverySequence = cms.Sequence(hltFilteredLayerClustersRecovery+hltTiclTrackstersRecovery)

from Configuration.ProcessModifiers.alpaka_cff import alpaka
alpaka.toModify(hltFilteredLayerClustersRecoveryL1Seeded, LayerClustersInputMask = cms.InputTag("hltHeterogeneousTracksterProducerL1Seeded"))
alpaka.toModify(hltTiclTrackstersRecoveryL1Seeded, original_mask = cms.InputTag("hltHeterogeneousTracksterProducerL1Seeded"))
