import FWCore.ParameterSet.Config as cms
from RecoHGCal.TICL.ticlDumper_cfi import ticlDumper as ticlDumper_

from Configuration.ProcessModifiers.ticl_superclustering_mustache_pf_cff import ticl_superclustering_mustache_pf
from Configuration.ProcessModifiers.ticl_superclustering_mustache_ticl_cff import ticl_superclustering_mustache_ticl


from RecoHGCal.TICL.iterativeTICL_cff import associatorsInstances

ticlIterLabels = ["hltHeterogeneousTracksterProducer"]
simTrackstersCollections = ["hltTiclSimTracksters", "hltTiclSimTrackstersfromCPs"]
dumperAssociators = []

for simTrackstersCollection in simTrackstersCollections:
    for tracksterIteration in ticlIterLabelsPSet.labels:
        suffix = "CP" if "fromCPs" in simTrackstersCollection else "SC"
        dumperAssociators.append(
            cms.PSet(
                branchName=cms.string(tracksterIteration),
                suffix=cms.string(suffix),
                associatorRecoToSimInputTag=cms.InputTag(f"hltAllTrackstersToSimTrackstersAssociationsByLCs:{tracksterIteration}To{simTrackstersCollection}"),
                associatorSimToRecoInputTag=cms.InputTag(f"hltAllTrackstersToSimTrackstersAssociationsByLCs:{simTrackstersCollection}To{tracksterIteration}")
            )
        )


ticlDumper = ticlDumper_.clone(
    tracksterCollections = [*[cms.PSet(treeName=cms.string(label), inputTag=cms.InputTag(label)) for label in ticlIterLabelsPSet.labels],
        cms.PSet(
            treeName=cms.string("simtrackstersSC"),
            inputTag=cms.InputTag("hltTiclSimTracksters"),
            tracksterType=cms.string("SimTracksterSC")
        ),
        cms.PSet(
            treeName=cms.string("simtrackstersCP"),
            inputTag=cms.InputTag("hltTiclSimTracksters", "fromCPs"),
            tracksterType=cms.string("SimTracksterCP")
        ),
    ],

    associators=dumperAssociators.copy(),

    layerClusters = cms.InputTag('hltHgCalLayerClustersFromSoAProducer'),
    layer_clustersTime = cms.InputTag('hltHgCalLayerClustersFromSoAProducer', 'timeLayerCluster'),
    tracks = cms.InputTag('hltGeneralTracks'),
    saveLCs = cms.bool(False),
    saveTICLCandidate = cms.bool(False),
    saveSimTICLCandidate = cms.bool(False),
    saveTracks = cms.bool(False),
    saveSuperclustering = cms.bool(False),
    saveRecoSuperclusters = cms.bool(False),
    saveHits = cms.bool(False),
)

#ticl_v5.toModify(ticlDumper,
#                 ticlcandidates = cms.InputTag("ticlCandidate"),
#                 recoSuperClusters_sourceTracksterCollection=cms.InputTag("ticlTrackstersCLUE3DHigh"),
#                 saveSuperclustering = cms.bool(True),
#                 trackstersInCand=cms.InputTag("ticlCandidate"))
#
(ticl_v5 & ticl_superclustering_mustache_pf).toModify(ticlDumper, saveSuperclustering=False, recoSuperClusters_sourceTracksterCollection=cms.InputTag("ticlTrackstersCLUE3DHigh"))
