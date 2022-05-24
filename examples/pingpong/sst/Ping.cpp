#include "Ping.hpp"

using SST::Interfaces::StringEvent;

// Constructor for our component
Ping::Ping(SST::ComponentId_t id, SST::Params &params) : SST::Component(id) {
  // get the rank that we are running on for demonstration purposes
  rank = getRank();
  myRank = std::to_string(rank.rank);

  // initialize SST output to STDOUT
  output.init(getName() + myRank + "-> ", 1, 0, SST::Output::STDOUT);

  // register a dummy time base so we can send messages
  registerTimeBase("1Hz");

  // get our parameter
  maxRepeats = params.find<uint64_t>("model", 10);
  repeats = 0;
  output.output(CALL_INFO, "Maximum Repeats: %lu\n", maxRepeats);

  // configure the port we will use to receive messages
  inPort = configureLink(
      "input", new SST::Event::Handler<Ping>(this, &Ping::handleEvent));
  if (!inPort) {
    output.fatal(CALL_INFO, -1, "Failed to configure port 'input'\n");
  }
  // configure the port we will use to send messages (don't need an event
  // handler)
  outPort = configureLink("output");
  if (!outPort) {
    output.fatal(CALL_INFO, -1, "Failed to configure port 'output'\n");
  }
  // Tell SST this component is a "Primary" Component and that the simulation
  // shouldn't end unless this component says it is OK
  registerAsPrimaryComponent();
  primaryComponentDoNotEndSim();
}

// SST function that runs before the start of simulated time
// This is being used to initiate the "ping pong" between components
void Ping::setup() { outPort->send(new StringEvent("Ping" + myRank)); }

// Called when input is received
void Ping::handleEvent(SST::Event *ev) {
  // Casting the SST Event to a StringEvent
  StringEvent *msg = dynamic_cast<StringEvent *>(ev);
  output.output(CALL_INFO, "Received message: %s\n", msg->getString().c_str());
  std::string newMsg = msg->getString() + "-Ping" + myRank;
  delete msg;

  // Checking to see if we have repeated the ping pong the requested number of
  // times If so, tell SST it is OK to stop the simulation now
  repeats++;
  output.output(CALL_INFO, "Repeats: %lu\n", repeats);
  if (repeats >= maxRepeats) {
    primaryComponentOKToEndSim();
    return;
  }

  msg = new StringEvent(newMsg);
  output.output(CALL_INFO, "Sent message: %s\n", msg->getString().c_str());
  outPort->send(msg);
}
