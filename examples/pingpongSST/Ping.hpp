#pragma once

#include <sst/core/component.h>
#include <sst/core/interfaces/stringEvent.h>
#include <sst/core/link.h>
#include <sst/core/rankInfo.h>

/*!
  @brief Ping "sender" which initiates the pingpong message passing
  */
class Ping : public SST::Component {
public:
  SST_ELI_DOCUMENT_PORTS(
      {"input", "port which receives messages", {"sst.Interfaces.StringEvent"}},
      {"output", "port which sends messages", {"sst.Interfaces.StringEvent"}});

  SST_ELI_REGISTER_COMPONENT(Ping, "pingpong", "Ping",
                             SST_ELI_ELEMENT_VERSION(0, 0, 1), "Ping",
                             COMPONENT_CATEGORY_UNCATEGORIZED);

  SST_ELI_DOCUMENT_PARAMS({"model",
                           "number of times to let the message travel around",
                           "10"});

  Ping(SST::ComponentId_t id, SST::Params &params);
  ~Ping() {}

  void setup();
  void handleEvent(SST::Event *ev);

private:
  uint64_t repeats;
  uint64_t maxRepeats;

  SST::RankInfo rank;
  std::string myRank;

  SST::Output output;

  SST::Link *inPort;
  SST::Link *outPort;
};
