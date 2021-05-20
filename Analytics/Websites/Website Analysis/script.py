from omniscope.api import OmniscopeApi
import pandas as pd
omniscope_api = OmniscopeApi()


url = omniscope_api.get_option("url")
max_depth = omniscope_api.get_option("max_depth")
n_workers = omniscope_api.get_option("n_workers")

if url is None:
	omniscope_api.abort("No url specified")


import asyncio
import httpx
from bs4 import BeautifulSoup as bs
from urllib.parse import urlparse, urljoin
from typing import Callable


class Analyser:
    
    def __init__(self, url: str, n_workers: int, max_depth: int, report_text: Callable[[dict], None], report_urls: Callable[[list], None], report_images: Callable[[list], None], local_only: bool = True):
        self.n_workers = n_workers
        self.url = url
        self.base = urlparse(url).scheme + "://" + urlparse(url).netloc + "/"
        self.visited_sites = set()
        self.visited_sites.add(url.strip())
        self.n_busy_workers = self.n_workers
        self.local_only = local_only
        self.max_depth = max_depth
        self.report_urls = report_urls
        self.report_text = report_text
        self.report_images = report_images

        
    async def analyse_site(self, site_data, url, depth, queue):
        soup = bs(site_data, features="html.parser")
        
        title_tag = soup.find("title")
        title = ""
        if title_tag is not None:
            title = title_tag.text
            
        h1_tag = soup.find("h1")
        h1 = ""
        if h1_tag is not None:
            h1 = h1_tag.text
        
        
        if self.report_text is not None:
            self.report_text({"url": url, "text": soup.text, "title": title, "h1": h1})
            
            
        sites = set()
        urls = []
        for a in soup.findAll('a', href=True):
            link = urljoin(self.base, a.get("href"))
            urls.append({"url": link, "parent": url, })
            if link.startswith(self.base) or not self.local_only:
                sites.add(link.strip())
                
        images = []
        for img in soup.findAll('img', src=True):
            images.append({"url": url, "image": img.get("src")})
            
        new_sites = sites - self.visited_sites
        if depth < self.max_depth:
            for site in new_sites:
                await queue.put({"url": site, "depth": depth + 1})
            
        self.visited_sites |= new_sites
        
        if self.report_urls is not None:
            self.report_urls(urls)
            
        if self.report_images is not None:
            self.report_images(images)
                
        
            
    async def worker(self, queue, name):
        
        try:
            
            while not queue.empty() or self.n_busy_workers > 1  :
                
                self.n_busy_workers = self.n_busy_workers - 1
                
                job = await queue.get()
                
                self.n_busy_workers = self.n_busy_workers + 1
                
                data = None
                
                try:
                    
                    async with httpx.AsyncClient() as client:
                        data = await client.get(job["url"])
                    
                except: 
                    continue
                
                await self.analyse_site(data.text, job["url"], job["depth"], queue)
                
                
            
            self.cancel_workers(name)
            
        except asyncio.CancelledError:
            pass
        
            
        
    def cancel_workers(self, name):
        for w in self.workers:
            if w.get_name() != name:
                w.cancel()
        
 
    async def run(self):
        
        queue = asyncio.Queue()
        queue.put_nowait({"url": self.url, "depth": 0})
        
        self.workers = [asyncio.create_task(self.worker(queue, "worker_" + str(i)), name="worker_" + str(i))
                 for i in range(self.n_workers)]
     
        await asyncio.gather(*self.workers)
     
 

def print_text(d):
    df = pd.DataFrame({"url": [d["url"]], "text": [d["text"]], "title": [d["title"]], "h1": [d["h1"]]})
    
    omniscope_api.write_output_records(df, output_number=0)

def print_urls(ds):
    if len(ds) > 0:
        parents = []
        urls = []
        for d in ds:
            parents.append(d["parent"])
            urls.append(d["url"])

        df = df = pd.DataFrame({"parent": parents, "url": urls})

        omniscope_api.write_output_records(df, output_number=1)
        
def print_images(ds):
    if len(ds) > 0:
        urls = []
        images = []
        for d in ds:
            urls.append(d["url"])
            images.append(d["image"])

        df = df = pd.DataFrame({"urls": urls, "images": images})

        omniscope_api.write_output_records(df, output_number=2)        
       
 


a = Analyser(url, n_workers = n_workers, max_depth = max_depth, report_text = print_text, report_urls = print_urls, report_images = print_images, local_only = True)

asyncio.run(a.run())

omniscope_api.close()
