#include "Ping.hpp"

using SST::Interfaces::StringEvent;

// Constructor for our component
Ping::Ping(SST::ComponentId_t id, SST::Params &params) : SST::Component(id) {
  // initialize SST output to STDOUT
  output.init("Ping-" + getName() + "-> ", 1, 0, SST::Output::STDOUT);

  // register a dummy time base so we can send messages
  registerTimeBase("1Hz");

  // get our parameter
  maxRepeats = params.find<uint64_t>("model", 10);
  repeats = 0;
  output.output(CALL_INFO, "Maximum Repeats: %lu\n", maxRepeats);

  // configure the port we will use to send and receive messages
  port = configureLink("inout",
                       new SST::Event::Handler<Ping>(this, &Ping::handleEvent));
  if (!port) {
    output.fatal(CALL_INFO, -1, "Failed to configure port 'inoutPort'\n");
  }
  // Tell SST this component is a "Primary" Component and that the simulation
  // shouldn't end unless this component says it is OK
  registerAsPrimaryComponent();
  primaryComponentDoNotEndSim();
}

// SST function that runs before the start of simulated time
// This is being used to initiate the "ping pong" between components
void Ping::setup() { port->send(new StringEvent("ping")); }

// Called when input is received
void Ping::handleEvent(SST::Event *ev) {
  // Casting the SST Event to a StringEvent
  StringEvent *msg = dynamic_cast<StringEvent *>(ev);
  output.output(CALL_INFO, "Received message: %s\n", msg->getString().c_str());
  delete msg;

  // Checking to see if we have repeated the ping pong the requested number of
  // times If so, tell SST it is OK to stop the simulation now
  repeats++;
  output.output(CALL_INFO, "Repeats: %lu\n", repeats);
  if (repeats >= maxRepeats) {
    primaryComponentOKToEndSim();
    return;
  }

  msg = new StringEvent("ping");
  output.output(CALL_INFO, "Sent message: %s\n", msg->getString().c_str());
  port->send(msg);
}
