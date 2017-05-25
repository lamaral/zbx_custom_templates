#!/usr/bin/env python3
# Author: Luiz Amaral - https://www.luiz.eng.br/

import argparse
import socket
from datetime import datetime
import time
import re

try:
    # Try to load pyOpenSSL first
    from OpenSSL import SSL
    import OpenSSL
    PYOPENSSL = True
except ImportError:
    PYOPENSSL = False

CA_CERTS = "/etc/ssl/certs/ca-certificates.crt"


def exit_error(errcode, errtext):
    print(errtext)
    exit(errcode)


def pyopenssl_check_callback(connection, x509, errnum, errdepth, ok):
    ''' callback for pyopenssl ssl check'''
    # Check if the certificate names match the SNI if defined or the hostname itself
    match = False
    # Compare the common name
    if x509.get_subject().commonName == SNI:
        match=True
    # If it didn't match, compare the alternative names
    if not match:
        # Get the alternative names on certificate
        names = pyopenssl_cert_san(x509)
        for name in names:
            if name == SNI:
                match=True
                break;
    # If the name matched, check the expiration date and return
    if match and DAYS:
        if x509.has_expired():
            exit_error(1, 'Error: Certificate has expired!')
        else:
            print(pyopenssl_check_expiration(x509.get_notAfter()))

    if not ok:
        return False
    return ok


def pyopenssl_check_expiration(asn1):
    # Dark magic
    try:
        expire_date = datetime.strptime(asn1.decode(), "%Y%m%d%H%M%SZ")
    except:
        exit_error(1, 'Certificate date format unknow.')

    expire_in = expire_date - datetime.now()
    if expire_in.days > 0:
        return expire_in.days
    else:
        return False

def pyopenssl_cert_san(cert_or_req):
    # Function borrowed from https://github.com/certbot/certbot/blob/master/acme/acme/crypto_util.py

    # constants based on PyOpenSSL certificate/CSR text dump
    part_separator = ":"
    parts_separator = ", "
    prefix = "DNS" + part_separator

    if isinstance(cert_or_req, OpenSSL.crypto.X509):
        func = OpenSSL.crypto.dump_certificate
    else:
        func = OpenSSL.crypto.dump_certificate_request
    text = func(OpenSSL.crypto.FILETYPE_TEXT, cert_or_req).decode("utf-8")
    # WARNING: this function does not support multiple SANs extensions.
    # Multiple X509v3 extensions of the same type is disallowed by RFC 5280.
    match = re.search(r"X509v3 Subject Alternative Name:\s*(.*)", text)
    # WARNING: this function assumes that no SAN can include
    # parts_separator, hence the split!
    sans_parts = [] if match is None else match.group(1).split(parts_separator)

    return [part.split(part_separator)[1]
            for part in sans_parts if part.startswith(prefix)]


def main():
    # Argument parsing
    parser = argparse.ArgumentParser()

    mxgroup = parser.add_mutually_exclusive_group(required=True)
    mxgroup.add_argument('-i', '--issuer', help='outputs the certificate issuer', action='store_true')
    mxgroup.add_argument('-d', '--days', help='outputs the number of days until certificate expiration', action='store_true')
    
    parser.add_argument('host', help='specify an host to connect to')
    parser.add_argument('-p', '--port', help='specify a port to connect to',
                        type=int, default=443)
    parser.add_argument('-n', '--name', help='specify the SNI',
                        type=str)
    args = parser.parse_args()

    # Passing arguments to global vars
    global HOST, PORT, SNI, ISSUER, DAYS
    HOST = args.host
    PORT = args.port
    # If SNI is not defined, define it as the hostname
    SNI = args.name if args.name else args.host
    ISSUER = args.issuer
    DAYS = args.days

    # Check the DNS name
    try:
        socket.getaddrinfo(HOST, PORT)[0][4][0]
    except socket.gaierror as e:
        exit_error(1, e)

    # Connect to the host and get the certificate
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    # Check if the PyOpenSSL was imported successfully
    if PYOPENSSL:
        try:
            ctx = SSL.Context(SSL.TLSv1_METHOD)
            ctx.set_verify(SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
                           pyopenssl_check_callback)
            ctx.load_verify_locations(CA_CERTS)

            ssl_sock = SSL.Connection(ctx, sock)
            ssl_sock.set_connect_state()
            ssl_sock.set_tlsext_host_name(SNI.encode())
            ssl_sock.do_handshake()

            x509 = ssl_sock.get_peer_certificate()
            x509name = x509.get_subject()

            # Check if the common name matches. If not, fallback to using the subject alternative names
            match = False
            if x509name.commonName == SNI:
                match=True
            if not match:
                # Fallback to SAN. The line below calls the function that returns a list of all the SAN in the certificate
                names = pyopenssl_cert_san(x509)
                for name in names:
                    if name == SNI:
                        match=True
                        break;
            # In case the name matched and the issuer was requested
            if match and ISSUER:
                print(x509.get_issuer().commonName)

            # In case none of the names matched, throw an error
            if not match:
                #print(SNI, x509name.commonName, names)
                exit_error(1, 'Error: Hostname does not match!')

            ssl_sock.shutdown()

        except SSL.Error as e:
            exit_error(1, e)
    # Couldn't import PyOpenSSL
    else:
        exit_error(1, "Couldn't import required modules")

    sock.close()


if __name__ == "__main__":
    main()