// Authors: Marco Rovere - marco.rovere@cern.ch, Felice Pantaleo - felice.pantaleo@cern.ch
// Date: 09/2020

#ifndef RecoHGCal_TICL_ClusterFilterByAlgoAndSizeAndLayerRange_H__
#define RecoHGCal_TICL_ClusterFilterByAlgoAndSizeAndLayerRange_H__

#include "DataFormats/CaloRecHit/interface/CaloClusterHostCollection.h"
#include "ClusterFilterBase.h"

#include <memory>
#include <utility>

// Filter clusters that belong to a specific algorithm
namespace ticl {
  class ClusterFilterByAlgoAndSizeAndLayerRange final : public ClusterFilterBase {
  public:
    ClusterFilterByAlgoAndSizeAndLayerRange(const edm::ParameterSet& ps)
        : ClusterFilterBase(ps),
          algo_number_(ps.getParameter<std::vector<int>>("algo_number")),
          min_cluster_size_(ps.getParameter<int>("min_cluster_size")),
          max_cluster_size_(ps.getParameter<int>("max_cluster_size")),
          min_layerId_(ps.getParameter<int>("min_layerId")),
          max_layerId_(ps.getParameter<int>("max_layerId")) {}
    ~ClusterFilterByAlgoAndSizeAndLayerRange() override {}

    void filter(const reco::CaloClusterHostCollection& layerClusters,
                std::vector<float>& layerClustersMask,
                hgcal::RecHitTools& rhtools) const override {

      auto clusters = layerClusters.view();
      for (size_t i = 0; i < static_cast<size_t>(layerClusters.size()[0]); i++) {
        auto layerId = rhtools.getLayerWithOffset(clusters.indexes()[i].seedID());
        const unsigned int nCells = clusters.position()[i].cells();
        if (find(algo_number_.begin(), algo_number_.end(), clusters.indexes()[i].algoID()) == algo_number_.end() or
            layerId > max_layerId_ or layerId < min_layerId_ or nCells > max_cluster_size_ or
            (nCells < min_cluster_size_ and rhtools.isSilicon(clusters.indexes()[i].seedID()))) {
          layerClustersMask[i] = 0.;
        }
      }
    }

  private:
    std::vector<int> algo_number_;
    unsigned int min_cluster_size_;
    unsigned int max_cluster_size_;
    unsigned int min_layerId_;
    unsigned int max_layerId_;
  };
}  // namespace ticl

#endif
