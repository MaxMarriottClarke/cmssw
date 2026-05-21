import FWCore.ParameterSet.Config as cms

from RecoHGCal.TICL.heterogeneousTracksterProducer_cfi import heterogeneousTracksterProducer as _heterogeneousTracksterProducer

hltHeterogeneousTracksterProducerL1Seeded = _heterogeneousTracksterProducer.clone(
    layerClusters = cms.InputTag('hltMergeLayerClustersL1Seeded'),
)
