// Authors: Marco Rovere - marco.rovere@cern.ch, Felice Pantaleo - felice.pantaleo@cern.ch
// Date: 11/2018

#ifndef RecoHGCal_TICL_ClusterFilterByAlgoAndSize_H__
#define RecoHGCal_TICL_ClusterFilterByAlgoAndSize_H__

#include "DataFormats/CaloRecHit/interface/CaloClusterHostCollection.h"
#include "ClusterFilterBase.h"

#include <memory>
#include <utility>

// Filter clusters that belong to a specific algorithm
namespace ticl {
  class ClusterFilterByAlgoAndSize final : public ClusterFilterBase {
  public:
    ClusterFilterByAlgoAndSize(const edm::ParameterSet& ps)
        : ClusterFilterBase(ps),
          algo_number_(ps.getParameter<std::vector<int>>(
              "algo_number")),  // hgcal_em = 6, hgcal_had = 7, hgcal_scintillator = 8, hfnose = 9
          min_cluster_size_(ps.getParameter<int>("min_cluster_size")),
          max_cluster_size_(ps.getParameter<int>("max_cluster_size")) {}
    ~ClusterFilterByAlgoAndSize() override {}

    void filter(const reco::CaloClusterHostCollection& layerClusters,
                std::vector<float>& layerClustersMask,
                hgcal::RecHitTools& rhtools) const override {
      auto clusters = layerClusters.view();
      for (size_t i = 0; i < static_cast<size_t>(layerClusters.size()[0]); i++) {
        const unsigned int nCells = clusters.position()[i].cells();
        if ((find(algo_number_.begin(), algo_number_.end(), clusters.indexes()[i].algoID()) == algo_number_.end()) or
            (nCells > max_cluster_size_) or
            ((nCells < min_cluster_size_) and (rhtools.isSilicon(clusters.indexes()[i].seedID())))) {
          layerClustersMask[i] = 0.;
        }
      }
    }

  private:
    std::vector<int> algo_number_;
    unsigned int min_cluster_size_;
    unsigned int max_cluster_size_;
  };
}  // namespace ticl

#endif
