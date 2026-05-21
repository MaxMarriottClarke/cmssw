# Reconstruction
from RecoHGCal.TICL.iterativeTICL_cff import *
from RecoLocalCalo.HGCalRecProducers.hgcalLayerClusters_cff import hgcalLayerClustersEE, hgcalLayerClustersHSi, hgcalLayerClustersHSci
from RecoLocalCalo.HGCalRecProducers.hgcalMergeLayerClusters_cfi import hgcalMergeLayerClusters
from RecoHGCal.TICL.ticlDumper_cff import ticlDumper
# Validation
from Validation.HGCalValidation.HGCalValidator_cff import *
from RecoLocalCalo.HGCalRecProducers.recHitMapProducer_cff import recHitMapProducer

# Load DNN ESSource
from RecoTracker.IterativeTracking.iterativeTk_cff import trackdnn_source

# Automatic addition of the customisation function from RecoHGCal.Configuration.RecoHGCal_EventContent_cff
from RecoHGCal.Configuration.RecoHGCal_EventContent_cff import customiseHGCalOnlyEventContent
from SimCalorimetry.HGCalAssociatorProducers.simTracksterAssociatorByEnergyScore_cfi import simTracksterAssociatorByEnergyScore as simTsAssocByEnergyScoreProducer
from SimCalorimetry.HGCalAssociatorProducers.TSToSimTSAssociation_cfi import  allTrackstersToSimTrackstersAssociationsByLCs
from SimCalorimetry.HGCalAssociatorProducers.TSToSimTSAssociationByHits_cfi import allTrackstersToSimTrackstersAssociationsByHits
from SimCalorimetry.HGCalAssociatorProducers.SimClusterToCaloParticleAssociation_cfi import SimClusterToCaloParticleAssociation


def customiseTICLFromReco(process):
    # TensorFlow ESSource
    process.TFESSource = cms.Task(process.trackdnn_source)

    process.hgcalLayerClustersTask = cms.Task(process.hgcalLayerClustersEE,
                                              process.hgcalLayerClustersHSi,
                                              process.hgcalLayerClustersHSci,
                                              process.hgcalMergeLayerClusters)

# Reconstruction
    process.TICL = cms.Path(process.hgcalLayerClustersTask,
                            process.TFESSource,
                            process.ticlLayerTileTask,
                            process.ticlIterationsTask,
                            process.ticlTracksterMergeTask)
# Validation
    process.TICL_ValidationProducers = cms.Task(process.recHitMapProducer,
                                                process.lcAssocByEnergyScoreProducer,
                                                process.layerClusterCaloParticleAssociationProducer,
                                                process.scAssocByEnergyScoreProducer,
                                                process.layerClusterSimClusterAssociationProducer,
                                                process.simTsAssocByEnergyScoreProducer,
                                                process.simTracksterHitLCAssociatorByEnergyScoreProducer,
                                                process.allTrackstersToSimTrackstersAssociationsByLCs,
                                                process.allTrackstersToSimTrackstersAssociationsByHits,
                                                process.SimClusterToCaloParticleAssociation,
                                                )

    process.TICL_Validator = cms.Task(process.hgcalValidator)
    process.TICL_Validation = cms.Path(process.TICL_ValidationProducers,
                                       process.TICL_Validator
                                       )
# Path and EndPath definitions
    process.FEVTDEBUGHLToutput_step = cms.EndPath(process.FEVTDEBUGHLToutput)
    process.DQMoutput_step = cms.EndPath(process.DQMoutput)

# Schedule definition
    process.schedule = cms.Schedule(process.TICL,
                                    process.TICL_Validation,
                                    process.FEVTDEBUGHLToutput_step,
                                    process.DQMoutput_step)
# call to customisation function customiseHGCalOnlyEventContent imported from RecoHGCal.Configuration.RecoHGCal_EventContent_cff
    process = customiseHGCalOnlyEventContent(process)

    return process


