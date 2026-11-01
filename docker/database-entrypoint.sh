#!/usr/bin/env bash
# This container owns the task network namespace. The agent joins it with
# --network container:<database>, without NET_ADMIN. Fail closed on any error.
set -euo pipefail
: "${MSE_GATEWAY_IPV4:?runner must supply the fixed API gateway IP}"
[[ "$MSE_GATEWAY_IPV4" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]
iptables -w -P INPUT DROP
iptables -w -P FORWARD DROP
iptables -w -P OUTPUT DROP
iptables -w -A INPUT -i lo -j ACCEPT
iptables -w -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -w -A OUTPUT -o lo -d 127.0.0.1/32 -j ACCEPT
iptables -w -A OUTPUT -d "$MSE_GATEWAY_IPV4/32" -p tcp --dport 8080 -j ACCEPT
# Docker's embedded DNS uses 127.0.0.11 and DNATs port 53 before filtering.
# Allow only 127.0.0.1 above, so its rewritten ports cannot bypass this firewall.
iptables -w -I OUTPUT -p udp --dport 53 -j DROP
iptables -w -I OUTPUT -p tcp --dport 53 -j DROP
ip6tables -w -P INPUT DROP
ip6tables -w -P FORWARD DROP
ip6tables -w -P OUTPUT DROP
ip6tables -w -A INPUT -i lo -j ACCEPT
ip6tables -w -A OUTPUT -o lo -j ACCEPT
exec setpriv --bounding-set=-net_admin,-net_raw --inh-caps=-all --ambient-caps=-all \
  /usr/local/bin/docker-entrypoint.sh "$@"
