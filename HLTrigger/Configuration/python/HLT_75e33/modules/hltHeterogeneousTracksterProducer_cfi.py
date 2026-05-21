import FWCore.ParameterSet.Config as cms

from RecoHGCal.TICL.heterogeneousTracksterProducer_cfi import heterogeneousTracksterProducer as _heterogeneousTracksterProducer

hltHeterogeneousTracksterProducer = _heterogeneousTracksterProducer.clone(
    layerClusters = cms.InputTag('hltMergeLayerClusters'),
)
