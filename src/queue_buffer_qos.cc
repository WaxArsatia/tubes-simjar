#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/traffic-control-module.h"

#include <algorithm>
#include <iomanip>
#include <initializer_list>
#include <iostream>
#include <sstream>
#include <string>

using namespace ns3;

namespace
{
Ipv4InterfaceContainer
AssignSubnet(Ipv4AddressHelper& address, NetDeviceContainer devices, uint32_t& networkIndex)
{
    std::ostringstream subnet;
    subnet << "10." << networkIndex++ << ".0.0";
    address.SetBase(subnet.str().c_str(), "255.255.255.0");
    return address.Assign(devices);
}

ApplicationContainer
InstallUdpCbr(NodeContainer sourceAndDestination,
              Ipv4Address destinationAddress,
              uint16_t destinationPort,
              const std::string& dataRate,
              uint32_t packetSize,
              double startTime,
              double stopTime)
{
    OnOffHelper client("ns3::UdpSocketFactory",
                       InetSocketAddress(destinationAddress, destinationPort));
    client.SetAttribute("DataRate", StringValue(dataRate));
    client.SetAttribute("PacketSize", UintegerValue(packetSize));
    client.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
    client.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));

    ApplicationContainer app = client.Install(sourceAndDestination.Get(0));
    app.Start(Seconds(startTime));
    app.Stop(Seconds(stopTime));
    return app;
}
}