def customiseTICLForDumper(process, histoName="histo.root"):

    from RecoHGCal.TICL.HLTSimTracksters_cff import (
        hltFilteredLayerClustersSimTracksters,
        tpToHltGeneralTrackAssociation,
        hltTiclSimTracksters,
    )
    from Validation.RecoTrack.associators_cff import (
        hltTPClusterProducer,
        hltTrackAssociatorByHits,
    )
    from SimGeneral.TrackingAnalysis.simHitTPAssociation_cfi import simHitTPAssocProducer

    from Validation.Configuration.hltHGCalSimValid_cff import (
        hltRecHitMapProducer,
        hltLcAssocByEnergyScoreProducer,
        hltScAssocByEnergyScoreProducer,
        hltLayerClusterCaloParticleAssociationProducer,
        hltLayerClusterSimClusterAssociationProducer,
        SimClusterToCaloParticleAssociation,
    )

    from SimCalorimetry.HGCalAssociatorProducers.AllLayerClusterToTracksterAssociatorsProducer_cfi import AllLayerClusterToTracksterAssociatorsProducer as _AllLCtoTSProducer
    from SimCalorimetry.HGCalAssociatorProducers.TSToSimTSAssociation_cfi import allTrackstersToSimTrackstersAssociationsByLCs as _allTStoSimTSAssoc

    recoLabel = "hltHeterogeneousTracksterProducer"

    hltAllLayerClusterToTracksterAssociations = _AllLCtoTSProducer.clone(
        layer_clusters = cms.InputTag("hltHgCalLayerClustersFromSoAProducer"),
        tracksterCollections = cms.VInputTag(
            cms.InputTag(recoLabel),
            cms.InputTag("hltTiclSimTracksters"),
            cms.InputTag("hltTiclSimTracksters", "fromCPs"),
        ),
    )
    hltAllTrackstersToSimTrackstersAssociationsByLCs = _allTStoSimTSAssoc.clone(
        allLCtoTSAccoc = cms.string("hltAllLayerClusterToTracksterAssociations"),
        layerClusters = cms.InputTag("hltHgCalLayerClustersFromSoAProducer"),
        tracksterCollections = cms.VInputTag(cms.InputTag(recoLabel)),
        simTracksterCollections = cms.VInputTag(
            cms.InputTag("hltTiclSimTracksters"),
            cms.InputTag("hltTiclSimTracksters", "fromCPs"),
        ),
    )

    process.hltTPClusterProducer = hltTPClusterProducer
    process.hltTrackAssociatorByHits = hltTrackAssociatorByHits
    process.tpToHltGeneralTrackAssociation = tpToHltGeneralTrackAssociation
    process.hltFilteredLayerClustersSimTracksters = hltFilteredLayerClustersSimTracksters
    process.hltTiclSimTracksters = hltTiclSimTracksters
    process.simHitTPAssocProducer = simHitTPAssocProducer
    process.hltRecHitMapProducer = hltRecHitMapProducer
    process.hltLcAssocByEnergyScoreProducer = hltLcAssocByEnergyScoreProducer
    process.hltScAssocByEnergyScoreProducer = hltScAssocByEnergyScoreProducer
    process.hltLayerClusterCaloParticleAssociationProducer = hltLayerClusterCaloParticleAssociationProducer.clone(
        label_lc = cms.InputTag("hltHgCalLayerClustersFromSoAProducer")
    )
    process.hltLayerClusterSimClusterAssociationProducer = hltLayerClusterSimClusterAssociationProducer.clone(
        label_lcl = cms.InputTag("hltHgCalLayerClustersFromSoAProducer")
    )
    process.SimClusterToCaloParticleAssociation = SimClusterToCaloParticleAssociation
    process.hltAllLayerClusterToTracksterAssociations = hltAllLayerClusterToTracksterAssociations
    process.hltAllTrackstersToSimTrackstersAssociationsByLCs = hltAllTrackstersToSimTrackstersAssociationsByLCs

    process.hltTiclDumperSimAndAssocSeq = cms.Sequence(
        process.simHitTPAssocProducer +
        process.hltTPClusterProducer +
        process.hltTrackAssociatorByHits +
        process.tpToHltGeneralTrackAssociation +
        process.hltRecHitMapProducer +
        process.hltLcAssocByEnergyScoreProducer +
        process.hltScAssocByEnergyScoreProducer +
        process.SimClusterToCaloParticleAssociation +
        process.hltLayerClusterCaloParticleAssociationProducer +
        process.hltLayerClusterSimClusterAssociationProducer +
        process.hltFilteredLayerClustersSimTracksters +
        process.hltTiclSimTracksters +
        process.hltAllLayerClusterToTracksterAssociations +
        process.hltAllTrackstersToSimTrackstersAssociationsByLCs
    )

    process.ticlDumperProducers = cms.Path(
        process.hltHgcalDigis +
        process.HLTTICLLocalRecoSequence +
        process.HLTTiclTrackstersCLUE3DHighStepSequence +
        process.hltTiclDumperSimAndAssocSeq
    )

    process.schedule.insert(
        list(process.schedule).index(process.endjob_step),
        process.ticlDumperProducers
    )

    process.ticlDumper = ticlDumper.clone()

    process.TFileService = cms.Service("TFileService",
                                       fileName=cms.string(histoName)
                                       )
    process.FEVTDEBUGHLToutput_step = cms.EndPath(
        process.FEVTDEBUGHLToutput + process.ticlDumper)
    return process
