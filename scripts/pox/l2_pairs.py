"""
MAC learning switch
No dedicated Controller class.
_handle_PacketIn shows how to parse a packet using pox

Notice that this is the simplest example of a reactive(dynamic) configuration.

Learn:  
        how pox components model work
        how to create an object able to raise events, create a new event class,
        how to setup handler priority
        how to stop an event using an handler
        how to set-up a One-time event,
        how to unsubscribe to an event

        how to parse a packet from an event obj
        how to construct a of_packet_out to tell the switch to flood
        how to construct a of_flow_add to tell the switch a new flow rule
"""

# TODO: 
#       how to subscribe EventRaiser to the pox core
#       what is the purpose of a connection object
#       how to manually parse raw_data payloads


from pox.core import core
import pox.openflow.libopenflow_01 as of

from pox.lib.revent import Event, EventMixin, EventHalt
import pox.lib.packet as pkt

import time

log = core.getLogger()

table = {}  # table[(a, b)]


class EventName(Event):

    """event that can be raised by EventRaiser"""

    def __init__(self):
        """TODO: to be defined1. """
        Event.__init__(self)
        log.debug("Inside EventName")


class EventRaiser(EventMixin):

    """obj able to raise events"""

    _eventMixin_events = set([
        EventName,
    ])
        

def _handle_EventName(event):
    """EvenName handler function

    :event: revent.Event
    """
    log.debug("callback: _handle_EventName")


def _handle_EventName_urgent(event):
    """see addListener in the launch function for the priority

    :returns: optional block the event otherwise pass the 
    control to the next handler according to priority
    """

    log.debug("callback: _handle_EventName_urgent")
    # return EventHalt
        

def _handle_EventName_onetime(event):
    """see addListener in the launch function for once

    :event: revent.Event

    """
    log.debug("callback: _handle_EventName_onetime")


def _handle_PacketIn(event):
    """PacketIn message is sent by the switch when
    its flow table contains no rule to route an
    incoming packet.
    """

    all_ports = of.OFPP_FLOOD  # 65531
    # log.debug("OFPP_FLOOD: %r" % all_ports)

    # obtain the packet object reference
    packet = event.parsed

    # parsed contains the openflow payload that usually is
    # the first part of the packet sent from host to s3
    log.debug("event: %r" % (event.__dict__))

    # table is indexed by a tuple (connection, mac_address)
    # log.debug("event.connection: %r" % (event.connection.__dict__))
    src_key = (event.connection, packet.src)
    table[src_key] = event.port
    log.debug("controller add new table entry: %r: %r" % (
        src_key, table[src_key]))

    # built key given the MAC destination 
    # and search the table for destination port
    dst_key = (event.connection, packet.dst)
    dst_port = table.get(dst_key)

    # tell the switch to flood -> send a of_packet_out pkt
    if dst_port is None:
        # data is a reference to the event that called that function
        of_packet_out = of.ofp_packet_out(data=event.ofp)

        # create a flood action
        action = of.ofp_action_output(port=all_ports)
        of_packet_out.actions.append(action)

        # send the of_packet_out
        event.connection.send(of_packet_out)

    # tell the switch two new rules -> send two of_flow_add pkts
    else:

        # first rule map PacketIn source mac to
        of_flow_add = of.ofp_flow_mod()

        # create matching rule
        of_flow_add.match.dl_src = packet.dst
        of_flow_add.match.dl_dst = packet.src

        # tell which port to use with those matching rules
        action = of.ofp_action_output(port=event.port)
        of_flow_add.actions.append(action)

        event.connection.send(of_flow_add)

        # do the same inverting source and destinantion 
        of_flow_add = of.ofp_flow_mod()

        of_flow_add.match.dl_src = packet.src
        of_flow_add.match.dl_dst = packet.dst

        action = of.ofp_action_output(port=dst_port)
        of_flow_add.actions.append(action)

        event.connection.send(of_flow_add)

        log.debug("Sent to switch rules for %s <-> %s" % (packet.src, packet.dst))


def _dissect_PacketIn(event):
    """Show how to parse packet using pox

    """
    packet = event.parsed
    inport = event.port
    dpid = event.connection.dpid
    if not packet.parsed:
        log.warning("%i %i ignoring unparsed packet", dpid, inport)
        return

    payload = packet.payload
    log.debug("first packet %r, with payload: %r with dpid=%r and inport=%r"
            % (packet, payload, dpid, inport))


def launch(disable_flood=False):
    """TODO: Docstring for launch.

    :disable_flood: TODO
    :returns: TODO

    """
    log.info("l2_pairs is running.")

    all_ports = of.OFPP_FLOOD
    log.debug("OFPP_FLOOD port number=%s" % (all_ports))

    if disable_flood:
        all_ports = of.OFPP_ALL
        log.debug("OFPP_ALL port number=%s" % (all_ports))

    # event_class, event_id = core.openflow.addListenerByName("PacketIn", _dissect_PacketIn, priority=2)
    event_class, event_id = core.openflow.addListenerByName("PacketIn", _handle_PacketIn, priority=1)

    # raiser = EventRaiser()
    # # default priority is unknown
    # event_class, event_id = raiser.addListener(EventName, _handle_EventName, priority=0)
    # event_class, event_id = raiser.addListener(EventName, _handle_EventName_urgent, priority=2)
    # event_class, event_id = raiser.addListener(EventName, _handle_EventName_onetime,
    #         once=True, priority=-1)

    # for x in range(3):
    #     raiser.raiseEvent(EventName)
    #     time.sleep(1)

    # rc = core.openflow.removeListener(event_id)
    # log.debug("core.openflow doesn't listen to %s with EID:%s? %r" % (event_class, event_id, rc))
