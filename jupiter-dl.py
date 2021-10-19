#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
download media from ERR's online streaming service Jupiter
"""

import json
import logging
import re
import urllib.request
from argparse import ArgumentParser
from urllib.parse import urlparse

USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'
API_BASEURL = 'https://services.err.ee/api/v2/'
EXPECTED_HOSTNAME = 'jupiter.err.ee'


def extract_content_id(url):
    parsed = urlparse(url)

    hostname = parsed.hostname
    if hostname != EXPECTED_HOSTNAME:
        raise ValueError(f"expected '{EXPECTED_HOSTNAME}' as hostname, got '{hostname}'")
        # TODO: maybe remove this check since urls like https://lasteekraan.err.ee/<content_id> are also possible; only deal with the api's response for an id; maybe let the user provide the id upfront

    path = parsed.path
    match = re.match(r'^/(?P<content_id>\d+)(/|$)', path)
    if match is None:
        raise ValueError(f"no content ID in path '{path}'")

    return match.group('content_id')


def fetch_content_page_data(content_id):
    url = API_BASEURL + 'vodContent/getContentPageData?contentId=' + str(content_id)
    req = urllib.request.Request(url,
                                 headers={'User-Agent': USER_AGENT},
                                 origin_req_host=f'https://{EXPECTED_HOSTNAME}/{content_id}')
    with urllib.request.urlopen(req) as resp:
        page_obj = json.loads(resp.read())
    if 'data' not in page_obj:
        raise FileNotFoundError(f"page data for content ID '{content_id}' could not be retrieved, server responded "
                                f"with: {page_obj}")
    return page_obj['data']


def download(url):
    if url.startswith('//'):
        url = 'https:' + url
        # TODO: nasty and doesn't belong here

    file_name = url.split('/')[-1]  # TODO: this is dangerous :-)

    with urllib.request.urlopen(url) as u:
        file_size = int(u.headers['content-length'])

        if args.dry_run:
            logging.info("** DRY RUN ** Would download %s bytes '%s'.", file_size, file_name)
            return

        logging.info("Downloading %s bytes '%s'.", file_size, file_name)

        with open(file_name, 'wb') as f:
            file_size_dl = 0
            block_size = 8192  # 8 kB
            while True:
                buffer = u.read(block_size)
                if not buffer:
                    break
                file_size_dl += len(buffer)
                f.write(buffer)
                logging.debug("%d/%d", file_size_dl, file_size)

            logging.info("Finished downloading '%s'.", file_name)


def main(args):
    logging.basicConfig(level=args.loglevel or logging.INFO)

    logging.info("Will extract content ID from URL '%s'.", args.url)
    content_id = extract_content_id(args.url)
    logging.info("Extracted content ID '%s' from URL.", content_id)

    logging.info("Going to fetch data about the content.")
    page_data = fetch_content_page_data(content_id)
    logging.debug("`page_data`: %s", page_data)
    content_type = page_data['mainContent']['type']
    content_heading = page_data['mainContent']['heading']
    if len(page_data['mainContent']['subHeading']) > 0:
        content_heading += " -- " + page_data['mainContent']['subHeading']
    logging.info("Received '%s' data for '%s'.", content_type, content_heading)

    medias = page_data['mainContent']['medias']
    for media in medias:
        logging.debug("`media`: %s", media)
        download(media['src']['file'])
        # TODO: look into the m3u8 file (media['hls']) to find the highest def ver and dl that
        if args.dl_subs:
            for sub in media['subtitles']:
                download(sub['src'])

    # TODO: deal with drm!!!
    # TODO: add possibility to bulk dl series
    # TODO: error handling


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-v', '--verbose', action='store_const', const=logging.DEBUG, dest='loglevel',
                       help="enable verbose (debug) logging")
    group.add_argument('-q', '--quiet', action='store_const', const=logging.WARN, dest='loglevel',
                       help="enable silent mode (log only warnings)")
    parser.add_argument('--dl-subs', action='store_true',
                        help="download subtitles as well")
    parser.add_argument('--dry-run', action='store_true',
                        help="do not download media and do not write anything to disk (no-op mode)")
    parser.add_argument('url',
                        help=f'{EXPECTED_HOSTNAME} URL to download from')

    args = parser.parse_args()

    main(args)
