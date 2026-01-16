"""
resolve.py: a recursive resolver built using dnspython
"""

import argparse

import dns.message
import dns.name
import dns.query
import dns.rdata
import dns.rdataclass
import dns.rdatatype

FORMATS = (("CNAME", "{alias} is an alias for {name}"),
           ("A", "{name} has address {address}"),
           ("AAAA", "{name} has IPv6 address {address}"),
           ("MX", "{name} mail is handled by {preference} {exchange}"))

# current as of 25 October 2018
ROOT_SERVERS = ("198.41.0.4",
                "199.9.14.201",
                "192.33.4.12",
                "199.7.91.13",
                "192.203.230.10",
                "192.5.5.241",
                "192.112.36.4",
                "198.97.190.53",
                "192.36.148.17",
                "192.58.128.30",
                "193.0.14.129",
                "199.7.83.42",
                "202.12.27.33")


def collect_results(name: str) -> dict:
    """
    This function parses final answers into the proper data structure that
    print_results requires. The main work is done within the `lookup` function.
    """
    full_response = {}
    target_name = dns.name.from_text(name)
    # lookup CNAME
    response = lookup(target_name, dns.rdatatype.CNAME)
    cnames = []
    tmp = name
    for answers in response.answer:
        for answer in answers:
            cnames.append({"name": answer, "alias": tmp})
            tmp = answer
    # lookup A
    response = lookup(target_name, dns.rdatatype.A)
    arecords = []
    for answers in response.answer:
        a_name = answers.name
        for answer in answers:
            if answer.rdtype == 1:  # A record
                arecords.append({"name": a_name, "address": str(answer)})
    # lookup AAAA
    response = lookup(target_name, dns.rdatatype.AAAA)
    aaaarecords = []
    for answers in response.answer:
        aaaa_name = answers.name
        for answer in answers:
            if answer.rdtype == 28:  # AAAA record
                aaaarecords.append({"name": aaaa_name, "address": str(answer)})
    # lookup MX
    response = lookup(target_name, dns.rdatatype.MX)
    mxrecords = []
    for answers in response.answer:
        mx_name = answers.name
        for answer in answers:
            if answer.rdtype == 15:  # MX record
                mxrecords.append({"name": mx_name,
                                  "preference": answer.preference,
                                  "exchange": str(answer.exchange)})

    full_response["CNAME"] = cnames
    full_response["A"] = arecords
    full_response["AAAA"] = aaaarecords
    full_response["MX"] = mxrecords

    return full_response


