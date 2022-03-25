#pragma once

#include <sst/core/component.h>
#include <sst/core/interfaces/stringEvent.h>
#include <sst/core/link.h>

/*!
  @brief Pong "receiver"
  */
class Pong : public SST::Component {
public:
  SST_ELI_DOCUMENT_PORTS({"inout", "port", {"sst.Interfaces.StringEvent"}});

  SST_ELI_REGISTER_COMPONENT(Pong, "pingpong", "Pong",
                             SST_ELI_ELEMENT_VERSION(0, 0, 1), "Pong",
                             COMPONENT_CATEGORY_UNCATEGORIZED);

  Pong(SST::ComponentId_t id, SST::Params &params);
  ~Pong() {}

  void handleEvent(SST::Event *ev);

private:
  SST::Output output;
  SST::Link *port;
};
