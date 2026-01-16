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

#CACHES 

DNSCache = {}      
ZoneCache = {}     
HostCache = {}      
CNAMEChain = False  

def startDNServers(name: dns.name.Name):
# WALK UP DNS TREE TO FIND EITHER CACHED OR ROOT SERVERS
    cur = name
    while True:
        ips = ZoneCache.get(cur)
        if ips:
            return list(ips)
        if cur == dns.name.root:
            break
        cur = cur.parent()
    return list(ROOT_SERVERS)

def AddZoneIPs(zone: dns.name.Name, ips):
# ADD IPs TO ZONE CACHE
    if not zone or not ips:
        return
    existing = ZoneCache.get(zone, []) # GET EXISTING IPS 
    ZoneCache[zone] = list(dict.fromkeys(existing + list(ips))) # REMOVE DUPLICATES AND ADD NEW IPS

def cacheDNSHostA(answer_rrsets):
# ADD A RECORDS TO HOST CACHE
    for rrset in answer_rrsets:
        if rrset.rdtype == dns.rdatatype.A:
            HostCache[rrset.name] = [rr.address for rr in rrset]

def buildCnameChain(original_name: dns.name.Name):
#TODO Q4. BUILD FULL CNAME CHAIN
    """ www.yahoo.com.tw is an alias for rc.yahoo.com.
	rc.yahoo.com is an alias for global-accelerator.dns-rc.aws.oath.cloud.
	global-accelerator.dns-rc.aws.oath.cloud is an alias for a7de0457831fd11f7.awsglobalaccelerator.com. #ADD THIS SECTION
	a7de0457831fd11f7.awsglobalaccelerator.com has address 13.248.158.7
	a7de0457831fd11f7.awsglobalaccelerator.com has address 76.223.84.192"""
    global CNAMEChain #To access global flag
    
    if CNAMEChain:
        return None  

    # Begin building full chain
    CNAMEChain = True
    finalCnameChain = dns.message.make_response(
        dns.message.make_query(original_name, dns.rdatatype.CNAME)
    )

    seen = set()  # Track seen aliases to avoid loops
    cur = original_name

    while True:
        step = lookup(cur, dns.rdatatype.CNAME)
        rrsetValues = next((rs for rs in step.answer if rs.rdtype == dns.rdatatype.CNAME), None) # Get CNAME rrset
        if rrsetValues is None:
            break

        finalCnameChain.answer.append(rrsetValues)
        nextLink = rrsetValues[0].target 

        if nextLink in seen:
            break

        seen.add(nextLink)
        cur = nextLink

    # Reset flag
    CNAMEChain = False
    return finalCnameChain


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
    key = (target_name, qtype)
    if key in DNSCache:
        return DNSCache[key]

    # Choose starting servers either from cache or root servers
    currentServers = startDNServers(target_name)  
    maxIters = 30 # Set limit

    for i in range(maxIters):
        progressed = False 

        for server in currentServers:
            # ERROR HANDLING FOR Q5
            try:
                query = dns.message.make_query(target_name, qtype, use_edns=True)
                query.flags &= ~dns.flags.RD  
                response = dns.query.udp(query, server, timeout=3)
                if response.flags & dns.flags.TC:
                    response = dns.query.tcp(query, server, timeout=3)
            except Exception:
                continue
            
            # PROCESS RESPONSE
            rcode = response.rcode()
            if rcode not in (dns.rcode.NOERROR, dns.rcode.NXDOMAIN):
                continue

            # Answer case
            if response.answer:
                # If CNAME query build full CNAME chain
                if qtype == dns.rdatatype.CNAME:
                    chain = buildCnameChain(target_name)
                    if chain is not None:
                        DNSCache[key] = chain
                        return chain
                    # No chain found cache normal response
                    DNSCache[key] = response
                    return response

                # Handle CNAME redirection for other types
                cnameTarget = None
                for rrset in response.answer:
                    if rrset.rdtype == dns.rdatatype.CNAME:
                        cnameTarget = rrset[0].target
                        break
                if cnameTarget and qtype != dns.rdatatype.CNAME:
                    out = lookup(cnameTarget, qtype) 
                    DNSCache[key] = out 
                    return out

                # Cache any A answers 
                cacheDNSHostA(response.answer)

                DNSCache[key] = response
                return response

            # Referral case
            NSNames = []
            nsZone = None
            for rrset in response.authority:
                if rrset.rdtype == dns.rdatatype.NS:
                    nsZone = nsZone or rrset.name
                    # Collect server names
                    for rr in rrset:
                        NSNames.append(rr.target)

            # Glue case 
            glueV4 = []
            for rrset in response.additional:
                # collect A records
                if rrset.rdtype == dns.rdatatype.A:
                    for rr in rrset:
                        glueV4.append(rr.address)
            # Use glue if available
            if glueV4:
                if nsZone:
                    AddZoneIPs(nsZone, glueV4)  # helps Q7 
                currentServers = glueV4
                progressed = True
                break

            # No glue case so resolve NS names
            if NSNames:
                resolveV4 = []
                # Resolve NS name to A record
                for NSName in NSNames:
                    if NSName in HostCache:
                        resolveV4.extend(HostCache[NSName])
                        continue
                    try:
                        nsResponse = lookup(NSName, dns.rdatatype.A)  # ONLY A lookups
                        addrs = []
                        # Extract A records
                        for rrset in nsResponse.answer:
                            if rrset.rdtype == dns.rdatatype.A:
                                for rr in rrset:
                                    addrs.append(rr.address) # Collect addresses
                        # Cache resolved addresses
                        if addrs:
                            HostCache[NSName] = addrs
                            resolveV4.extend(addrs)
                    except Exception:
                        continue
                # Use resolved addresses
                if resolveV4:
                    if nsZone:
                        AddZoneIPs(nsZone, resolveV4) 
                    currentServers = resolveV4
                    progressed = True
                    break

            # NODATA case 
            for rrset in response.authority:
                if rrset.rdtype == dns.rdatatype.SOA:
                    DNSCache[key] = response  # cache negative/NODATA 
                    return response


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
