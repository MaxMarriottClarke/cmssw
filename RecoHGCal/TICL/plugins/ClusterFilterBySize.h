// Author: Marco Rovere - marco.rovere@cern.ch
// Date: 11/2018

#ifndef RecoHGCal_TICL_ClusterFilterBySize_H__
#define RecoHGCal_TICL_ClusterFilterBySize_H__

#include "DataFormats/CaloRecHit/interface/CaloClusterHostCollection.h"
#include "ClusterFilterBase.h"

#include <memory>
#include <utility>

// Filter clusters that belong to a specific algorithm
namespace ticl {
  class ClusterFilterBySize final : public ClusterFilterBase {
  public:
    ClusterFilterBySize(const edm::ParameterSet& ps)
        : ClusterFilterBase(ps), max_cluster_size_(ps.getParameter<int>("max_cluster_size")) {}
    ~ClusterFilterBySize() override {}

    void filter(const reco::CaloClusterHostCollection& layerClusters,
                std::vector<float>& layerClustersMask,
                hgcal::RecHitTools& rhtools) const override {

      auto clusters = layerClusters.view();
      for (size_t i = 0; i < static_cast<size_t>(layerClusters.size()[0]); i++) {
        const unsigned int nCells = clusters.position()[i].cells();
        if (nCells > max_cluster_size_) {
          layerClustersMask[i] = 0.;
        }
      }
    }

  private:
    unsigned int max_cluster_size_;
  };
}  // namespace ticl

#endif
