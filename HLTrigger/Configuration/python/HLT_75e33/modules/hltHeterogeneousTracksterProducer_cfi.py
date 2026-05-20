import FWCore.ParameterSet.Config as cms

hltHeterogeneousTracksterProducer = cms.EDProducer(
    'HeterogeneousTracksterProducer@alpaka',
    layerClusters = cms.InputTag('hltMergeLayerClusters'),
    patternRecognitionBy = cms.string('CLUEstering'),
    pluginPatternRecognitionByCLUEstering = cms.PSet(
        rho_c = cms.double(6.),
        dc    = cms.double(2.),
        dm    = cms.double(1.8),
        type  = cms.string('CLUEstering'),
    ),
    alpaka = cms.untracked.PSet(backend = cms.untracked.string('')),
)
