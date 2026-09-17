// Default port/interface catalog per device type, used to offer a real port to pick from when
// connecting two devices on the Design canvas or Topology page instead of an abstract line
// between boxes. Purely a frontend convenience list (no server-side port inventory) - the port
// name the user picks (or types, for a type with no default list) is stored as free text on the
// connection (DesignRelationship.source_interface/target_interface,
// TopologyLink.source_interface/destination_interface).
const DEFAULT_PORTS_BY_TYPE: Record<string, string[]> = {
  router: ["Gi0/0", "Gi0/1", "Gi0/2", "Gi0/3"],
  switch: Array.from({ length: 24 }, (_, i) => `Gi0/${i + 1}`),
  firewall: ["Gi0/0", "Gi0/1", "Gi0/2", "Gi0/3", "Gi0/4", "Gi0/5", "Gi0/6", "Gi0/7"],
  load_balancer: ["Gi0/0", "Gi0/1"],
  server: ["eth0", "eth1"],
  domain_controller: ["eth0", "eth1"],
  dns_server: ["eth0"],
  dhcp_server: ["eth0"],
  wlc: ["Gi0/0", "Gi0/1"],
};

export function defaultPortsForType(type: string | null | undefined): string[] {
  if (!type) return [];
  return DEFAULT_PORTS_BY_TYPE[type.toLowerCase()] ?? [];
}
