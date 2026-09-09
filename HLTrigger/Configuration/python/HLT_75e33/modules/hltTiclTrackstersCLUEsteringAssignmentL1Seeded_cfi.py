import FWCore.ParameterSet.Config as cms

from RecoHGCal.TICL.trackstersCLUEsteringProducer_cfi import trackstersCLUEsteringProducer as _trackstersCLUEsteringProducer

# layerClusters and sigmaT must follow the hltMergeLayerClustersL1Seeded order: EE, HSci, HSi.
hltTiclTrackstersCLUEsteringAssignmentL1Seeded = _trackstersCLUEsteringProducer.clone(
    layerClusters = ['hltHgcalSoALayerClustersProducerL1Seeded',
                     'hltHgcalSoALayerClustersProducerHSciL1Seeded',
                     'hltHgcalSoALayerClustersProducerHSiL1Seeded'],
    sigmaT = [0.003, 0.012, 0.006],
    filtered_mask = ('hltFilteredLayerClustersCLUE3DHighL1Seeded', 'CLUE3DHigh')
)
