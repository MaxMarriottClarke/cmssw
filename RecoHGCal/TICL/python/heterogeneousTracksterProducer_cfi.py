import FWCore.ParameterSet.Config as cms

heterogeneousTracksterProducer = cms.EDProducer(
    'HeterogeneousTracksterProducer@alpaka',
    layerClusters = cms.InputTag('mergeLayerClusters'),
    patternRecognitionBy = cms.string('CLUEstering'),
    pluginPatternRecognitionByCLUEstering = cms.PSet(
        rho_c = cms.double(0.1),
        dc    = cms.double(0.1),
        dm    = cms.double(4.),
        ds    = cms.double(10.),
        type  = cms.string('CLUEstering'),
    ),
    alpaka = cms.untracked.PSet(backend = cms.untracked.string('')),
)