def lookup(target_name: dns.name.Name,
           qtype: dns.rdata.Rdata) -> dns.message.Message:
    """
    This function uses a recursive resolver to find the relevant answer to the
    query.

    TODO: replace this implementation with one which asks the root servers
    and recurses to find the proper answer.
    """
    if not hasattr(lookup, "_answer_cache"):
        lookup._answer_cache = {}      # (dns.name.Name, qtype) -> dns.message.Message
    if not hasattr(lookup, "_zone_ip_hints"):
        lookup._zone_ip_hints = {}     # zone name -> [IPv4 strings]
    if not hasattr(lookup, "_host_a_cache"):
        lookup._host_a_cache = {}      # dns.name.Name -> [IPv4 strings]
    if not hasattr(lookup, "_building_cname_chain"):
        lookup._building_cname_chain = False  # flag to build full CNAME chain only once

    _ANS = lookup._answer_cache
    _ZONE = lookup._zone_ip_hints
    _HOSTA = lookup._host_a_cache

    # Fast path: return cached response if available
    key = (target_name, qtype)
    if key in _ANS:
        return _ANS[key]

    # Helper: choose starting servers using cached zone hints if possible
    def _start_servers_for(name: dns.name.Name):
        cur = name
        while True:
            if cur in _ZONE and _ZONE[cur]:
                return list(_ZONE[cur])
            if cur == dns.name.root:
                break
            cur = cur.parent()
        return list(ROOT_SERVERS)

    current_servers = _start_servers_for(target_name)
    max_iters = 30

    for _ in range(max_iters):
        progressed = False

        for server in current_servers:
            try:
                query = dns.message.make_query(target_name, qtype, use_edns=True)
                query.flags &= ~dns.flags.RD  # iterative (don’t request recursion)
                response = dns.query.udp(query, server, timeout=3)
                if response.flags & dns.flags.TC:
                    response = dns.query.tcp(query, server, timeout=3)
            except Exception:
                continue

            rcode = response.rcode()
            if rcode not in (dns.rcode.NOERROR, dns.rcode.NXDOMAIN):
                continue

            # Case 1: got an answer (could be CNAME or the requested type)
            if response.answer:
                cname_target = None
                for rrset in response.answer:
                    if rrset.rdtype == dns.rdatatype.CNAME:
                        cname_target = rrset[0].target

                # --- FULL CNAME CHAIN HANDLING (only for CNAME queries) ---
                if qtype == dns.rdatatype.CNAME:
                    if not lookup._building_cname_chain:
                        lookup._building_cname_chain = True
                        try:
                            chain_msg = dns.message.make_response(
                                dns.message.make_query(target_name, dns.rdatatype.CNAME)
                            )
                            seen = set()
                            cur = target_name
                            while True:
                                step = lookup(cur, dns.rdatatype.CNAME)
                                step_rrset = None
                                for rs in step.answer:
                                    if rs.rdtype == dns.rdatatype.CNAME:
                                        step_rrset = rs
                                        break
                                if step_rrset is None:
                                    break
                                chain_msg.answer.append(step_rrset)
                                nxt = step_rrset[0].target
                                if nxt in seen:
                                    break
                                seen.add(nxt)
                                cur = nxt
                            _ANS[key] = chain_msg
                            return chain_msg
                        finally:
                            lookup._building_cname_chain = False
                    else:
                        # internal recursive call, just return server's response
                        _ANS[key] = response
                        return response

                # --- NORMAL (non-CNAME) behavior ---
                if cname_target and qtype != dns.rdatatype.CNAME:
                    out = lookup(cname_target, qtype)
                    _ANS[key] = out
                    return out

                # Cache A responses for NS hostnames
                for rrset in response.answer:
                    if rrset.rdtype == dns.rdatatype.A:
                        _HOSTA[rrset.name] = [rr.address for rr in rrset]

                _ANS[key] = response
                return response

            # Case 2: referral — collect NS names
            ns_names = []
            for rrset in response.authority:
                if rrset.rdtype == dns.rdatatype.NS:
                    for rr in rrset:
                        ns_names.append(rr.target)

            # Delegated zone name
            delegated_zone = None
            for rrset in response.authority:
                if rrset.rdtype == dns.rdatatype.NS:
                    delegated_zone = rrset.name
                    break

            # Prefer IPv4 glue ONLY (A records in Additional)
            glue_v4 = []
            for rrset in response.additional:
                if rrset.rdtype == dns.rdatatype.A:
                    for rr in rrset:
                        glue_v4.append(rr.address)

            if glue_v4:
                if delegated_zone:
                    _ZONE[delegated_zone] = list(dict.fromkeys(glue_v4))
                current_servers = glue_v4
                progressed = True
                break

            # No glue -> resolve NS hostnames to A (IPv4) ONLY
            if ns_names:
                resolved_v4 = []
                for ns_name in ns_names:
                    if ns_name in _HOSTA:
                        resolved_v4.extend(_HOSTA[ns_name])
                        continue
                    try:
                        ns_resp = lookup(ns_name, dns.rdatatype.A)
                        for rrset in ns_resp.answer:
                            if rrset.rdtype == dns.rdatatype.A:
                                for rr in rrset:
                                    resolved_v4.append(rr.address)
                        if resolved_v4:
                            _HOSTA[ns_name] = list(dict.fromkeys(resolved_v4))
                    except Exception:
                        continue
                if resolved_v4:
                    if delegated_zone:
                        existing = _ZONE.get(delegated_zone, [])
                        merged = list(dict.fromkeys(existing + resolved_v4))
                        _ZONE[delegated_zone] = merged
                    current_servers = resolved_v4
                    progressed = True
                    break

            # Case 3: authoritative NODATA (SOA present)
            for rrset in response.authority:
                if rrset.rdtype == dns.rdatatype.SOA:
                    _ANS[key] = response
                    return response

        if not progressed:
            raise RuntimeError("Failed to resolve: no responding IPv4 referrals")

    raise RuntimeError("Max recursion depth reached")


def print_results(results: dict) -> None:
    """
    take the results of a `lookup` and print them to the screen like the host
    program would.
    """

    for rtype, fmt_str in FORMATS:
        for result in results.get(rtype, []):
            print(fmt_str.format(**result))


def main():
    """
    if run from the command line, take args and call
    printresults(lookup(hostname))
    """
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("name", nargs="+",
                                 help="DNS name(s) to look up")
    argument_parser.add_argument("-v", "--verbose",
                                 help="increase output verbosity",
                                 action="store_true")
    program_args = argument_parser.parse_args()
    for a_domain_name in program_args.name:
        print_results(collect_results(a_domain_name))

if __name__ == "__main__":
    main()
