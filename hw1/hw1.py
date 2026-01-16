# Allowed Modules
import logging
import socket
import sys
import gzip
import ssl
# End of Allowed Modules
# Adding any extra module will result into score of 0

def retrieve_url(url):
  
    TIMEOUT = 15
    MAX_REDIRECTS = 10

    def default_port(scheme):
        return 443 if scheme == "https" else 80

    def idna(host):
        # Convert Unicode hostname to ASCII (punycode)
        try:
            return host.encode("idna").decode("ascii")
        except Exception:
            return None

    def simple_GET(host_ascii, port, path, scheme):
        # Build a minimal, deterministic HTTP/1.1 GET request
        host_hdr = host_ascii if port == default_port(scheme) else f"{host_ascii}:{port}"
        lines = [
            f"GET {path} HTTP/1.1",
            f"Host: {host_hdr}",
            "Connection: close",
            "User-Agent: None",
            "Accept: */*",
            "Accept-Language: en",
            "Accept-Encoding: identity",
            "",  # end headers
            "",
        ]
        try:
            return "\r\n".join(lines).encode("ascii", "strict")
        except UnicodeEncodeError:
            return None

    def open_socket(scheme, host_ascii, port):
        # Open TCP
        s = socket.create_connection((host_ascii, port), timeout=TIMEOUT)
        if scheme == "https":
            ssl_context = ssl.create_default_context() 
            s = ssl_context.wrap_socket(s, server_hostname=host_ascii)  # SNI for HTTPS
        return s

    def partition_response(raw_response):
        # Split raw HTTP response bytes into (header_block, body) or (None, None)
        sep = b"\r\n\r\n"
        i = raw_response.find(sep)
        if i == -1:
            return None, None
        return raw_response[:i], raw_response[i + 4:]

    def parse_headers(header_block):
        # Return (status_code, headers_dict) from a header block
        text = header_block.decode("iso-8859-1", "replace")
        lines = text.split("\r\n")
        # First line is status line
        if not lines or not lines[0].startswith("HTTP/"):
            return None, {}
        parts = lines[0].split(" ", 2)
        try:
            code = int(parts[1])
        except Exception:
            code = None
        hdrs = {}
        # Parse headers
        for ln in lines[1:]:
            if not ln:
                continue
            kv = ln.split(":", 1)
            if len(kv) != 2:
                continue
            k = kv[0].strip().lower()
            v = kv[1].strip()
            hdrs[k] = v
        return code, hdrs

    def decode_chunked(body_bytes):
        # Decode Transfer-Encoding: chunked payload
        pos = 0
        out = bytearray()
        total_len = len(body_bytes)
        #Loop over chunks
        while True:
            j = body_bytes.find(b"\r\n", pos)
            if j == -1:
                return None
            # Parse chunk size line
            size_line = body_bytes[pos:j].decode("ascii", "replace").strip()
            semi = size_line.find(";")
            size_str = size_line[:semi] if semi != -1 else size_line
            try:
                size = int(size_str, 16)
            except ValueError:
                return None
            pos = j + 2
            if size == 0:
                return bytes(out)  # Ignore trailers
            if pos + size > total_len:
                return None
            out += body_bytes[pos:pos + size]
            pos += size
            if body_bytes[pos:pos + 2] != b"\r\n":
                return None
            pos += 2

    def reparse_url(full_url):
        # Reparse an absolute URL into (scheme, host, port, path)
        #HTTP
        if full_url.startswith("http://"):
            rest = full_url[7:]
            scheme = "http"
            port = 80
        #HTTPS
        elif full_url.startswith("https://"):
            rest = full_url[8:]
            scheme = "https"
            port = 443
        else:
            return None
        # Find host, port, path
        slash_idx = rest.find("/")
        if slash_idx == -1:
            hostport = rest
            path = "/"
        else:
            hostport = rest[:slash_idx]
            path = rest[slash_idx:] or "/"
        if not hostport:
            return None

        if ":" in hostport:
            host, port_str = hostport.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                return None
        else:
            host = hostport
        return scheme, host, port, path

    def resolve_redirect(cur_scheme, cur_host, cur_port, cur_path, location):
        # Resolve a Location header into an absolute URL string
        if location.startswith("http://") or location.startswith("https://"):
            return location
        # Protocol
        if location.startswith("//"):
            return f"{cur_scheme}:{location}"
        # Absolute path
        if location.startswith("/"):
            if (cur_scheme == "http" and cur_port == 80) or (cur_scheme == "https" and cur_port == 443):
                return f"{cur_scheme}://{cur_host}{location}"
            else:
                return f"{cur_scheme}://{cur_host}:{cur_port}{location}"
        # Relative path
        base_dir_end = cur_path.rfind("/")
        base_dir = cur_path[:base_dir_end + 1] if base_dir_end != -1 else "/"
        joined = base_dir + location
        if (cur_scheme == "http" and cur_port == 80) or (cur_scheme == "https" and cur_port == 443):
            return f"{cur_scheme}://{cur_host}{joined}"
        else:
            return f"{cur_scheme}://{cur_host}:{cur_port}{joined}"

    def check_dynamic(headers):
        # Check headers for signs of dynamic content
        cc = headers.get("cache-control", "").lower()
        pragma = headers.get("pragma", "").lower()
        vary = headers.get("vary", "").strip()
        # Check for cookies or no cache 
        if "set-cookie" in headers:
            return True
        # Check cache-control, pragma and vary in the headers
        if "no-store" in cc or "no-cache" in cc or "max-age=0" in cc or "private" in cc:
            return True
        if "no-cache" in pragma:
            return True
        if vary == "*":
            return True
        return False

    def full_URL_check(start_scheme, start_host, start_port, start_path):
        # Uses all helper function to open socket, send request, read close, skip 1xx,
        # handle redirects, decode body, return (final_url_tuple, body_bytes, headers_dict) or (None, None, None)
        cur_scheme, cur_host, cur_port, cur_path = start_scheme, start_host, start_port, start_path

        for _ in range(MAX_REDIRECTS + 1):
            host_ascii = idna(cur_host)
            if not host_ascii:
                return None, None, None

            req = simple_GET(host_ascii, cur_port, cur_path, cur_scheme)
            if req is None:
                return None, None, None

            sock = None
            # Read response
            try:
                sock = open_socket(cur_scheme, host_ascii, cur_port)
                sock.sendall(req)

                chunks = []
                while True:
                    data = sock.recv(4096)
                    if not data:
                        break
                    chunks.append(data)
                if not chunks:
                    return None, None, None
                raw_response = b"".join(chunks)
            except (socket.timeout, OSError, ssl.SSLError):
                return None, None, None
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except Exception:
                        pass

            # Skip 1xx responses
            while True:
                header_block, body = partition_response(raw_response)
                if header_block is None:
                    return None, None, None
                code, hdrs = parse_headers(header_block)
                if code is None:
                    return None, None, None
                if 100 <= code < 200:
                    sep_idx = raw_response.find(b"\r\n\r\n")
                    if sep_idx == -1:
                        return None, None, None
                    raw_response = raw_response[sep_idx + 4:]
                    continue
                break

            # Redirects
            if 300 <= code <= 399:
                loc = hdrs.get("location")
                if not loc:
                    return None, None, None
                nxt = resolve_redirect(cur_scheme, cur_host, cur_port, cur_path, loc)
                if not nxt:
                    return None, None, None
                parsed = reparse_url(nxt)
                if not parsed:
                    return None, None, None
                cur_scheme, cur_host, cur_port, cur_path = parsed
                continue

            # Only final 200 OK is acceptable
            if code != 200:
                return None, None, None

            # Transfer/Content encodings
            te = hdrs.get("transfer-encoding", "").lower()
            ce = hdrs.get("content-encoding", "").lower()

            if "chunked" in te:
                decoded = decode_chunked(body)
                if decoded is None:
                    return None, None, None
                body = decoded

            if "gzip" in ce:
                try:
                    body = gzip.decompress(body)
                except Exception:
                    return None, None, None

            # Success
            return (cur_scheme, cur_host, cur_port, cur_path), body, hdrs

        # Too many redirects
        return None, None, None

    # Initial parse (branching)
    if not isinstance(url, str):
        raise ValueError("URL must be a string")
    # HTTP
    if url.startswith("http://"):
        url_no_scheme = url[7:]
        port = 80
        scheme = "http"
    # HTTPS
    elif url.startswith("https://"):
        url_no_scheme = url[8:]
        port = 443
        scheme = "https"
    else:
        raise ValueError("URL must start with http:// or https://")

    slash_idx = url_no_scheme.find("/")
    if slash_idx == -1:
        hostport = url_no_scheme
        path = "/"
    else:
        hostport = url_no_scheme[:slash_idx]
        path = url_no_scheme[slash_idx:] or "/"
    if not hostport:
        return None

    if ":" in hostport:
        host, port_str = hostport.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            return None
    else:
        host = hostport

    # First fetch
    final1, body1, hdrs1 = full_URL_check(scheme, host, port, path)
    if final1 is None or body1 is None:
        return None

    # Only double-fetch if headers suggest content is likely dynamic
    if check_dynamic(hdrs1):
        fs, fh, fp, fpath = final1
        final2, body2, _ = full_URL_check(fs, fh, fp, fpath)
        # Compare bodies
        if final2 is None or body2 is None:
            return None
        if body1 != body2:
            return None

    return body1


if __name__ == "__main__":
    sys.stdout.buffer.write(retrieve_url(sys.argv[1]))
