#include "RecoHGCal/TICL/plugins/alpaka/PatternRecognitionPluginFactory.h"
#include "RecoHGCal/TICL/plugins/alpaka/PatternRecognitionByCLUEstering.h"
#include "FWCore/ParameterSet/interface/ValidatedPluginFactoryMacros.h"
#include "FWCore/ParameterSet/interface/ValidatedPluginMacros.h"

// Use a backend-specific category name so the same plugin name ("CLUEstering")
// does not collide across multiple backend .so files in the global plugin registry.
#define ALPAKA_STRINGIFY_(x) #x
#define ALPAKA_STRINGIFY(x) ALPAKA_STRINGIFY_(x)
#define ALPAKA_PATTERN_RECO_FACTORY_NAME ALPAKA_STRINGIFY(ALPAKA_ACCELERATOR_NAMESPACE) "PatternRecognitionFactoryAlpaka"

EDM_REGISTER_VALIDATED_PLUGINFACTORY(PatternRecognitionFactoryAlpaka, ALPAKA_PATTERN_RECO_FACTORY_NAME);
// EDM_REGISTER_VALIDATED_PLUGINFACTORY(PatternRecognitionHFNoseFactoryAlpaka, "PatternRecognitionHFNoseFactoryAlpaka");
DEFINE_EDM_VALIDATED_PLUGIN(PatternRecognitionFactoryAlpaka,
                            ALPAKA_ACCELERATOR_NAMESPACE::PatternRecognitionByCLUEstering,
                            "CLUEstering");