int
main(int argc, char* argv[])
{
    uint32_t bufferPackets = 10;
    uint32_t runSeed = 1;
    uint32_t packetSize = 1024;
    bool csvHeader = false;
    double simulationStop = 25.0;
    double trafficStart = 1.0;
    double trafficStop = 19.0;
    std::string mainRate = "1Mbps";
    std::string backgroundRate = "0.5Mbps";

    CommandLine cmd(__FILE__);
    cmd.AddValue("bufferPackets", "FifoQueueDisc MaxSize on R4->H4 in packets", bufferPackets);
    cmd.AddValue("runSeed", "NS-3 run number for reproducible repetitions", runSeed);
    cmd.AddValue("csvHeader", "Print CSV header before data row", csvHeader);
    cmd.AddValue("simulationStop", "Simulation stop time in seconds", simulationStop);
    cmd.AddValue("mainRate", "UDP CBR rate for H0->H4", mainRate);
    cmd.AddValue("backgroundRate", "UDP CBR rate for each background flow", backgroundRate);
    cmd.Parse(argc, argv);

    if (bufferPackets == 0)
    {
        std::cerr << "bufferPackets must be greater than zero\n";
        return 2;
    }
    if (trafficStop <= trafficStart)
    {
        std::cerr << "trafficStop must be greater than trafficStart\n";
        return 5;
    }
    if (simulationStop <= trafficStop)
    {
        std::cerr << "simulationStop must be greater than trafficStop so all offered traffic is measured\n";
        return 5;
    }

    SeedManager::SetSeed(12345);
    SeedManager::SetRun(runSeed);

    NodeContainer hosts;
    hosts.Create(5);
    NodeContainer routers;
    routers.Create(5);

    InternetStackHelper stack;
    stack.Install(hosts);
    stack.Install(routers);

    PointToPointHelper hostLink;
    hostLink.SetDeviceAttribute("DataRate", StringValue("100Mbps"));
    hostLink.SetChannelAttribute("Delay", StringValue("2ms"));
    hostLink.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize("10000p")));

    PointToPointHelper routerLink;
    routerLink.SetDeviceAttribute("DataRate", StringValue("10Mbps"));
    routerLink.SetChannelAttribute("Delay", StringValue("5ms"));
    routerLink.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize("10000p")));

    PointToPointHelper bottleneckLink;
    bottleneckLink.SetDeviceAttribute("DataRate", StringValue("2Mbps"));
    bottleneckLink.SetChannelAttribute("Delay", StringValue("10ms"));
    bottleneckLink.SetQueue("ns3::DropTailQueue", "MaxSize", QueueSizeValue(QueueSize("1p")));

    NetDeviceContainer h0r0 = hostLink.Install(NodeContainer(hosts.Get(0), routers.Get(0)));
    NetDeviceContainer h1r1 = hostLink.Install(NodeContainer(hosts.Get(1), routers.Get(1)));
    NetDeviceContainer h2r2 = hostLink.Install(NodeContainer(hosts.Get(2), routers.Get(2)));
    NetDeviceContainer h3r3 = hostLink.Install(NodeContainer(hosts.Get(3), routers.Get(3)));
    NetDeviceContainer r4h4 = bottleneckLink.Install(NodeContainer(routers.Get(4), hosts.Get(4)));

    NetDeviceContainer r0r1 = routerLink.Install(NodeContainer(routers.Get(0), routers.Get(1)));
    NetDeviceContainer r1r2 = routerLink.Install(NodeContainer(routers.Get(1), routers.Get(2)));
    NetDeviceContainer r2r3 = routerLink.Install(NodeContainer(routers.Get(2), routers.Get(3)));
    NetDeviceContainer r3r4 = routerLink.Install(NodeContainer(routers.Get(3), routers.Get(4)));
    NetDeviceContainer r4r0 = routerLink.Install(NodeContainer(routers.Get(4), routers.Get(0)));
    NetDeviceContainer r0r2 = routerLink.Install(NodeContainer(routers.Get(0), routers.Get(2)));
    NetDeviceContainer r1r3 = routerLink.Install(NodeContainer(routers.Get(1), routers.Get(3)));

    TrafficControlHelper trafficControl;
    std::ostringstream queueSize;
    queueSize << bufferPackets << "p";
    trafficControl.SetRootQueueDisc("ns3::FifoQueueDisc",
                                    "MaxSize",
                                    QueueSizeValue(QueueSize(queueSize.str())));
    NetDeviceContainer bottleneckDevice;
    bottleneckDevice.Add(r4h4.Get(0));
    QueueDiscContainer bottleneckQueueDisc = trafficControl.Install(bottleneckDevice);

    Ipv4AddressHelper address;
    uint32_t networkIndex = 1;
    Ipv4InterfaceContainer h0r0If = AssignSubnet(address, h0r0, networkIndex);
    Ipv4InterfaceContainer h1r1If = AssignSubnet(address, h1r1, networkIndex);
    Ipv4InterfaceContainer h2r2If = AssignSubnet(address, h2r2, networkIndex);
    Ipv4InterfaceContainer h3r3If = AssignSubnet(address, h3r3, networkIndex);
    Ipv4InterfaceContainer r4h4If = AssignSubnet(address, r4h4, networkIndex);
    AssignSubnet(address, r0r1, networkIndex);
    AssignSubnet(address, r1r2, networkIndex);
    AssignSubnet(address, r2r3, networkIndex);
    AssignSubnet(address, r3r4, networkIndex);
    AssignSubnet(address, r4r0, networkIndex);
    AssignSubnet(address, r0r2, networkIndex);
    AssignSubnet(address, r1r3, networkIndex);

    Ipv4Address h0Address = h0r0If.GetAddress(0);
    Ipv4Address h4Address = r4h4If.GetAddress(1);

    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    const uint16_t mainPort = 9000;
    const uint16_t bgPort1 = 9001;
    const uint16_t bgPort2 = 9002;
    const uint16_t bgPort3 = 9003;

    for (uint16_t port : {mainPort, bgPort1, bgPort2, bgPort3})
    {
        PacketSinkHelper sink("ns3::UdpSocketFactory", InetSocketAddress(Ipv4Address::GetAny(), port));
        ApplicationContainer sinkApp = sink.Install(hosts.Get(4));
        sinkApp.Start(Seconds(0.0));
        sinkApp.Stop(Seconds(simulationStop + 1.0));
    }

    InstallUdpCbr(NodeContainer(hosts.Get(0), hosts.Get(4)),
                  h4Address,
                  mainPort,
                  mainRate,
                  packetSize,
                  trafficStart,
                  trafficStop);
    InstallUdpCbr(NodeContainer(hosts.Get(1), hosts.Get(4)),
                  h4Address,
                  bgPort1,
                  backgroundRate,
                  packetSize,
                  trafficStart,
                  trafficStop);
    InstallUdpCbr(NodeContainer(hosts.Get(2), hosts.Get(4)),
                  h4Address,
                  bgPort2,
                  backgroundRate,
                  packetSize,
                  trafficStart,
                  trafficStop);
    InstallUdpCbr(NodeContainer(hosts.Get(3), hosts.Get(4)),
                  h4Address,
                  bgPort3,
                  backgroundRate,
                  packetSize,
                  trafficStart,
                  trafficStop);

    FlowMonitorHelper flowMonitorHelper;
    Ptr<FlowMonitor> monitor = flowMonitorHelper.InstallAll();

    Simulator::Stop(Seconds(simulationStop));
    Simulator::Run();
    monitor->CheckForLostPackets();
    const QueueDisc::Stats& queueDiscStats = bottleneckQueueDisc.Get(0)->GetStats();
    const uint64_t queueDiscDrops =
        queueDiscStats.GetNDroppedPackets(FifoQueueDisc::LIMIT_EXCEEDED_DROP);

    Ptr<Ipv4FlowClassifier> classifier =
        DynamicCast<Ipv4FlowClassifier>(flowMonitorHelper.GetClassifier());
    FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();

    bool foundMainFlow = false;
    FlowId mainFlowId = 0;
    uint64_t txPackets = 0;
    uint64_t rxPackets = 0;
    uint64_t lostPackets = 0;
    uint64_t rxBytes = 0;
    double averageDelayMs = 0.0;

    for (const auto& entry : stats)
    {
        Ipv4FlowClassifier::FiveTuple tuple = classifier->FindFlow(entry.first);
        if (tuple.sourceAddress == h0Address && tuple.destinationAddress == h4Address &&
            tuple.destinationPort == mainPort)
        {
            foundMainFlow = true;
            mainFlowId = entry.first;
            txPackets = entry.second.txPackets;
            rxPackets = entry.second.rxPackets;
            rxBytes = entry.second.rxBytes;
            lostPackets = txPackets >= rxPackets ? txPackets - rxPackets : 0;
            averageDelayMs =
                rxPackets > 0 ? entry.second.delaySum.GetSeconds() * 1000.0 / rxPackets : 0.0;
            break;
        }
    }

    if (!foundMainFlow)
    {
        std::cerr << "main flow H0->H4 was not found\n";
        Simulator::Destroy();
        return 3;
    }

    if (txPackets == 0)
    {
        std::cerr << "main flow H0->H4 transmitted zero packets\n";
        Simulator::Destroy();
        return 4;
    }

    const double measurementDuration = trafficStop - trafficStart;
    const double throughputMbps = static_cast<double>(rxBytes) * 8.0 / measurementDuration / 1000000.0;
    const double lossRatio =
        static_cast<double>(lostPackets) * 100.0 / static_cast<double>(txPackets);

    if (csvHeader)
    {
        std::cout << "buffer_packets,tx_packets,rx_packets,lost_packets,queue_disc_drops,"
                  << "packet_loss_ratio_percent,throughput_mbps,average_delay_ms,run_seed,flow_id\n";
    }

    std::cout << std::fixed << std::setprecision(6) << bufferPackets << ',' << txPackets << ','
              << rxPackets << ',' << lostPackets << ',' << queueDiscDrops << ',' << lossRatio
              << ',' << throughputMbps << ',' << averageDelayMs << ',' << runSeed << ','
              << mainFlowId << '\n';

    Simulator::Destroy();
    return 0;
}
