import FWCore.ParameterSet.Config as cms

from RecoHGCal.TICL.trackstersCLUEsteringProducer_cfi import trackstersCLUEsteringProducer as _trackstersCLUEsteringProducer

# layerClusters and sigmaT must follow the hltMergeLayerClusters order: EE, HSci, HSi.
hltTiclTrackstersCLUEsteringAssignment = _trackstersCLUEsteringProducer.clone(
    layerClusters = ['hltHgcalSoALayerClustersProducer',
                     'hltHgcalSoALayerClustersProducerHSci',
                     'hltHgcalSoALayerClustersProducerHSi'],
    sigmaT = [0.003, 0.012, 0.006],
    filtered_mask = ('hltFilteredLayerClustersCLUE3DHigh', 'CLUE3DHigh')
)
