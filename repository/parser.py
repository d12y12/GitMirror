#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parser pages and export repo json file.
"""

import os
import json
import requests
import time
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .minisetting import Setting
from .utils import get_logger, get_github_token
from .store import Repository, RepositoryStore


class ParserError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class Meta:
    def __init__(self):
        self.meta = {
            'repository': Repository(),
            'url': '',
            "excludes": [],
            'html': '',
            'error': ''
        }

    def __getitem__(self, name):
        if name in self.meta['repository']:
            return self.meta['repository'][name]
        return self.meta[name]

    def __setitem__(self, name, value):
        if name not in self.meta and name not in self.meta['repository']:
            raise ValueError("name error")
        if name == 'url':
            self.meta['repository']['html_url'] = value
        if name in self.meta['repository']:
            self.meta['repository'][name] = value
        else:
            self.meta[name] = value

    def __contains__(self, name):
        return name in self.meta or name in self.meta['repository']

    def __iter__(self):
        return iter(self.meta)

    def __len__(self):
        return len(self.meta)

    def to_dict(self):
        if self.meta['error']:
            return {
                'repository': self.meta['repository'].to_dict(),
                'error': self.meta['error']
            }

        else:
            return self.meta['repository'].to_dict()

    def partial_copy(self):
        copy_meta = Meta()
        copy_meta.meta['excludes'] = self.meta['excludes']
        copy_meta.meta['repository']['target_url'] = self.meta['repository']['target_url']
        copy_meta.meta['repository']['source'] = self.meta['repository']['source']
        copy_meta.meta['repository']['source_type'] = self.meta['repository']['source_type']
        return copy_meta

    def clear_error(self):
        self.meta['error'] = ''


class RepositoryParser:
    def __init__(self, setting: Setting = None):
        self.setting = setting if setting else Setting()
        self.sources = None
        self.failed_list = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.parsed = []

    def download(self, meta: Meta, callback=None):
        """
        Download the url.

        :param meta: include url and report error in this context
        :param callback: callback function
        :returns:if use callback return callback result
        """
        is_github = False
        if 'github' in urlparse(meta['url']).netloc:
            is_github = True
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"
        }
        if is_github:
            headers['Accept'] = "application/vnd.github.v3+json"
        auth = get_github_token() if is_github else ()
        r = None
        retry = 0 if self.setting['REQUESTS_RETRY_ENABLED'] else self.setting['REQUESTS_RETRY_TIMES']
        while retry <= self.setting['REQUESTS_RETRY_TIMES']:
            try:
                r = requests.get(meta['url'], auth=auth, headers=headers,
                                 timeout=(self.setting['REQUESTS_CONNECTION_TIMEOUT'],
                                          self.setting['REQUESTS_READ_TIMEOUT']))
                r.encoding = 'utf-8'
                # print(r.headers)
                break
            except requests.exceptions.RequestException as e:
                retry += 1
                self.logger.error(e)
                time.sleep(self.setting['REQUESTS_RETRY_INTERVAL'])
            finally:
                if r:
                    r.close()
        if r:
            meta['html'] = r.text
        else:
            meta['error'] = "download failed: {}".format(meta['url'])
            self.logger.error("download failed: {}".format(meta['url']))

        if callback:
            return callback(meta)

    def parse(self, repositories_sources=None, database='', status_path=''):
        """
        common parse function
        """
        if not repositories_sources and not database:
            return
        if database:
            store = RepositoryStore(self.setting)
        if not repositories_sources and database:
            try:
                repositories_sources = store.get_repositories(database)
            except Exception as e:
                raise ParserError("Read repository source failed: {}".format(str(e)))
                return

        self.failed_list = {}
        self.sources = repositories_sources

        repository_list = []
        for repositories_source in repositories_sources:
            meta_source = Meta()
            meta_source['source'] = repositories_source['source']
            meta_source['excludes'] = repositories_source['excludes']
            meta_source['target_url'] = ','.join(repositories_source['targets'])

            self.get_source_type(meta_source, self.process_error)
            if meta_source['error']:
                continue
            if meta_source['source_type'] == 'index':
                for meta_repository in self.parse_index(meta_source, self.process_error):
                    if meta_repository['error']:
                        continue
                    if database:
                        ret = store.add_repository(database, meta_repository['repository'])
                        if isinstance(ret, int):
                            yield meta_repository.to_dict()
                        else:
                            meta_repository['error'] = json.dumps(ret) if isinstance(ret, dict) else ret
                            self.process_error(meta_source)
                    else:
                        yield meta_repository.to_dict()
            else:
                repository_list.append(meta_source)

        for repository in repository_list:
            meta_repository = self.parse_repository(repository)
            if meta_repository['error']:
                continue
            if database:
                ret = store.add_repository(database, meta_repository['repository'])
                if isinstance(ret, int):
                    yield meta_repository.to_dict()
                else:
                    meta_repository['error'] = json.dumps(ret) if isinstance(ret, dict) else ret
                    self.process_error(meta_repository)
            else:
                yield meta_repository.to_dict()

        if status_path:
            name = ''
            if database:
                name = os.path.basename(database).split('.')[0]
            self.save_status(status_path, name)

    def get_source_type(self, meta_source: Meta, error_callback=None):
        raise NotImplementedError('Need to implemented in subclass')

    def matches_excludes(self, meta: Meta):
        raise NotImplementedError('Need to implemented in subclass')

    def parse_index(self, meta_source: Meta, error_callback=None):
        raise NotImplementedError('Need to implemented in subclass')

    def parse_repository(self, meta_source: Meta, error_callback=None):
        raise NotImplementedError('Need to implemented in subclass')

    def process_error(self, meta: Meta):
        if meta['source'] not in self.failed_list:
            self.failed_list[meta['source']] = []
        self.failed_list[meta['source']].append(meta.to_dict())

    def save_status(self, path='', name=''):
        """
        Export repo list to json file

        :param data: data to save
        :param file_name: file name to save
        """

        if not self.failed_list or not path:
            return
        # process failed list
        time_str = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        result = {
            "generatedAt": time_str,
            "input": self.sources,
            "status": self.failed_list
        }
        name = name if name else self.__class__.__name__.lower()
        file_name = os.path.join(path, '_'.join((name, 'parse', time_str)) + '.json')
        self.logger.info("save parse status to <{}>".format(file_name))
        with open(file_name, 'w', encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)


class Cgit(RepositoryParser):

    def get_source_type(self, meta_source: Meta, error_callback=None):
        if not error_callback:
            error_callback = self.process_error
        meta_source['url'] = meta_source['source']
        self.download(meta_source)
        if meta_source['error']:
            return meta_source
        soup = BeautifulSoup(meta_source['html'], 'html.parser')
        # Check if this is a index page
        tab = soup.find('table', attrs={'class': 'tabs'})
        if not tab:
            meta_source['error'] = "parse failed"
            return meta_source
        if tab.find('td').text.strip() == "index":
            meta_source['source_type'] = "index"
        elif tab.find('td').text.strip().find("summary") != -1:
            meta_source['source_type'] = "repository"
        else:
            meta_source['error'] = "parse failed"
            error_callback(meta_source)
        return meta_source

    def matches_excludes(self, meta: Meta):
        return meta['url'] in meta['excludes']

    def parse_index(self, meta_source: Meta, error_callback=None):
        """
            Parser Index page.

            :param meta_source: include necessary for build repository list
            :param error_callback: error_callback function
            :yield: parse_repository
        """
        if not error_callback:
            error_callback = self.process_error
        original_url = meta_source['url']
        offset = 0
        if '?ofs=' in meta_source['url']:
            original_url = meta_source['url'].split("?ofs=")[0]
            offset = meta_source['url'].split("?ofs=")[1]
        original_offset = offset
        while True:
            meta_index = meta_source.partial_copy()
            meta_index['url'] = original_url + "?ofs=" + str(offset)
            if meta_index['url'] in self.parsed:
                meta_index['error'] = "already parsed {}".format(meta_index['source'])
                error_callback(meta_index)
                break
            if self.matches_excludes(meta_index):
                meta_index['error'] = 'exclude'
                error_callback(meta_index)
                break
            self.download(meta_index)
            if meta_index['error']:
                error_callback(meta_index)
                break
            soup = BeautifulSoup(meta_index['html'], 'html.parser')
            table_list = soup.find('table', attrs={'class': 'list nowrap'})
            offset_page = len(table_list.find_all('tr')) - \
                     len(table_list.find_all('tr', attrs={'class': ['nohover', 'nohover-highlight']}))
            self.parsed.append(meta_index['url'])
            if offset_page == 0:
                if offset == original_offset:
                    meta_index['error'] = "empty index"
                    error_callback(meta_index)
                break
            offset += offset_page
            # process index page
            table = soup.find('table', attrs={'class': 'list nowrap'})
            if not table:
                meta_index['error'] = "parsing failed"
                error_callback(meta_index)
                continue
            section = ""
            for row in table.find_all('tr'):
                meta_repository = meta_index.partial_copy()
                cols = row.find_all('td')
                # Table header part
                if len(cols) == 0:
                    ths = row.find_all('th')
                    for idx, th in enumerate(ths):
                        th = th.text.strip()
                        if th == "Name":
                            name_index = idx
                        elif th == "Description":
                            description_index = idx
                        elif th == "Owner":
                            owner_index = idx
                    continue
                # section part
                if len(cols) == 1:
                    section = cols[0].text.strip()
                    continue
                # repo part
                url = ""
                for link in cols[name_index].find_all('a', href=True):
                    url = urljoin(meta_repository['source'], link['href'])
                cols = [ele.text.strip() for ele in cols]
                meta_repository['section'] = section
                meta_repository['name'] = cols[name_index] if name_index != -1 else ""
                meta_repository['descriptions'] = cols[description_index] if description_index != -1 else ""
                meta_repository['owner'] = cols[owner_index] if owner_index != -1 else ""
                meta_repository['url'] = url if url else ""

                yield self.parse_repository(meta_repository)

    def parse_repository(self, meta_repository: Meta, error_callback=None):
        """
            Parser repository page.

            :param meta_repository: include necessary for build repository
            :param error_callback: error process callback
            :returns: repository
        """
        if not error_callback:
            error_callback = self.process_error
        if self.matches_excludes(meta_repository):
            meta_repository['error'] = 'exclude'
            error_callback(meta_repository)
            return meta_repository
        self.download(meta_repository)
        if meta_repository['error']:
            error_callback(meta_repository)
            return meta_repository
        self.parsed.append(meta_repository['url'])
        soup = BeautifulSoup(meta_repository['html'], 'html.parser')
        # Process repo page
        # Check name, description and owner
        table = soup.find('table', attrs={'id': "header"})
        if not table:
            meta_repository['error'] = "parsing failed"
            error_callback(meta_repository)
            return meta_repository

        name = table.find('td', attrs={'class': 'main'}).text.strip().split(":")[-1].strip()
        cols = table.find_all('td', attrs={'class': 'sub'})
        if len(cols) == 1:
            descriptions = cols[0].text.strip()
            owner = ""
        if len(cols) == 2:
            descriptions = cols[0].text.strip()
            owner = cols[1].text.strip()

        meta_repository['name'] = meta_repository['name'] if 'name' in meta_repository and \
                                                              meta_repository['name'] and \
                                                              name != meta_repository['name'] else name
        meta_repository['descriptions'] = meta_repository['descriptions'] if 'descriptions' in meta_repository and \
                                                             len(descriptions) <= len(meta_repository['descriptions']) \
                                                             else descriptions
        meta_repository['owner'] = meta_repository['owner'] if 'owner' in meta_repository and \
                                                               meta_repository['owner'] and \
                                                               owner != meta_repository['owner'] else owner
        section = meta_repository['section'] if 'section' in meta_repository else ""
        section = self.setting['DEFAULT_SECTION_NAME'] if not section and \
                                                          self.setting['ENABLE_DEFAULT_SECTION'] else section

        # Process clone url
        clone_url = []
        git_url = []
        table = soup.find('table', attrs={'class': ['list nowrap', 'list']})

        if table:
            for row in table.find_all('tr'):
                if row.text.strip() == "Clone":
                    for element in row.next_siblings:
                        if element.string.startswith("git"):
                            git_url.append(element.string)
                        if element.string.startswith(("http", "https")):
                            clone_url.append(element.string)
        if not clone_url:
            meta_repository['error'] = "No clone URL"
            error_callback(meta_repository)
            return meta_repository

        meta_repository['section'] = section
        meta_repository['clone_url'] = ",".join(clone_url)
        return meta_repository


class GitHub(RepositoryParser):

    def get_source_type(self, meta_source: Meta, error_callback=None):
        if not error_callback:
            error_callback = self.process_error
        parsed_src = meta_source['source'].split("/")
        if len(parsed_src) == 1:
            meta_source['source_type'] = 'index'
        elif len(parsed_src) == 2:
            meta_source['source_type'] = 'repository'
        else:
            meta_source['error'] = "parse failed"
            error_callback(meta_source)
        return meta_source

    def matches_excludes(self, meta):
        for exclude in meta['excludes']:
            if exclude.index("/") != -1:
                # this is full name compare
                if meta['owner'] + "/" + meta['name'] == exclude:
                    return True
            else:
                # this is owner
                if meta['owner'] == exclude:
                    return True
        return False

    def parse_index(self, meta_source: Meta, error_callback=None):
        if not error_callback:
            error_callback = self.process_error
        parsed_src = meta_source['source'].split("/")
        original_url = "https://api.github.com/users/{}/repos".format(parsed_src[0])
        page = 1

        while True:
            meta_index = meta_source.partial_copy()
            meta_index['url'] = original_url + "?page=" + str(page)
            if meta_index['url'] in self.parsed:
                meta_index['error'] = "already parsed {}".format(meta_index['source'])
                error_callback(meta_index)
                break
            self.download(meta_index)
            if meta_index['error']:
                error_callback(meta_index)
                break
            res_json = json.loads(meta_index['html'])
            if not res_json:
                if page == 1:
                    meta_index['error'] = "empty index"
                    error_callback(meta_index)
                break
            page += 1
            for repo in res_json:
                meta_repository = meta_index.partial_copy()
                if not repo['clone_url']:
                    meta_repository['error'] = "No clone URL"
                    error_callback(meta_repository)
                    continue
                meta_repository['name'] = repo['name']
                meta_repository['section'] = repo['owner']['login']
                meta_repository['owner'] = repo['owner']['login']
                meta_repository['descriptions'] = repo['description']
                meta_repository['html_url'] = repo['html_url']
                meta_repository['clone_url'] = repo['clone_url']
                if self.matches_excludes(meta_repository):
                    meta_repository['error'] = "exclude"
                    error_callback(meta_repository)
                    continue
                yield meta_repository

    def parse_repository(self, meta_source: Meta, error_callback=None):
        """
            Parser repository page.

            :param meta_source: include necessary for build repository
            :param error_callback: error process callback
            :returns: repository
        """
        if not error_callback:
            error_callback = self.process_error
        parsed_src = meta_source['source'].split("/")
        meta_repository = meta_source.partial_copy()
        meta_repository['url'] = "https://api.github.com/repos/{}/{}".format(parsed_src[0], parsed_src[1])
        if self.matches_excludes(meta_repository):
            meta_repository['error'] = 'exclude'
            return meta_repository
        self.download(meta_repository)
        if meta_repository['error']:
            error_callback(meta_repository)
            return meta_repository
        res_json = json.loads(meta_repository['html'])
        if "message" in res_json:
            meta_repository['error'] = "Github cannot find this repository"
            error_callback(meta_repository)
            return meta_repository

        # parser repository
        if not res_json['clone_url']:
            meta_repository['error'] = "No clone URL"
            error_callback(meta_repository)
            return meta_repository

        meta_repository['name'] = res_json['name']
        meta_repository['section'] = res_json['owner']['login']
        meta_repository['owner'] = res_json['owner']['login']
        meta_repository['descriptions'] = res_json['description']
        meta_repository['html_url'] = res_json['html_url']
        meta_repository['clone_url'] = res_json['clone_url']
        if self.matches_excludes(meta_repository):
            meta_repository['error'] = "exclude"
            error_callback(meta_repository)
            return meta_repository
        return meta_repository
