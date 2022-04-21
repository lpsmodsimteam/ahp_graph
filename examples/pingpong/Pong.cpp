#include "Pong.hpp"

using SST::Interfaces::StringEvent;

// Constructor for our component
Pong::Pong(SST::ComponentId_t id, SST::Params &params) : SST::Component(id) {
  // get the rank that we are running on for demonstration purposes
  rank = getRank();
  myRank = std::to_string(rank.rank);

  // initialize SST output to STDOUT
  output.init(getName() + myRank + "-> ", 1, 0, SST::Output::STDOUT);

  // register a dummy time base so we can send messages
  registerTimeBase("1Hz");

  // configure the port we will use to receive messages
  inPort = configureLink(
      "input", new SST::Event::Handler<Pong>(this, &Pong::handleEvent));
  if (!inPort) {
    output.fatal(CALL_INFO, -1, "Failed to configure port 'input'\n");
  }
  // configure the port we will use to send messages (don't need an event
  // handler)
  outPort = configureLink("output");
  if (!outPort) {
    output.fatal(CALL_INFO, -1, "Failed to configure port 'output'\n");
  }
}

// Called when input is received
void Pong::handleEvent(SST::Event *ev) {
  // Casting the SST Event to a StringEvent
  StringEvent *msg = dynamic_cast<StringEvent *>(ev);
  output.output(CALL_INFO, "Received message: %s\n", msg->getString().c_str());
  std::string newMsg = msg->getString() + "-Pong" + myRank;
  delete msg;

  msg = new StringEvent(newMsg);
  output.output(CALL_INFO, "Sent message: %s\n", msg->getString().c_str());
  outPort->send(msg);
}
