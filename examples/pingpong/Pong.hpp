#pragma once

#include <sst/core/component.h>
#include <sst/core/interfaces/stringEvent.h>
#include <sst/core/link.h>
#include <sst/core/rankInfo.h>

/*!
  @brief Pong "receiver"
  */
class Pong : public SST::Component {
public:
  SST_ELI_DOCUMENT_PORTS(
      {"input", "port which receives messages", {"sst.Interfaces.StringEvent"}},
      {"output", "port which sends messages", {"sst.Interfaces.StringEvent"}});

  SST_ELI_REGISTER_COMPONENT(Pong, "pingpong", "Pong",
                             SST_ELI_ELEMENT_VERSION(0, 0, 1), "Pong",
                             COMPONENT_CATEGORY_UNCATEGORIZED);

  Pong(SST::ComponentId_t id, SST::Params &params);
  ~Pong() {}

  void handleEvent(SST::Event *ev);

private:
  SST::RankInfo rank;
  std::string myRank;

  SST::Output output;

  SST::Link *inPort;
  SST::Link *outPort;
};
