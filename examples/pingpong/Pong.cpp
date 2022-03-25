#include "Pong.hpp"

using SST::Interfaces::StringEvent;

// Constructor for our component
Pong::Pong(SST::ComponentId_t id, SST::Params &params) : SST::Component(id) {

  // initialize SST output to STDOUT
  output.init("Pong-" + getName() + "-> ", 1, 0, SST::Output::STDOUT);

  // register a dummy time base so we can send messages
  registerTimeBase("1Hz");

  // configure the port we will use to send and receive messages
  port = configureLink("inout",
                       new SST::Event::Handler<Pong>(this, &Pong::handleEvent));
  if (!port) {
    output.fatal(CALL_INFO, -1, "Failed to configure port 'inoutPort'\n");
  }
}

// Called when input is received
void Pong::handleEvent(SST::Event *ev) {
  // Casting the SST Event to a StringEvent
  StringEvent *msg = dynamic_cast<StringEvent *>(ev);
  output.output(CALL_INFO, "Received message: %s\n", msg->getString().c_str());
  delete msg;

  msg = new StringEvent("pong");
  output.output(CALL_INFO, "Sent message: %s\n", msg->getString().c_str());
  port->send(msg);
}
